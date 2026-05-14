#!/usr/bin/env python3
"""
Manage Way Back Home events via the API.

Uses your gcloud credentials automatically — no Firebase setup needed.
Requires: gcloud auth login (with a @google.com account)

Usage:
  # Create an event
  python3 scripts/manage_event.py create buildwithai-chi "Build with AI Chicago"
  python3 scripts/manage_event.py create buildwithai-chi "Build with AI Chicago" --max 1000

  # Update an event (e.g. increase max participants)
  python3 scripts/manage_event.py update buildwithai-chi --max 1000
  python3 scripts/manage_event.py update buildwithai-chi --name "Build with AI Chicago 2026"

  # View an event
  python3 scripts/manage_event.py get buildwithai-chi
"""

import argparse
import json
import subprocess
import sys
import os

# Load API URL from workshop config or use default
CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "workshop.config.json")
DEFAULT_API_URL = "https://api.waybackhome.dev"


def get_api_base_url():
    """Get API base URL from workshop.config.json."""
    try:
        with open(CONFIG_PATH) as f:
            config = json.load(f)
            return config.get("api_base_url", DEFAULT_API_URL)
    except (FileNotFoundError, json.JSONDecodeError):
        return DEFAULT_API_URL


def get_identity_token():
    """Get a Google OIDC token using gcloud."""
    try:
        result = subprocess.run(
            ["gcloud", "auth", "print-identity-token"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        print("❌ Failed to get identity token.")
        print("   Run: gcloud auth login")
        sys.exit(1)
    except FileNotFoundError:
        print("❌ gcloud not found. Install the Google Cloud SDK.")
        sys.exit(1)


def api_request(method, path, token, data=None):
    """Make an API request using curl (available everywhere)."""
    api_url = get_api_base_url()
    url = f"{api_url}{path}"

    cmd = [
        "curl", "-s", "-w", "\n%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {token}",
        "-H", "Content-Type: application/json",
    ]

    if data:
        cmd.extend(["-d", json.dumps(data)])

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    # Split response body and status code
    lines = output.rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    status_code = int(lines[-1]) if lines[-1].isdigit() else 0

    return status_code, body


def cmd_create(args):
    """Create a new event."""
    token = get_identity_token()

    data = {
        "code": args.code,
        "name": args.name,
    }
    if args.description:
        data["description"] = args.description
    if args.max:
        data["max_participants"] = args.max

    status, body = api_request("POST", "/events", token, data)

    if status == 200:
        event = json.loads(body)
        print(f"✓ Event '{event['code']}' created!")
        print(f"  Name:             {event['name']}")
        print(f"  Max participants: {event['max_participants']}")
        print(f"  Created by:       {event['created_by']}")
    elif status == 409:
        print(f"⚠️  Event '{args.code}' already exists!")
        sys.exit(1)
    elif status == 403:
        print("❌ Access denied. You must use a @google.com account.")
        sys.exit(1)
    elif status == 401:
        print("❌ Authentication failed. Run: gcloud auth login")
        sys.exit(1)
    else:
        print(f"❌ Error ({status}): {body}")
        sys.exit(1)


def cmd_update(args):
    """Update an existing event."""
    token = get_identity_token()

    data = {}
    if args.name:
        data["name"] = args.name
    if args.description is not None:
        data["description"] = args.description
    if args.max:
        data["max_participants"] = args.max

    if not data:
        print("⚠️  No updates provided. Use --name, --description, or --max.")
        sys.exit(1)

    status, body = api_request("PATCH", f"/events/{args.code}", token, data)

    if status == 200:
        event = json.loads(body)
        print(f"✓ Event '{event['code']}' updated!")
        print(f"  Name:             {event['name']}")
        print(f"  Description:      {event.get('description', '')}")
        print(f"  Max participants: {event['max_participants']}")
        print(f"  Current count:    {event['participant_count']}")
    elif status == 404:
        print(f"❌ Event '{args.code}' not found.")
        sys.exit(1)
    elif status == 403:
        print("❌ Access denied. You must use a @google.com account.")
        sys.exit(1)
    elif status == 401:
        print("❌ Authentication failed. Run: gcloud auth login")
        sys.exit(1)
    else:
        print(f"❌ Error ({status}): {body}")
        sys.exit(1)


def cmd_get(args):
    """Get event details (public, no auth needed)."""
    api_url = get_api_base_url()

    result = subprocess.run(
        ["curl", "-s", "-w", "\n%{http_code}", f"{api_url}/events/{args.code}"],
        capture_output=True, text=True
    )
    output = result.stdout.strip()
    lines = output.rsplit("\n", 1)
    body = lines[0] if len(lines) > 1 else ""
    status_code = int(lines[-1]) if lines[-1].isdigit() else 0

    if status_code == 200:
        event = json.loads(body)
        print(f"📋 Event: {event['code']}")
        print(f"  Name:             {event['name']}")
        print(f"  Description:      {event.get('description', '')}")
        print(f"  Max participants: {event['max_participants']}")
        print(f"  Current count:    {event['participant_count']}")
        print(f"  Active:           {event['active']}")
        print(f"  Created by:       {event.get('created_by', 'N/A')}")
        print(f"  Created at:       {event.get('created_at', 'N/A')}")
    elif status_code == 404:
        print(f"❌ Event '{args.code}' not found.")
        sys.exit(1)
    else:
        print(f"❌ Error ({status_code}): {body}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Manage Way Back Home events via the API",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="Requires: gcloud auth login (with a @google.com account)"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Create command
    create_parser = subparsers.add_parser("create", help="Create a new event")
    create_parser.add_argument("code", help="Event code (e.g. buildwithai-chi)")
    create_parser.add_argument("name", help="Event display name")
    create_parser.add_argument("--description", "-d", default=None, help="Event description")
    create_parser.add_argument("--max", "-m", type=int, default=None, help="Max participants (default: 500)")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update an event")
    update_parser.add_argument("code", help="Event code to update")
    update_parser.add_argument("--name", "-n", default=None, help="New display name")
    update_parser.add_argument("--description", "-d", default=None, help="New description")
    update_parser.add_argument("--max", "-m", type=int, default=None, help="New max participants")

    # Get command
    get_parser = subparsers.add_parser("get", help="View event details")
    get_parser.add_argument("code", help="Event code to view")

    args = parser.parse_args()

    if args.command == "create":
        cmd_create(args)
    elif args.command == "update":
        cmd_update(args)
    elif args.command == "get":
        cmd_get(args)


if __name__ == "__main__":
    main()

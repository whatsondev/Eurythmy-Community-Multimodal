"""
Event Routes (Public + Google User)

Public endpoints for event information and participant listing.
Google-authenticated endpoints for event creation and updates.
"""

from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Depends

from ..config import DEFAULT_MAX_PARTICIPANTS
from ..database import get_event, create_event, check_username_exists, list_participants_by_event, update_event
from ..dependencies import verify_google_user
from ..models import EventCreate, EventResponse, EventUpdate, UsernameCheckResponse, ParticipantResponse


router = APIRouter(prefix="/events", tags=["Events"])


# =============================================================================
# Google User Endpoints (require @google.com auth)
# =============================================================================

@router.post("", response_model=EventResponse)
async def create_new_event(data: EventCreate, user_email: str = Depends(verify_google_user)):
    """
    Create a new event (google.com users only).

    Requires Firebase Auth with a @google.com email.
    """
    # Check if event code already exists
    existing = await get_event(data.code)
    if existing:
        raise HTTPException(status_code=409, detail="Event code already exists")

    event = {
        "code": data.code,
        "name": data.name,
        "description": data.description or "",
        "max_participants": data.max_participants or DEFAULT_MAX_PARTICIPANTS,
        "participant_count": 0,
        "created_at": datetime.now(timezone.utc),
        "created_by": user_email,
        "active": True,
    }

    await create_event(event)

    return EventResponse(**event)


@router.patch("/{code}", response_model=EventResponse)
async def update_existing_event(code: str, data: EventUpdate, user_email: str = Depends(verify_google_user)):
    """
    Update an existing event (google.com users only).

    Requires Firebase Auth with a @google.com email.
    Only updates the fields that are provided.
    """
    # Verify event exists
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    # Build update dict from provided fields only
    updates = {k: v for k, v in data.dict().items() if v is not None}

    if not updates:
        return EventResponse(**event)

    await update_event(code, updates)

    # Return updated event
    updated = await get_event(code)
    return EventResponse(**updated)


# =============================================================================
# Public Endpoints (no auth required)
# =============================================================================

@router.get("/{code}", response_model=EventResponse)
async def get_event_info(code: str):
    """
    Get event information by code.

    Used by setup.sh to validate event codes.
    """
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    if not event.get("active", True):
        raise HTTPException(status_code=410, detail="Event has ended")

    return EventResponse(**event)


@router.get("/{code}/check-username/{username}", response_model=UsernameCheckResponse)
async def check_username(code: str, username: str):
    """
    Check if a username is available for an event.

    Used by setup.sh to validate username choice.
    """
    # First verify event exists
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    exists = await check_username_exists(code, username)

    return UsernameCheckResponse(
        available=not exists,
        username=username
    )


@router.get("/{code}/participants", response_model=list[ParticipantResponse])
async def list_event_participants(code: str):
    """
    List all participants for an event.

    Used by the world map UI to render participant markers.
    """
    # Verify event exists
    event = await get_event(code)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")

    participants = await list_participants_by_event(code)

    # Only return active participants with completed registration
    return [
        ParticipantResponse(**p)
        for p in participants
        if p.get("active", True) and p.get("registered_at")
    ]

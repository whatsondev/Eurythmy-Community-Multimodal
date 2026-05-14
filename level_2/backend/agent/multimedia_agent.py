"""
multimedia_agent.py — Eurythmy Network Multimodal Pipeline
===========================================================
Adapted from the Way Back Home Level 2 codelab multimedia_agent.py.

Processes recordings and images from Community Eurythmy sessions.
Extracts structured entities (practitioner, specialism, spatial form, venue)
and saves them to the EurythmyGraph Spanner database.

Current recording format: iPhone 17 video.
The Gemini multimodal pipeline handles this fine — no professional
quality required at this stage.

Extraction prompt updated per §5 of eurythmy_dev_instructions_v2.docx.
"""

import os

from google.adk.agents import LlmAgent, SequentialAgent
from dotenv import load_dotenv

from agent.tools.extraction_tools import (
    upload_media,
    extract_from_media,
    save_to_spanner,
)

load_dotenv()

USE_MEMORY_BANK = os.getenv("USE_MEMORY_BANK", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Stage 1 — Upload Agent
# ---------------------------------------------------------------------------

upload_agent = LlmAgent(
    name="UploadAgent",
    model="gemini-2.5-flash",
    instruction="""Extract the file path from the user's message and upload it.

Use `upload_media(file_path, practitioner_id)` to upload the file.
The practitioner_id is optional — include it if the user mentions a specific
practitioner (e.g. 'Tomie's recording' → use their practitioner_id if known).
If the user provides a path like '/path/to/file', use that.

Return the upload result with gcs_uri and media_type.""",
    tools=[upload_media],
    output_key="upload_result",
)

# ---------------------------------------------------------------------------
# Stage 2 — Extraction Agent
# Prompt updated per §5 of eurythmy_dev_instructions_v2.docx
# ---------------------------------------------------------------------------

extraction_agent = LlmAgent(
    name="ExtractionAgent",
    model="gemini-2.5-flash",
    instruction="""Analyse the uploaded recording or image from a Community Eurythmy session.

Previous step result: {upload_result}

Use `extract_from_media(gcs_uri, media_type, signed_url)` with the values from
the upload result.

The extraction prompt sent to Gemini must request the following where visible:

  - Practitioner names (if identifiable)
  - Specialism or form being demonstrated
    (e.g. speech eurythmy, veil work, copper rod, planetary gesture)
  - Spatial forms visible (lemniscate, circle, spiral, triangle …)
  - Musical interval or quality if apparent
  - Venue or setting
  - Any therapeutic or educational context evident

Return as structured JSON matching the Specialisms schema.

Return the extraction results including entities and relationships found.""",
    tools=[extract_from_media],
    output_key="extraction_result",
)

# ---------------------------------------------------------------------------
# Stage 3 — Spanner Save Agent
# ---------------------------------------------------------------------------

spanner_agent = LlmAgent(
    name="SpannerAgent",
    model="gemini-2.5-flash",
    instruction="""Save the extracted eurythmy session information to the EurythmyGraph database.

Upload result:     {upload_result}
Extraction result: {extraction_result}

Use `save_to_spanner(extraction_result, practitioner_id)` to save to Spanner.
Pass the WHOLE `extraction_result` object/dict from the previous step.
Include practitioner_id if it was provided in the upload step.

Return the save statistics.""",
    tools=[save_to_spanner],
    output_key="spanner_result",
)

# ---------------------------------------------------------------------------
# Stage 4 — Summary Agent
# ---------------------------------------------------------------------------

save_msg = (
    "6. Mention that the data is also being synced to the memory bank."
    if USE_MEMORY_BANK
    else ""
)

summary_instruction = f"""Provide a user-friendly summary of the eurythmy session media processing.

Upload:     {{upload_result}}
Extraction: {{extraction_result}}
Database:   {{spanner_result}}

Summarise:
1. What file was processed (name and type)
2. Key information extracted (practitioners, specialisms, spatial forms, venue) — list names and counts
3. Relationships identified (e.g. practitioner demonstrated specialism)
4. What was saved to the database (broadcast ID, number of entities)
5. Any issues encountered
{save_msg}

Be concise but informative. Use warm, community-appropriate language."""

summary_agent = LlmAgent(
    name="SummaryAgent",
    model="gemini-2.5-flash",
    instruction=summary_instruction,
    output_key="summary_result",
)

# ---------------------------------------------------------------------------
# Sequential pipeline
# ---------------------------------------------------------------------------

multimedia_agent = SequentialAgent(
    name="EurythmyMultimediaPipeline",
    description="Processes uploaded recordings and images from Community Eurythmy sessions. Extracts specialisms, practitioners, spatial forms, and venue information, then saves to EurythmyGraph.",
    sub_agents=[upload_agent, extraction_agent, spanner_agent, summary_agent],
)
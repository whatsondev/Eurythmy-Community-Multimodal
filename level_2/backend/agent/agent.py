"""
agent.py — Community Eurythmy Network Agent
=============================================
Adapted from the Way Back Home Level 2 codelab agent.py.

Renames:
  SurvivorGraph  → EurythmyGraph
  graph-db       → eurythmy-db
  skill_embedding→ specialism_embedding

Agent instruction text replaced per §4 of the dev instructions.
"""

import asyncio
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from google.adk.agents import LlmAgent
from google.adk.tools.preload_memory_tool import PreloadMemoryTool
from google.adk.agents.callback_context import CallbackContext
from google.genai import types

from agent.tools.hybrid_search_tools import (
    semantic_search,
    keyword_search,
    hybrid_search,
)
from agent.multimedia_agent import multimedia_agent

load_dotenv()

logger = logging.getLogger(__name__)

USE_MEMORY_BANK = os.getenv("USE_MEMORY_BANK", "false").lower() == "true"

# ---------------------------------------------------------------------------
# Memory Bank callback (saves session after each interaction)
# ---------------------------------------------------------------------------

async def add_session_to_memory(
    callback_context: CallbackContext,
) -> Optional[types.Content]:
    """Automatically save completed sessions to memory bank in the background."""
    if hasattr(callback_context, "_invocation_context"):
        invocation_context = callback_context._invocation_context
        if invocation_context.memory_service:
            asyncio.create_task(
                invocation_context.memory_service.add_session_to_memory(
                    invocation_context.session
                )
            )
            logger.info("Scheduled session save to memory bank in background")


# ---------------------------------------------------------------------------
# Tool list
# ---------------------------------------------------------------------------

agent_tools = [
    semantic_search,   # Force RAG / embedding search
    keyword_search,    # Specific keyword / filter search
    hybrid_search,     # Meaning + location or pillar
]

if USE_MEMORY_BANK:
    agent_tools.append(PreloadMemoryTool())

# ---------------------------------------------------------------------------
# Root agent — instruction text per §4 of eurythmy_dev_instructions_v2.docx
# ---------------------------------------------------------------------------

root_agent = LlmAgent(
    name="eurythmy_network_agent",
    model="gemini-2.5-flash",
    instruction="""
You are a guide for the Community Eurythmy — a knowledge graph connecting
practitioners, teachers, therapists, venues, and participants across the West Midlands
and beyond. You help people find the right movement support, teacher, or therapeutic
approach for their needs.

When someone describes what they are looking for, use semantic_search to find
specialisms and practitioners that match the meaning of what they need, not just
the exact words.

When they give a specific location or pillar, use hybrid_search to combine meaning
and context.

Search routing:
- semantic_search: open or descriptive queries
  e.g. 'something for grief', 'movement to help my child speak'
- keyword_search: specific filters
  e.g. 'therapists in Birmingham', 'practitioners at Elmfield'
- hybrid_search: meaning + location or pillar
  e.g. 'therapeutic work in the West Midlands'

Always respond with warmth. This is a community tool. The people in this graph are
trusted practitioners who have given their knowledge to serve this community.
""",
    tools=agent_tools,
    sub_agents=[multimedia_agent],
    after_agent_callback=add_session_to_memory if USE_MEMORY_BANK else None,
)
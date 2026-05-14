"""
hybrid_search_tools.py — Eurythmy Network
==========================================
ADK tool definitions wrapping HybridSearchService.

Adapted from the Way Back Home Level 2 codelab hybrid_search_tools.py.
Three tools exposed to the agent:
  semantic_search — open/conceptual queries
  keyword_search  — specific filters (venue, role, name)
  hybrid_search   — meaning + location or pillar

Fix applied:
  logger.error → logger.exception in all three tool handlers so the full
  stack trace is printed instead of just the exception message. This was
  masking the real cause of 'NoneType has no attribute row_type'.
"""

from __future__ import annotations

import logging
from functools import lru_cache

from services.hybrid_search_service import HybridSearchService, SearchMethod

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Singleton service
# ---------------------------------------------------------------------------

@lru_cache(maxsize=1)
def _get_service() -> HybridSearchService:
    return HybridSearchService()


# ---------------------------------------------------------------------------
# Shared result formatter
# ---------------------------------------------------------------------------

def _format_results(
    results:      list[dict],
    analysis:     str,
    show_analysis: bool = False,
) -> str:
    if not results:
        return "No practitioners or specialisms found for that query."

    lines = []
    if show_analysis:
        lines.append(f"🔍 {analysis}\n")

    for r in results:
        icon = "🔀" if r.get("found_by_both") else (
               "🧬" if r.get("distance") is not None else "🔑")
        name      = r.get("practitioner_name", "Unknown")
        role      = r.get("role", "")
        specialism= r.get("specialism_name", "")
        level     = r.get("level", "")
        venue     = r.get("venue_name", "")

        line = f"{icon} {name} ({role}) — {specialism} [{level}]"
        if venue:
            line += f" @ {venue}"
        lines.append(line)

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool 1 — Semantic (RAG) search
# ---------------------------------------------------------------------------

async def semantic_search(query: str, limit: int = 10) -> str:
    """
    Force semantic (RAG) search using specialism embeddings.

    Use when you want to find things by MEANING, not just keywords.
    Great for open or abstract queries — handles vocabulary mismatch.

    Routing examples:
      'something for grief'            → Moon gesture, Veil Eurythmy, Interval Third
      'movement to help my child speak'→ Speech Eurythmy, Tomie Ando-Boadman

    Args:
        query: Describe the concept or need in natural language.
        limit: Maximum number of results to return.

    Returns:
        Practitioner/specialism matches ranked by semantic similarity.
    """
    try:
        service = _get_service()
        result  = service.smart_search(
            query,
            force_method=SearchMethod.RAG,
            limit=limit,
        )
        return _format_results(result["results"], result["analysis"], show_analysis=True)
    except Exception as e:
        # logger.exception prints the full stack trace, not just the message.
        logger.exception("semantic_search error: %s", e)
        return f"Error in semantic search: {e}"


# ---------------------------------------------------------------------------
# Tool 2 — Keyword search
# ---------------------------------------------------------------------------

async def keyword_search(query: str, limit: int = 10) -> str:
    """
    Keyword / filter search across practitioner names, roles, specialisms, and venues.

    Use for specific, named queries — venue names, role types, place names.

    Routing examples:
      'therapists in Birmingham'  → Ursula Werner
      'practitioners at Elmfield' → Tomie Ando-Boadman
      'Stourbridge venues'        → Elmfield, Christian Community, Glasshouse

    Args:
        query: Keyword, name, or filter term.
        limit: Maximum number of results to return.

    Returns:
        Filtered practitioner/specialism matches.
    """
    try:
        service = _get_service()
        result  = service.smart_search(
            query,
            force_method=SearchMethod.KEYWORD,
            limit=limit,
        )
        return _format_results(result["results"], result["analysis"], show_analysis=False)
    except Exception as e:
        logger.exception("keyword_search error: %s", e)
        return f"Error in keyword search: {e}"


# ---------------------------------------------------------------------------
# Tool 3 — Hybrid search
# ---------------------------------------------------------------------------

async def hybrid_search(query: str, limit: int = 10) -> str:
    """
    Hybrid search — combines semantic embedding search with keyword filtering,
    merged via Reciprocal Rank Fusion (RRF).

    Use when the query has both a conceptual element AND a location or pillar.

    Routing examples:
      'therapeutic work in the West Midlands' → Ursula Werner, Elysia Centre
      'performance eurythmy in Stourbridge'   → Glasshouse / Stage Group

    Results marked 🔀 were found by both methods (highest confidence).

    Args:
        query: Natural language query combining concept + location or pillar.
        limit: Maximum number of results to return.

    Returns:
        RRF-merged practitioner/specialism matches.
    """
    try:
        service = _get_service()
        result  = service.smart_search(
            query,
            force_method=SearchMethod.HYBRID,
            limit=limit,
        )
        return _format_results(result["results"], result["analysis"], show_analysis=True)
    except Exception as e:
        logger.exception("hybrid_search error: %s", e)
        return f"Error in hybrid search: {e}"
"""
hybrid_search_service.py — Eurythmy Network
============================================
Adapted from the Way Back Home Level 2 codelab hybrid_search_service.py.

Key renames:
  graph-db        → eurythmy-db
  SurvivorGraph   → EurythmyGraph
  Survivors       → Practitioners
  Biomes          → Venues
  Skills          → Specialisms
  skill_embedding → specialism_embedding
  SurvivorHasSkill→ PractitionerHasSpecialism
  proficiency     → level

"""

import logging
import os
from enum import Enum
from typing import Any

from google.cloud import spanner
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

PROJECT_ID  = os.getenv("GOOGLE_CLOUD_PROJECT")
# BUG FIX 1: Default was "eurythmy -community" (old codelab name). Corrected to "eurythmy-network".
INSTANCE_ID = os.getenv("INSTANCE_ID", "eurythmy -community")
DATABASE_ID = os.getenv("DATABASE_ID", "eurythmy-db")


class SearchMethod(Enum):
    KEYWORD  = "keyword"
    RAG      = "semantic"
    HYBRID   = "hybrid"


class HybridSearchService:
    """
    Three search modes for the Eurythmy Community:
      - RAG (semantic):  cosine distance on specialism_embedding
      - keyword:         SQL LIKE / category filter on Practitioners + Venues
      - hybrid:          RRF merge of both
    """

    def __init__(self):
        client   = spanner.Client(project=PROJECT_ID)
        instance = client.instance(INSTANCE_ID)
        self.db  = instance.database(DATABASE_ID)

    # -----------------------------------------------------------------------
    # Semantic (RAG) search
    # -----------------------------------------------------------------------

    def _rag_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        Graph RAG query: traverse Practitioner → Specialism edges,
        rank by cosine distance on specialism_embedding.
        """
        sql = """
            WITH query_embedding AS (
                SELECT embeddings.values AS val
                FROM ML.PREDICT(
                    MODEL TextEmbeddings,
                    (SELECT @query AS content)
                )
            )
            SELECT
                p.practitioner_id,
                p.name AS practitioner_name,
                p.role,
                p.pillar,
                sp.specialism_id,
                sp.name AS specialism_name,
                sp.category,
                phs.level,
                COSINE_DISTANCE(
                    sp.specialism_embedding,
                    (SELECT val FROM query_embedding)
                ) AS distance
            FROM Practitioners p
            JOIN PractitionerHasSpecialism phs
                ON p.practitioner_id = phs.practitioner_id
            JOIN Specialisms sp
                ON phs.specialism_id = sp.specialism_id
            WHERE sp.specialism_embedding IS NOT NULL
            ORDER BY distance ASC
            LIMIT @limit
        """
        with self.db.snapshot() as snapshot:
            # BUG FIX 2: Individual Spanner rows don't have .keys().
            # Field names must be read from result.fields on the StreamedResultSet.
            result = snapshot.execute_sql(
                sql,
                params={"query": query, "limit": limit},
                param_types={
                    "query": spanner.param_types.STRING,
                    "limit": spanner.param_types.INT64,
                },
            )
            rows = list(result)
            fields = [field.name for field in result.fields]
            return [dict(zip(fields, row)) for row in rows]

    # -----------------------------------------------------------------------
    # Keyword search
    # -----------------------------------------------------------------------

    def _keyword_search(self, query: str, limit: int = 10) -> list[dict]:
        """
        SQL LIKE search across practitioner name, role, specialism name/category,
        and venue name/location.
        """
        sql = """
                SELECT DISTINCT
        p.practitioner_id,
        p.name AS practitioner_name,
        p.role,
        p.pillar,
        sp.specialism_id,
        sp.name AS specialism_name,
        sp.category,
        phs.level,
        v.name AS venue_name,
        v.location AS venue_location
    FROM Practitioners p
    JOIN PractitionerHasSpecialism phs
        ON p.practitioner_id = phs.practitioner_id
    JOIN Specialisms sp
        ON phs.specialism_id = sp.specialism_id
    LEFT JOIN PractitionerAtVenue pav
        ON p.practitioner_id = pav.practitioner_id
    LEFT JOIN Venues v
        ON pav.venue_id = v.venue_id
    WHERE
        LOWER(COALESCE(p.name, '')) LIKE LOWER(@query_like)
        OR LOWER(COALESCE(p.role, '')) LIKE LOWER(@query_like)
        OR LOWER(COALESCE(sp.name, '')) LIKE LOWER(@query_like)
        OR LOWER(COALESCE(sp.category, '')) LIKE LOWER(@query_like)
        OR LOWER(COALESCE(v.name, '')) LIKE LOWER(@query_like)
        OR LOWER(COALESCE(v.location, '')) LIKE LOWER(@query_like)
    ORDER BY
        p.name,
        sp.name
    LIMIT @limit
        """
        query_like = f"%{query}%"
        with self.db.snapshot() as snapshot:
            # BUG FIX 2 (same fix): Use result.fields instead of row.keys().
            result = snapshot.execute_sql(
                sql,
                params={"query_like": query_like, "limit": limit},
                param_types={
                    "query_like": spanner.param_types.STRING,
                    "limit":      spanner.param_types.INT64,
                },
            )
            rows = list(result)
            fields = [field.name for field in result.fields]
            return [dict(zip(fields, row)) for row in rows]

    # -----------------------------------------------------------------------
    # RRF hybrid merge
    # -----------------------------------------------------------------------

    @staticmethod
    def _rrf_merge(
        keyword_results: list[dict],
        rag_results:     list[dict],
        K: int = 60,
    ) -> list[dict]:
        """Reciprocal Rank Fusion — merge two ranked lists."""
        keyword_ranks: dict[str, int] = {}
        rag_ranks:     dict[str, int] = {}

        for rank, row in enumerate(keyword_results, start=1):
            pid = row["practitioner_id"]
            keyword_ranks[pid] = rank

        for rank, row in enumerate(rag_results, start=1):
            pid = row["practitioner_id"]
            rag_ranks[pid] = rank

        all_ids = set(keyword_ranks) | set(rag_ranks)
        scored  = []

        rag_by_id     = {r["practitioner_id"]: r for r in rag_results}
        keyword_by_id = {r["practitioner_id"]: r for r in keyword_results}

        for pid in all_ids:
            rank_kw  = keyword_ranks.get(pid, float("inf"))
            rank_rag = rag_ranks.get(pid,     float("inf"))

            rrf_score = 0.0
            if rank_kw  != float("inf"):
                rrf_score += 1.0 / (K + rank_kw)
            if rank_rag != float("inf"):
                rrf_score += 1.0 / (K + rank_rag)

            row  = rag_by_id.get(pid) or keyword_by_id[pid]
            both = pid in keyword_ranks and pid in rag_ranks

            scored.append({**row, "rrf_score": rrf_score, "found_by_both": both})

        return sorted(scored, key=lambda x: x["rrf_score"], reverse=True)

    # -----------------------------------------------------------------------
    # Public smart_search entry point
    # -----------------------------------------------------------------------

    def smart_search(
        self,
        query:        str,
        force_method: SearchMethod | None = None,
        limit:        int = 10,
    ) -> dict[str, Any]:
        """
        Route to the best search method and return unified results dict.

        Returns:
            {
              "results": [...],
              "method":  "semantic" | "keyword" | "hybrid",
              "analysis": "...",
            }
        """
        method = force_method or SearchMethod.HYBRID

        if method == SearchMethod.RAG:
            results  = self._rag_search(query, limit)
            analysis = "Semantic (RAG) search — results ranked by specialism embedding similarity."
        elif method == SearchMethod.KEYWORD:
            results  = self._keyword_search(query, limit)
            analysis = "Keyword search — results filtered by text match."
        else:
            kw_results  = self._keyword_search(query, limit)
            rag_results = self._rag_search(query, limit)
            results     = self._rrf_merge(kw_results, rag_results)[:limit]
            analysis    = "Hybrid search — keyword + semantic results merged via RRF."

        return {
            "results":  results,
            "method":   method.value,
            "analysis": analysis,
        }
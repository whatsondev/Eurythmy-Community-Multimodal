import json
import logging
import os  # BUG FIX 1: duplicate 'import os' removed (was imported twice)
from typing import List, Optional
from google import genai
from google.genai import types
from .base_extractor import (
    BaseExtractor, ExtractionResult, ExtractedEntity,
    ExtractedRelationship, EntityType, RelationshipType
)
from services.gcs_service import GCSService

logger = logging.getLogger(__name__)


class TextExtractor(BaseExtractor):
    """Extract Community Eurythmy Network entities from text content"""
    # BUG FIX 2: Class docstring said "Extract survivor network entities" — updated.

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv('PROJECT_ID'),
            location=os.getenv('REGION'),
        )
        self.model_name  = 'gemini-2.5-flash'
        self.gcs_service = GCSService()

    def _get_extraction_prompt(self, text: str) -> str:
        # BUG FIX 3: Entire prompt used old codelab entity types, property names,
        # categories, and relationship names. The Gemini response is parsed with
        # EntityType(e['entity_type']) — if the model returns "Survivor" or "Skill"
        # those strings fail the EntityType enum lookup and every entity is silently
        # skipped (logged as "Skipping invalid entity"). Prompt now matches the
        # eurythmy EntityType and RelationshipType enum values exactly.
        return f"""Analyse this text and extract information for the Community Eurythmy Network database.

## Entity Types to Extract:

1. **Practitioner**: People in the eurythmy network — teachers, therapists, performers, students, musicians, organisers.
   - Properties: name (required), role (teacher|therapist|performer|student|musician|organiser),
     bio, pillar (Art|Health|Education|Social|Tools), notes

2. **Specialism**: Eurythmy forms, practices, or areas of expertise.
   - Properties: name (required), category (speech|tone|therapeutic|pedagogical|performance|instrument|science),
     description, pillar

3. **Seek**: What a participant is looking for — a therapeutic need or learning goal.
   - Properties: name (required), category (therapeutic|artistic|educational|social),
     description

4. **Material**: Physical resources — instruments, scores, silk veils, copper rods, recordings.
   - Properties: name (required), type (instrument|score|textile|recording|other),
     description

5. **Venue**: Spaces where eurythmy takes place.
   - Properties: name (required), location, type (school|therapeutic|arts_centre|community_hub|congregation),
     notes, pillar

## Relationships to Identify:

1. **PractitionerHasSpecialism**: Practitioner → Specialism (level: master|qualified|developing|supporting)
2. **ParticipantSeeks**: Practitioner/Participant → Seek (status: active|resolved|pending)
3. **SurvivorFoundResource**: Practitioner → Material (found_at: timestamp or description)
4. **PractitionerAtVenue**: Practitioner → Venue
5. **PractitionerCanSupport**: Practitioner → Practitioner (reason, match_score 0–1)
6. **SpecialismTreatsNeed**: Specialism → Seek (strength: primary|secondary, notes)

## Text to Analyse:
{text[:8000]}

## Return JSON (no markdown):
{{
    "summary": "Brief summary of the content",
    "entities": [
        {{
            "entity_type": "Practitioner|Specialism|Seek|Material|Venue",
            "name": "entity name",
            "properties": {{"key": "value"}},
            "confidence": 0.0
        }}
    ],
    "relationships": [
        {{
            "relationship_type": "PractitionerHasSpecialism|ParticipantSeeks|SurvivorFoundResource|PractitionerAtVenue|PractitionerCanSupport|SpecialismTreatsNeed",
            "source": "source entity name",
            "target": "target entity name",
            "properties": {{}},
            "confidence": 0.0
        }}
    ],
    "broadcast_info": {{
        "title": "suggested title for this content",
        "broadcast_type": "report|session_note|request|update"
    }}
}}"""

    async def extract(self, gcs_uri: str, text_content: str = None) -> ExtractionResult:
        """Extract entities from text"""
        try:
            if not text_content:
                text_content = self.gcs_service.read_text_content(gcs_uri)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=self._get_extraction_prompt(text_content),
                config=types.GenerateContentConfig(
                    response_mime_type="application/json"
                ),
            )

            try:
                result_json = json.loads(response.text)
            except json.JSONDecodeError:
                text = response.text.strip()
                if text.startswith('```json'):
                    text = text[7:-3]
                elif text.startswith('```'):
                    text = text[3:-3]
                result_json = json.loads(text)

            entities = []
            for e in result_json.get('entities', []):
                try:
                    entity_type = EntityType(e['entity_type'])
                    entities.append(ExtractedEntity(
                        entity_type=entity_type,
                        name=e['name'],
                        properties=e.get('properties', {}),
                        confidence=e.get('confidence', 0.8),
                    ))
                except (ValueError, KeyError) as ex:
                    logger.warning(f"Skipping invalid entity: {e}, error: {ex}")

            relationships = []
            for r in result_json.get('relationships', []):
                try:
                    rel_type = RelationshipType(r['relationship_type'])
                    relationships.append(ExtractedRelationship(
                        relationship_type=rel_type,
                        source_name=r['source'],
                        target_name=r['target'],
                        properties=r.get('properties', {}),
                        confidence=r.get('confidence', 0.8),
                    ))
                except (ValueError, KeyError) as ex:
                    logger.warning(f"Skipping invalid relationship: {r}, error: {ex}")

            return ExtractionResult(
                media_uri=gcs_uri,
                media_type="text",
                entities=entities,
                relationships=relationships,
                raw_content=text_content[:1000],
                summary=result_json.get('summary', ''),
                broadcast_info=result_json.get('broadcast_info'),
                metadata={'word_count': len(text_content.split())},
            )

        except Exception as e:
            logger.error(f"Text extraction failed: {e}")
            raise

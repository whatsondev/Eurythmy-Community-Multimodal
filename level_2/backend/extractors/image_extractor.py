import json
import logging
import os  # BUG FIX 1: duplicate 'import os' removed (was imported twice)
from PIL import Image
from google import genai
from google.genai import types
from .base_extractor import (
    BaseExtractor, ExtractionResult, ExtractedEntity,
    ExtractedRelationship, EntityType, RelationshipType
)
from services.gcs_service import GCSService

logger = logging.getLogger(__name__)


class ImageExtractor(BaseExtractor):
    """Extract Community Eurythmy Network entities from images and recordings"""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv('PROJECT_ID'),
            location=os.getenv('REGION'),
        )
        self.model_name  = 'gemini-2.5-flash'
        self.gcs_service = GCSService()

    def _get_extraction_prompt(self) -> str:
        # BUG FIX 2: Entire prompt context was codelab content — it described
        # a sci-fi disaster-response scenario with biome survivors, xenobiologists,
        # volcanic environments, amber fuel, and codelab character names
        # (Dr Elena Frost, Captain Yuki Tanaka, Lt Sarah Park).
        #
        # This caused two concrete failures:
        #   a) The model was primed to look for the wrong things in images,
        #      returning codelab-domain entities.
        #   b) Relationship type "PractitionerFoundMaterial" and "SpecialismTreatsSeek"
        #      in the old prompt do not match any RelationshipType enum value, so
        #      RelationshipType(r['relationship_type']) raised ValueError and every
        #      relationship was silently dropped.
        #
        # Replaced with the extraction prompt from eurythmy_dev_instructions_v2.docx §5.
        return """You are analysing a recording or image from a Community Eurythmy session.

## Known Practitioners (match by visual cues where possible):
- Tomie Ando-Boadman — teacher / performer, based at Elmfield Steiner School, Stourbridge
- Marie-Reine — teacher, Christian Community tradition, speech and sacramental eurythmy
- Ursula Werner — therapist, Elysia Therapeutic Centre, Stourbridge; copper rod, planetary gestures
- Eurythmy West Midlands Stage Group — ensemble, Glasshouse Arts Centre

## Known Venues:
- Elmfield Steiner School — school / performance space, Stourbridge
- The Christian Community, Stourbridge — congregation / practice space
- Elysia Therapeutic Centre — therapeutic practice, Stourbridge
- Glasshouse Arts Centre — arts centre / performance venue, Stourbridge
- EthyOn Cafe — community hub, Birmingham

## Known Specialisms (examples):
Speech Eurythmy, Tone Eurythmy, Pedagogical Eurythmy, Therapeutic Eurythmy,
Copper Rod Eurythmy, Planetary Gesture (Saturn/Moon/Sun), Veil Eurythmy,
Interval Work (Fifth/Third), Lemniscate Forms, Group / Ensemble Eurythmy,
Christian Community Sacramental Eurythmy, Goethean Observation

---

## Extract the following where visible:

### 1. Practitioner names (if identifiable)
Match against known practitioners above using visual cues — costume, setting, instruments held.

### 2. Specialism or form being demonstrated
e.g. speech eurythmy, veil work, copper rod, planetary gesture, lemniscate, group ensemble

### 3. Spatial forms visible
e.g. lemniscate, circle, spiral, triangle, figure-of-eight

### 4. Musical interval or quality if apparent
e.g. fifth (open, wide), third (warm, intimate), major/minor quality

### 5. Venue or setting
Match to known venues above, or describe the space.

### 6. Any therapeutic or educational context evident
e.g. children present → pedagogical; one-to-one → therapeutic; stage lighting → performance

---

## RETURN JSON (STRICT — NO MARKDOWN):

{
    "summary": "Description of the session or image",
    "scene_type": "performance|class|therapeutic_session|rehearsal|community|other",

    "entities": [
        {
            "entity_type": "Practitioner|Specialism|Seek|Material|Venue",
            "name": "exact known entity name or descriptive label",
            "properties": {
                "description": "what is observed",
                "category": "if applicable",
                "role": "if a practitioner"
            },
            "confidence": 0.0
        }
    ],

    "relationships": [
        {
            "relationship_type": "PractitionerHasSpecialism|ParticipantSeeks|SurvivorFoundResource|PractitionerAtVenue|PractitionerCanSupport|SpecialismTreatsNeed",
            "source": "source entity name",
            "target": "target entity name",
            "properties": {},
            "confidence": 0.0
        }
    ],

    "broadcast_info": {
        "title": "suggested title for this session recording",
        "broadcast_type": "performance|session_note|therapeutic_record|community_update"
    },

    "spatial_forms": ["lemniscate", "circle"],
    "musical_qualities": ["interval of the fifth"]
}"""

    async def extract(self, gcs_uri: str, **kwargs) -> ExtractionResult:
        """Extract entities from image"""
        temp_path = None
        try:
            temp_path = self.gcs_service.download_to_temp(gcs_uri)
            image     = Image.open(temp_path)

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[self._get_extraction_prompt(), image],
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
                    entities.append(ExtractedEntity(
                        entity_type=EntityType(e['entity_type']),
                        name=e['name'],
                        properties=e.get('properties', {}),
                        confidence=e.get('confidence', 0.8),
                    ))
                except (ValueError, KeyError):
                    continue

            relationships = []
            for r in result_json.get('relationships', []):
                try:
                    relationships.append(ExtractedRelationship(
                        # BUG FIX 3: Old prompt listed "PractitionerFoundMaterial"
                        # and "SpecialismTreatsSeek" — neither exist as enum values.
                        # RelationshipType(value) raised ValueError and every
                        # relationship was silently dropped via the except block.
                        # Correct enum values are now in the prompt above.
                        relationship_type=RelationshipType(r['relationship_type']),
                        source_name=r['source'],
                        target_name=r['target'],
                        properties=r.get('properties', {}),
                        confidence=r.get('confidence', 0.8),
                    ))
                except (ValueError, KeyError):
                    continue

            return ExtractionResult(
                media_uri=gcs_uri,
                media_type="image",
                entities=entities,
                relationships=relationships,
                summary=result_json.get('summary', ''),
                broadcast_info=result_json.get('broadcast_info'),
                metadata={
                    'scene_type':      result_json.get('scene_type'),
                    'spatial_forms':   result_json.get('spatial_forms', []),
                    'musical_qualities': result_json.get('musical_qualities', []),
                    'image_size':      f"{image.width}x{image.height}",
                },
            )

        except Exception as e:
            logger.error(f"Image extraction failed: {e}")
            raise
        finally:
            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

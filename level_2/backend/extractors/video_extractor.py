import json
import logging
import os  
import time
from google import genai
from google.genai import types
from .base_extractor import (
    BaseExtractor, ExtractionResult, ExtractedEntity,
    ExtractedRelationship, EntityType, RelationshipType
)
from services.gcs_service import GCSService

logger = logging.getLogger(__name__)


class VideoExtractor(BaseExtractor):
    
    """Extract Community Eurythmy Network entities from video recordings"""

    def __init__(self):
        self.client = genai.Client(
            vertexai=True,
            project=os.getenv('PROJECT_ID'),
            location=os.getenv('REGION'),
        )
        self.model_name  = 'gemini-2.5-flash'
        self.gcs_service = GCSService()

    def _get_extraction_prompt(self) -> str:
        return """You are analysing a video recording from a Community Eurythmy session.
Current recording format: iPhone 17 video. No professional quality required.

Watch the entire video and identify:

## Known Practitioners (match by visual / audio cues where possible):
- Tomie Ando-Boadman — teacher / performer, Elmfield Steiner School, Stourbridge
- Marie-Reine — teacher, Christian Community tradition, speech and sacramental eurythmy
- Ursula Werner — therapist, Elysia Therapeutic Centre; copper rod, planetary gestures
- Eurythmy West Midlands Stage Group — ensemble, Glasshouse Arts Centre, Stourbridge

## Known Specialisms to look for:
Speech Eurythmy, Tone Eurythmy, Pedagogical Eurythmy, Therapeutic Eurythmy,
Copper Rod Eurythmy, Planetary Gesture (Saturn/Moon/Sun), Veil Eurythmy,
Interval Work (Fifth/Third), Lemniscate Forms, Group / Ensemble Eurythmy

## Extract across the full video:

1. **Practitioners/People**
   - Names spoken or visible, roles, interactions

2. **Specialisms demonstrated**
   - Eurythmy forms, gestures, instruments used (copper rod, silk veil…)
   - Who demonstrates what

3. **Spatial forms visible**
   - Lemniscate, circle, spiral, triangle, figure-of-eight

4. **Musical interval or quality**
   - Fifth (open, wide), third (warm), major/minor quality

5. **Venue or setting**
   - Match to known venues above, or describe the space

6. **Therapeutic or educational context**
   - Children present → pedagogical; one-to-one → therapeutic; stage → performance

7. **Spoken content**
   - Key messages, names, instructions, any text visible on screen

## Return JSON (no markdown):
{
    "summary": "Overall session summary",
    "scene_type": "performance|class|therapeutic_session|rehearsal|community|other",
    "duration_estimate": "estimated length",
    "key_moments": [
        {"time": "approximate timestamp", "event": "description"}
    ],
    "transcript_summary": "key spoken content",
    "spatial_forms": ["lemniscate", "circle"],
    "musical_qualities": ["interval of the fifth"],
    "entities": [
        {
            "entity_type": "Practitioner|Specialism|Seek|Material|Venue",
            "name": "entity name",
            "properties": {
                "description": "details",
                "first_seen": "when in video",
                "role": "if a practitioner",
                "category": "if a specialism or seek"
            },
            "confidence": 0.0
        }
    ],
    "relationships": [
        {
            "relationship_type": "PractitionerHasSpecialism|ParticipantSeeks|PractitionerFoundMaterial|PractitionerAtVenue|PractitionerCanSupport|SpecialismTreatsNeed",
            "source": "source entity name",
            "target": "target entity name",
            "properties": {},
            "confidence": 0.0
        }
    ],
    "broadcast_info": {
        "title": "suggested title",
        "broadcast_type": "performance|session_note|therapeutic_record|community_update",
        "duration_seconds": 0
    }
}"""

    async def extract(self, gcs_uri: str, **kwargs) -> ExtractionResult:
        """Extract entities from video"""
        temp_path  = None
        video_file = None

        try:
            temp_path = self.gcs_service.download_to_temp(gcs_uri)

            logger.info("Uploading video to Gemini File API for processing...")
            video_file = self.client.files.upload(path=temp_path)

            # Wait for Gemini to finish processing
            while video_file.state == types.FileState.PROCESSING:
                logger.info("Video processing — waiting 5 s...")
                time.sleep(5)
                video_file = self.client.files.get(name=video_file.name)

            if video_file.state == types.FileState.FAILED:
                raise Exception("Video processing failed in Gemini File API")

            response = self.client.models.generate_content(
                model=self.model_name,
                contents=[self._get_extraction_prompt(), video_file],
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
                        relationship_type=RelationshipType(r['relationship_type']),
                        source_name=r['source'],
                        target_name=r['target'],
                        properties=r.get('properties', {}),
                        confidence=r.get('confidence', 0.8),
                    ))
                except (ValueError, KeyError):
                    continue

            broadcast_info = result_json.get('broadcast_info', {})
            broadcast_info['transcript'] = result_json.get('transcript_summary', '')

            return ExtractionResult(
                media_uri=gcs_uri,
                media_type="video",
                entities=entities,
                relationships=relationships,
                raw_content=result_json.get('transcript_summary', ''),
                summary=result_json.get('summary', ''),
                broadcast_info=broadcast_info,
                metadata={
                    'scene_type':       result_json.get('scene_type'),
                    'duration_estimate': result_json.get('duration_estimate'),
                    'key_moments':      result_json.get('key_moments', []),
                    'spatial_forms':    result_json.get('spatial_forms', []),
                    'musical_qualities': result_json.get('musical_qualities', []),
                },
            )

        except Exception as e:
            logger.error(f"Video extraction failed: {e}")
            raise
        finally:
            # BUG FIX 4: Original finally block had a stray `pass` immediately
            # before `self.client.files.delete(...)` with a long comment implying
            # the delete might not run. The pass is a no-op so the delete did run,
            # but the misleading comment and structure have been cleaned up.
            if video_file:
                try:
                    self.client.files.delete(name=video_file.name)
                except Exception as cleanup_err:
                    logger.warning(f"Failed to delete remote Gemini file: {cleanup_err}")

            if temp_path and os.path.exists(temp_path):
                os.unlink(temp_path)

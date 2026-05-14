import uuid
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from google.cloud import spanner
from google.cloud.spanner_v1 import param_types
from extractors.base_extractor import (
    ExtractionResult, ExtractedEntity, ExtractedRelationship,
    EntityType, RelationshipType
)
import os

logger = logging.getLogger(__name__)

class SpannerGraphService:
    """Service to sync extracted data to Spanner Graph DB"""
    
    def __init__(self):
        self.client = spanner.Client(project=os.getenv('PROJECT_ID'))
        self.instance = self.client.instance(os.getenv('INSTANCE_ID'))
        self.database = self.instance.database(os.getenv('DATABASE_ID'))
        
        # Map EntityType to table info
        self.node_table_config = {
            EntityType.PRACTITIONER: {
                'table': 'Practitioners',
                'id_column': 'Practitioner_id',
                'name_column': 'name',
                 'role_colum': 'role',
                 'pillar_column': 'pillar',
                 'bio_column' : 'bio',
                 'venue_id_column' : 'venue_id',
                 'notes_column' : 'notes',
                # columns list is indicative, we dynamically check properties
            },
            EntityType.SPECIALISM: {
                'table': 'Specialisms',
                'id_column': 'specialism_id',
                'name_column': 'name',
                'category_column': 'category',
                'description_column': 'description',
                'pillar_column': 'pillar',
            },
            EntityType.SEEK: {
                'table': 'Seeks',
                'id_column': 'seek_id',
                'category_column': 'category',
                'description_column': 'description',
            },
            EntityType.MATERIAL: {
                'table': 'Materials',
                'id_column': 'material_id',
                'name_column': 'name',
            },
            EntityType.VENUE: {
                'table': 'Venues',
                'id_column': 'venue_id',
                'name_column': 'name',
                'location_column' : 'location',
                'type_column' : 'type',
                'pillar_column' : 'pillar',
                'notes_column' : 'notes',

            },
        }
        
        # Map RelationshipType to edge table info
        self.edge_table_config = {
            RelationshipType.HAS_SKILL: {
        'table': 'PractitionerHasSpecialism',
        'source_col': 'practitioner_id',
        'target_col': 'specialism_id',
        'source_type': EntityType.PRACTITIONER,
        'target_type': EntityType.SPECIALISM,
        'property_columns': ['proficiency']
    },

    RelationshipType.HAS_NEED: {
        'table': 'PractitionerHasSeek',
        'source_col': 'practitioner_id',
        'target_col': 'seek_id',
        'source_type': EntityType.PRACTITIONER,
        'target_type': EntityType.SEEK,
        'property_columns': ['status']
    },

    RelationshipType.FOUND_RESOURCE: {
        'table': 'PractitionerHasResource',
        'source_col': 'practitioner_id',
        'target_col': 'resource_id',
        'source_type': EntityType.PRACTITIONER,
        'target_type': EntityType.RESOURCE,
        'property_columns': ['found_at']
    },

    RelationshipType.IN_BIOME: {
        'table': 'PractitionerInVenue',
        'source_col': 'practitioner_id',
        'target_col': 'venue_id',
        'source_type': EntityType.PRACTITIONER,
        'target_type': EntityType.VENUE,
        'property_columns': []
    },
    
    RelationshipType.CAN_HELP: {
    'table': 'PractitionerCanHelp',
    'source_col': 'helper_id',
    'target_col': 'helpee_id',
    'source_type': EntityType.PRACTITIONER,
    'target_type': EntityType.PRACTITIONER,
    'property_columns': [
        'specialism_id',
        'seek_id',
        'reason',
        'match_score'
    ]
},

RelationshipType.TREATS: {
    'table': 'SpecialismAddressesSeek',
    'source_col': 'specialism_id',
    'target_col': 'seek_id',
    'source_type': EntityType.SPECIALISM,
    'target_type': EntityType.SEEK,
    'property_columns': ['effectiveness']
            }
        }
    
    def _generate_id(self) -> str:
        return str(uuid.uuid4())
    
    def _find_entity_by_name(self, transaction, entity_type: EntityType, name: str) -> Optional[str]:
        """Find entity ID by name, returns None if not found"""
        config = self.node_table_config[entity_type]
        
        # Use simple SQL select, assuming names are unique enough for this demo
        # Use LOWER for case-insensitive match
        query = f"SELECT {config['id_column']} FROM {config['table']} WHERE LOWER({config['name_column']}) = @name LIMIT 1"
        
        results = transaction.execute_sql(
            query,
            params={'name': name.lower()},
            param_types={'name': param_types.STRING}
        )
        
        rows = list(results)
        return rows[0][0] if rows else None
    
    def _create_entity(self, transaction, entity: ExtractedEntity) -> str:
        """Create new entity and return its ID"""
        config = self.node_table_config[entity.entity_type]
        entity_id = self._generate_id()
        
        columns = [config['id_column'], config['name_column']]
        values = [entity_id, entity.name]
        
        # Add basic properties if they exist in Entity properties
        # Note: In a real app, we'd validate against schema columns strictly.
        # Here we add common ones identified in our schema logic.
        
        # Mapping properties to columns
        # Survivor
        if entity.entity_type == EntityType.SURVIVOR:
            columns.append('created_at')
            values.append(datetime.utcnow())
            for k in ['callsign', 'role', 'status', 'biome', 'quadrant', 'description']:
                if k in entity.properties:
                    columns.append(k)
                    values.append(str(entity.properties[k]))
                    
        # Skill
        elif entity.entity_type == EntityType.SKILL:
            for k in ['category', 'description']:
                if k in entity.properties:
                    columns.append(k)
                    values.append(str(entity.properties[k]))
                    
        # Need
        elif entity.entity_type == EntityType.NEED:
            for k in ['category', 'urgency']:
                if k in entity.properties:
                    columns.append(k)
                    values.append(str(entity.properties[k]))
                    
        # Resource
        elif entity.entity_type == EntityType.RESOURCE:
            for k in ['type', 'description', 'biome']:
                if k in entity.properties:
                    columns.append(k)
                    values.append(str(entity.properties[k]))
                    
        # Biome
        elif entity.entity_type == EntityType.BIOME:
            for k in ['quadrant', 'description']:
                if k in entity.properties:
                    columns.append(k)
                    values.append(str(entity.properties[k]))
        
        transaction.insert(
            config['table'],
            columns=columns,
            values=[values]
        )
        return entity_id
    
    def _create_relationship(self, transaction, relationship: ExtractedRelationship,
                            entity_id_map: Dict[str, str]) -> bool:
        """Create edge between entities"""
        config = self.edge_table_config.get(relationship.relationship_type)
        if not config:
            return False
        
        source_id = entity_id_map.get(relationship.source_name)
        target_id = entity_id_map.get(relationship.target_name)
        
        if not source_id or not target_id:
            return False
        
        # Check existence
        check_query = f"""
            SELECT 1 FROM {config['table']}
            WHERE {config['source_col']} = @source_id 
            AND {config['target_col']} = @target_id
            LIMIT 1
        """
        results = list(transaction.execute_sql(
            check_query,
            params={'source_id': source_id, 'target_id': target_id},
            param_types={'source_id': param_types.STRING, 'target_id': param_types.STRING}
        ))
        
        if results:
            return True # Already exists
        
        columns = [config['source_col'], config['target_col']]
        values = [source_id, target_id]
        
        for k in config['property_columns']:
            if k in relationship.properties:
                columns.append(k)
                if k == 'found_at':
                    # Handle timestamp conversion if needed, or use string/commit_timestamp
                     values.append(datetime.utcnow()) 
                elif k == 'match_score':
                     values.append(float(relationship.properties[k]))
                else:
                     values.append(str(relationship.properties[k]))
                     
        transaction.insert(
            config['table'],
            columns=columns,
            values=[values]
        )
        return True
        
    def _create_broadcast(self, transaction, gcs_uri: str, extraction_result: ExtractionResult,
                         survivor_id: Optional[str] = None) -> str:
        broadcast_id = self._generate_id()
        info = extraction_result.broadcast_info or {}
        
        columns = ['broadcast_id', 'gcs_uri', 'processed', 'processed_at', 'created_at']
        values = [broadcast_id, gcs_uri, True, datetime.utcnow(), datetime.utcnow()]
        
        if survivor_id:
            columns.append('survivor_id')
            values.append(survivor_id)
            
        columns.append('title')
        values.append(info.get('title', f"Upload: {extraction_result.media_type}"))
        
        if 'broadcast_type' in info:
            columns.append('broadcast_type')
            values.append(info['broadcast_type'])
            
        if 'transcript' in info:
            columns.append('transcript')
            values.append(str(info['transcript'])[:10000]) # Limit
            
        if 'thumbnail_url' in info:
             columns.append('thumbnail_url')
             values.append(info['thumbnail_url'])

        if 'duration_seconds' in info and info['duration_seconds']:
             # Check if it's integer
             try:
                 dur = int(float(info['duration_seconds']))
                 columns.append('duration_seconds')
                 values.append(dur)
             except:
                 pass

        transaction.insert('Broadcasts', columns=columns, values=[values])
        return broadcast_id

    def save_extraction_result(self, extraction_result: ExtractionResult,
                               survivor_id: Optional[str] = None) -> Dict[str, Any]:
        """Save complete extraction result to Spanner Graph DB"""
        
        stats = {
            'entities_created': 0, 'entities_found_existing': 0,
            'relationships_created': 0, 'broadcast_id': None, 'errors': []
        }
        
        def transaction_work(transaction):
            entity_id_map = {}
            
            # 1. Process entities
            for entity in extraction_result.entities:
                try:
                    existing_id = self._find_entity_by_name(transaction, entity.entity_type, entity.name)
                    if existing_id:
                        entity_id_map[entity.name] = existing_id
                        stats['entities_found_existing'] += 1
                    else:
                        new_id = self._create_entity(transaction, entity)
                        entity_id_map[entity.name] = new_id
                        stats['entities_created'] += 1
                except Exception as e:
                    logger.error(f"Entity error {entity.name}: {e}")
            
            # 2. Process relationships
            for r in extraction_result.relationships:
                try:
                    # Resolve IDs if missing (try finding them in DB if not in current batch)
                    if r.source_name not in entity_id_map:
                         s_conf = self.node_table_config.get(self.edge_table_config[r.relationship_type]['source_type'])
                         # Just use generic find
                         # For now, skip if not found to avoid complexity
                         pass
                    
                    if self._create_relationship(transaction, r, entity_id_map):
                        stats['relationships_created'] += 1
                except Exception as e:
                    logger.error(f"Relationship error: {e}")
            
            # 3. Create broadcast
            try:
                b_survivor_id = survivor_id
                if not b_survivor_id:
                     # heuristic: pick first survivor found
                     for name, eid in entity_id_map.items():
                         # check if this name was a survivor. inefficient map but works
                         if any(e.name == name and e.entity_type == EntityType.SURVIVOR for e in extraction_result.entities):
                             b_survivor_id = eid
                             break
                
                # If still no survivor ID, use/create a default "Unknown Survivor"
                if not b_survivor_id:
                    unknown_name = "Unknown Survivor"
                    existing_id = self._find_entity_by_name(transaction, EntityType.SURVIVOR, unknown_name)
                    if existing_id:
                        b_survivor_id = existing_id
                    else:
                        # Create default
                        default_survivor = ExtractedEntity(
                            name=unknown_name, 
                            entity_type=EntityType.SURVIVOR,
                            properties={"status": "Unknown", "description": "System default for unassigned broadcasts"}
                        )
                        b_survivor_id = self._create_entity(transaction, default_survivor)
                        stats['entities_created'] += 1

                bid = self._create_broadcast(transaction, extraction_result.media_uri, extraction_result, b_survivor_id)
                stats['broadcast_id'] = bid
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

        try:
            self.database.run_in_transaction(transaction_work)
        except Exception as e:
             stats['errors'].append(str(e))
             logger.error(f"Transaction failed: {e}")
        
        return stats

    def query_graph(self, gql_query: str) -> List[Dict]:
        """Execute a GQL query on the graph"""
        with self.database.snapshot() as snapshot:
            results = snapshot.execute_sql(f"GRAPH {os.getenv('GRAPH_NAME')} {gql_query}")
            # Convert results to dicts
            out = []
            for row in results:
                # row is list-like, fields are in results.fields
                d = {}
                for idx, field in enumerate(results.fields):
                    d[field.name] = row[idx]
                out.append(d)
            return out

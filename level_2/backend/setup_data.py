"""
Eurythmy Community Database Setup Script
Run: python setup_database.py
Or:  python setup_database.py --project=your-project-id
"""

from google.cloud import spanner
from google.cloud.spanner_admin_instance_v1 import (
    Instance as InstancePB,
    CreateInstanceRequest,
)
from google.cloud.spanner_admin_database_v1.types import spanner_database_admin
import argparse
import time
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configuration - load from environment variables with defaults
INSTANCE_ID = os.getenv("INSTANCE_ID", "survivor-network")
DATABASE_ID = os.getenv("DATABASE_ID", "eurythmy-db")
GRAPH_NAME = os.getenv("GRAPH_NAME", "EurythmyGraph")
PROJECT_ID = os.getenv("PROJECT_ID", None)
REGION = os.getenv("REGION", "us-central1")

# DDL Statements
DDL_STATEMENTS = [
    # Node Tables
    """CREATE TABLE Venues (
        venue_id STRING(36) NOT NULL,
        name STRING(50) NOT NULL,
        location STRING(200),
        type STRING(50),
        pillar array<STRING(50)>,
        notes STRING(MAX)
    ) PRIMARY KEY (venue_id)""",
    
    """CREATE TABLE Specialisms (
        specialism_id STRING(36) NOT NULL,
        name STRING(100) NOT NULL,
        category STRING(50),
        description STRING(MAX),
        pillar array<STRING(50)>
    ) PRIMARY KEY (specialism_id)""",
    
    """CREATE TABLE Seeks (
        seek_id STRING(36) NOT NULL,
         name STRING(50),
         category STRING(50),
        description STRING(MAX) NOT NULL,
    ) PRIMARY KEY (seek_id)""",
    
    """CREATE TABLE Materials (
        material_id STRING(36) NOT NULL,
        name STRING(100) NOT NULL,
        type STRING(50),
        icon STRING(50),
        venue STRING(20),
        description STRING(MAX)
    ) PRIMARY KEY (material_id)""",
    
    """CREATE TABLE Practitioners (
        practitioner_id STRING(36) NOT NULL,
        name STRING(100),
        role STRING(50),
        pillar array<STRING(50)>,
        bio STRING(MAX),
        venue_id STRING(36),
        notes STRING(MAX),
        created_at TIMESTAMP
    ) PRIMARY KEY (practitioner_id)""",
    
    """CREATE TABLE Broadcasts (
        broadcast_id STRING(36) NOT NULL,
        practitioner_id STRING(36) NOT NULL,
        broadcast_type STRING(20),
        title STRING(200),
        gcs_uri STRING(500),
        thumbnail_url STRING(500),
        duration_seconds INT64,
        transcript STRING(MAX),
        processed BOOL,
        processed_at TIMESTAMP,
        created_at TIMESTAMP
    ) PRIMARY KEY (broadcast_id)""",
    
    # Edge Tables
    """CREATE TABLE PractitionerHasSpecialism (
        practitioner_id STRING(36) NOT NULL,
        specialism_id STRING(36) NOT NULL,
        level STRING(20)
    ) PRIMARY KEY (practitioner_id, specialism_id)""",
    
    """CREATE TABLE ParticipantSeeks (
        practitioner_id STRING(36) NOT NULL,
        seek_id STRING(36) NOT NULL,
        status STRING(20)
    ) PRIMARY KEY (practitioner_id, seek_id)""",
    
    """CREATE TABLE PractitionerFoundMaterial (
        practitioner_id STRING(36) NOT NULL,
        material_id STRING(36) NOT NULL,
        found_at TIMESTAMP
    ) PRIMARY KEY (practitioner_id, material_id)""",
    
    """CREATE TABLE PractitionerAtVenue (
        practitioner_id STRING(36) NOT NULL,
        venue_id STRING(36) NOT NULL
    ) PRIMARY KEY (practitioner_id, venue_id)""",
    
    """CREATE TABLE PractitionerCanSupport (
        supporter_id STRING(36) NOT NULL,
        supportee_id STRING(36) NOT NULL,
        reason STRING(MAX),
        match_score FLOAT64,
        specialism_id STRING(36),
        seek_id STRING(36)
    ) PRIMARY KEY (supporter_id, supportee_id)""",
    
    """CREATE TABLE SpecialismTreatsNeed (
        specialism_id STRING(36) NOT NULL,
        seek_id STRING(36) NOT NULL,
        strength STRING(50),
        notes STRING(MAX),

    ) PRIMARY KEY (specialism_id, seek_id)""",
]


def insert_data(database):
    """Insert all data into the database."""
    
    def insert_nodes(transaction):
        # Venues
        transaction.insert(
            "Venues",
            columns=["venue_id", "name", "location", "type", "pillar", "notes"],
            values=[
                ("V001", "Elmfield Steiner School", "Love Lane, Stourbridge, West Midlands DY8 2EA", "School / Performance Space", ["Education", "Art"], "Primary base for Tomie Ando-Boadman. Steiner Waldorf school with eurythmy hall."),
   
                ("V002", "The Christian Community, Stourbridge", "22 Baylie St, Stourbridge DY8 1AZ", "Congregation / Practice Space", ["Art", "Social", "Health"], "Base for Marie-Reine. Speech and sacramental eurythmy tradition."),
            
                ("V003", "Elysia Therapeutic Centre", "52 Bowling Green Rd, Stourbridge DY8 3RZ", "Therapeutic Practice", ["Health"], "Base for Ursula Werner. Therapeutic and curative eurythmy."),
            
                ("V004", "Glasshouse Arts Centre", "Stourbridge, West Midlands", "Arts Centre / Performance Venue", ["Art", "Social"], "Base for Eurythmy West Midlands Stage Group."),
            
                ("V005", "EthyOn Cafe", "Birmingham, West Midlands", "Community Hub", ["Social", "Education"], "Community hub for induction sessions and outreach."),
                            
            ]
        )
        
        # Specialisms
        transaction.insert(
            "Specialisms",
            columns=["specialism_id", "name", "category", "description", "pillar"],
            values=[
                ("S001", "Speech Eurythmy", "speech", "Making the sounds and rhythms of language visible through movement. Works with consonants, vowels, and poetic metre.", ["Art", "Education"]),
   
                ("S002", "Tone Eurythmy", "tone", "Translating musical intervals, melody, and rhythm into movement. Works with the inner life of music.", ["Art", "Education"]),
            
                ("S003", "Pedagogical Eurythmy", "pedagogical", "Eurythmy adapted for classroom and learning contexts. Supports child development and group learning.", ["Education"]),
            
                ("S004", "Therapeutic Eurythmy", "therapeutic", "Clinically applied eurythmy for therapeutic purposes. Works with specific conditions and individual treatment plans.", ["Health"]),
            
                ("S005", "Copper Rod Eurythmy", "therapeutic", "Use of copper rods as extensions of gesture. Grounds and focusses forces through the material quality of copper.", ["Health", "Art"]),
            
                ("S006", "Planetary Gesture — Saturn", "therapeutic", "The Saturn gesture works with consolidation, boundary, and structure. Downward, earthy, forming quality.", ["Health", "Art"]),
            
                ("S007", "Planetary Gesture — Moon", "therapeutic", "The Moon gesture works with fluid, reflective, and receptive qualities. Supports emotional regulation and dreaming.", ["Health", "Art"]),
            
                ("S008", "Planetary Gesture — Sun", "therapeutic", "The Sun gesture radiates warmth, openness, and presence. Works with vitality and heart forces.", ["Health", "Art"]),
            
                ("S009", "Veil Eurythmy", "performance", "Use of silk veils as extensions of movement. Works with breath, flow, and colour as living qualities.", ["Art", "Health"]),
            
                ("S010", "Interval Work — Fifth", "tone", "Movement that expresses the interval of the fifth. Quality of openness, wide horizons, and meditative space.", ["Art", "Health"]),
            
                ("S011", "Interval Work — Third", "tone", "Movement that expresses the interval of the third. Quality of warmth, internality, and gentle intimacy.", ["Art", "Health"]),
            
                ("S012", "Lemniscate Forms", "speech", "Figure-of-eight spatial forms. Works with polarity, balance, and integration of opposites.", ["Art", "Health", "Education"]),
            
                ("S013", "Christian Community Sacramental Eurythmy", "speech", "Eurythmy forms developed for use within Christian Community services and sacramental context.", ["Art", "Social"]),
            
                ("S014", "Group / Ensemble Eurythmy", "performance", "Coordinated movement for groups. Spatial forms, relationship between performers, and collective gesture.", ["Art", "Social"]),
            
                ("S015", "Goethean Observation", "science", "Scientific methodology based on Goethe's approach to nature. Colour as living phenomena, qualitative observation.", ["Tools", "Education"]),
            
                ("S016", "Piano Accompaniment for Eurythmy", "instrument", "Live piano support for eurythmy practice and performance. Responsive, not prescriptive musical partnership.", ["Art"]),
            ]
        )
        
        # Seeks
        transaction.insert(
            "Seeks",
            columns=["seek_id", "name", "category", "description"],
            values=[
                ("N001", "Grounding", "therapeutic", "A sense of physical presence, rootedness, and embodied calm."),
   
                ("N002", "Anxiety Support", "therapeutic", "Support for anxiety, nervousness, or overactive thinking."),
            
                ("N003", "Grief and Loss", "therapeutic", "Movement support during bereavement or emotional loss."),
            
                ("N004", "Language and Communication Support", "therapeutic", "Support for speech development, DLD, or communication challenges."),
            
                ("N005", "Emotional Regulation", "therapeutic", "Support for managing strong or fluctuating emotional states."),
            
                ("N006", "Vitality and Life Force", "therapeutic", "Fatigue, low energy, or depletion — seeking renewal."),
            
                ("N007", "Creative Expression", "artistic", "Desire to explore movement as an artistic and expressive medium."),
            
                ("N008", "Movement Learning", "educational", "Learning eurythmy as a new practice — beginner or developmental."),
            
                ("N009", "Boundary and Structure", "therapeutic", "Difficulty with personal boundaries, form-giving, or containment."),
            
                ("N010", "Community and Belonging", "social", "Seeking connection, shared practice, and communal experience."),
            
                ("N011", "Spiritual Inquiry", "social", "Exploring movement as a path of inner development or spiritual practice."),
            
                ("N012", "Performance Specialisms", "artistic", "Developing artistic quality for performance or presentation."),

            ]
        )
        
        # Materials
        transaction.insert(
            "Materials",
            columns=["material_id", "name", "type", "icon", "venue", "description"],
            values=[
                ("material_scores_intro", "Introduction to Eurythmy Scores", "score", "🎼", "Elmfield Steiner School", "Foundational eurythmy movement scores used for student learning and practice."),
                ("material_speech_recordings", "Speech Eurythmy Recordings", "recording", "🎤", "The Christian Community, Stourbridge", "Audio recordings for speech and sacramental eurythmy exercises."),
                ("material_therapy_guides", "Therapeutic Movement Guides", "score", "📘", "Elysia Therapeutic Centre", "Curative eurythmy guidance materials for therapeutic sessions."),
                ("material_stage_music", "Stage Performance Music", "recording", "🎵", "Glasshouse Arts Centre", "Performance music and rehearsal recordings for stage productions."),
                ("material_instruments_basic", "Basic Rhythm Instruments", "instrument", "🥁", "EthyOn Cafe", "Community instruments used for rhythm and movement workshops."),
                ("material_eurythmy_rods", "Eurythmy Copper Rods", "instrument", "🪄", "Elmfield Steiner School", "Traditional copper rods used in movement alignment exercises."),
                ("material_choral_recordings", "Choral Practice Recordings", "recording", "🎶", "Glasshouse Arts Centre", "Group vocal and movement synchronization recordings."),
                ("material_learning_manuals", "Eurythmy Learning Manuals", "score", "📚", "EthyOn Cafe", "Printed and digital manuals for introductory community sessions."),
            ]
        )
        
        # Practitioners
        timestamp = "2026-01-09T11:51:58.482898948Z"
        transaction.insert(
            "Practitioners",
            columns=["practitioner_id", "name", "role", "pillar", "bio", "venue_id", "notes", "created_at"],
            values=[
               ("P001", "Tomie Ando-Boadman", "teacher / performer", ["Art", "Education"], "Master-level eurythmy performer and teacher. Demonstrates the art of movement at the highest level.", "V001", "Key artist for Rhythmic Transmitters recordings.", timestamp),
   
                ("P002", "Marie-Reine", "teacher", ["Art", "Education", "Social"], "Eurythmy teacher working within the Christian Community tradition. Speech and tone eurythmy.", "V002", "First name only. Brings sacramental and speech eurythmy lineage.", timestamp),
            
                ("P003", "Ursula Werner", "therapist", ["Health"], "Qualified Eurythmy Therapist. Guides therapeutic applications including curative and supportive work.", "V003", "Primary therapeutic eurythmy contact for the project.", timestamp),
            
                ("P004", "Eurythmy West Midlands Stage Group", "ensemble / performer", ["Art", "Social"], "Performing ensemble offering performance knowledge and artistic guidance.", "V004", "Collective node — individual members to be added as graph grows.", timestamp),
            
                ("P005", "May", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
            
                ("P006", "Janet", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
            
                ("P007", "Haruko", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
                ("P008", "Chris", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
            
                ("P009", "Shelagh", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
            
                ("P010", "Ken", "student", ["Education", "Social"], "Community eurythmy participant.", "V005", "First name only.", timestamp),
            
                ("P011", "Carl Higgs", "musician", ["Art"], "Pianist. Provides live musical accompaniment for eurythmy sessions and recordings.", "V001", "Key collaborator for Rhythmic Transmitters performance recording.", timestamp),
            
                ("P012", "Dr Judyth Sassoon", "scientist", ["Tools", "Education"], "Goethean Scientist. Provides research methodology guidance on colour as living phenomena.", None, "Research collaborator — no fixed venue node yet.", timestamp),
            
                ("P013", "Dr Sehar Sajid", "artist / researcher", ["Art", "Tools"], "Visual Artist. Advises on translating movement into geometric organic forms.", None, "", timestamp),
            
                ("P014", "Adrian Large", "practitioner", ["Health"], "Body Treatments Practitioner. Contributes embodied practice knowledge.", None, "", timestamp),
            
                ("P015", "Pam Dhami", "organiser", ["Social"], "Marketing Consultant. Community outreach and engagement.", None, "", timestamp),
            
                ("P016", "Sam Alim", "organiser", ["Social"], "Community Organiser. Connects with underserved communities.", None, "", timestamp),
            
                ("P017", "Setsu Adachi","project lead / researcher", ["Tools", "Social"], "Project Lead, Rhythmic Transmitters. Creative technology researcher and community organiser.", "V005", "WhatsOn Agency / Metro Pages Ltd", timestamp),
            ]
        )
    
    def insert_edges(transaction):
        # PractitionerHasSpecialism
        transaction.insert(
            "PractitionerHasSpecialism",
            columns=["practitioner_id", "specialism_id", "level"],
            values=[
                  ("P001", "S001", "master"),
                    ("P001", "S002", "master"),
                    ("P001", "S003", "master"),
                    ("P001", "S014", "master"),
                    ("P001", "S009", "qualified"),
                    ("P002", "S001", "qualified"),
                    ("P002", "S013", "qualified"),
                    ("P002", "S002", "qualified"),
                    ("P002", "S014", "qualified"),
                    ("P003", "S004", "qualified"),
                    ("P003", "S005", "qualified"),
                    ("P003", "S006", "qualified"),
                    ("P003", "S007", "qualified"),
                    ("P003", "S008", "qualified"),
                    ("P004", "S014", "qualified"),
                    ("P004", "S002", "qualified"),
                    ("P004", "S009", "qualified"),
                    ("P005", "S001", "developing"),
                    ("P005", "S002", "developing"),
                    ("P006", "S001", "developing"),
                    ("P007", "S002", "developing"),
                    ("P008", "S001", "developing"),
                    ("P009", "S001", "developing"),
                    ("P010", "S002", "developing"),
                    ("P011", "S016", "qualified"),
                    ("P012", "S015", "qualified")
            ]
        )
        
        # ParticipantSeeks
        transaction.insert(
            "ParticipantSeeks",
            columns=["practitioner_id", "seek_id", "status"],
            values=[
        ("P005", "N008", "active"),  # May → Movement Learning
        ("P005", "N010", "active"),  # May → Community and Belonging

        ("P006", "N008", "active"),  # Janet → Movement Learning
        ("P006", "N005", "active"),  # Janet → Emotional Regulation

        ("P007", "N011", "active"),  # Haruko → Spiritual Inquiry
        ("P007", "N007", "active"),  # Haruko → Creative Expression

        ("P008", "N007", "active"),  # Chris → Creative Expression
        ("P008", "N010", "active"),  # Chris → Community and Belonging

        ("P009", "N003", "active"),  # Shelagh → Grief and Loss
        ("P009", "N002", "active"),  # Shelagh → Anxiety Support

        ("P010", "N001", "active"),  # Ken → Grounding
        ("P010", "N009", "active"),  # Ken → Boundary and Structure

        ("P017", "N010", "active"),  # Setsu Adachi → Community and Belonging
        ("P017", "N011", "active"),  # Setsu Adachi → Spiritual Inquiry
        ("P017", "N007", "active"),  # Setsu Adachi → Creative Expression
    ]
        )
        
        # PractitionerFoundMaterial
        found_timestamp = "2026-01-09T11:52:17.437279487Z"
        transaction.insert(
            "PractitionerFoundMaterial",
            columns=["practitioner_id", "material_id", "found_at"],
            values=[
        ("P001", "material_scores_intro", found_timestamp),         # Tomie Ando-Boadman
        ("P002", "material_speech_recordings", found_timestamp),   # Marie-Reine
        ("P003", "material_therapy_guides", found_timestamp),      # Ursula Werner
        ("P003", "material_learning_manuals", found_timestamp),    # Ursula Werner
        ("P004", "material_stage_music", found_timestamp),         # Eurythmy West Midlands Stage Group
        ("P011", "material_eurythmy_rods", found_timestamp),       # Carl Higgs
        ("P012", "material_choral_recordings", found_timestamp),   # Dr Judyth Sassoon
        ("P017", "material_instruments_basic", found_timestamp),   # Setsu Adachi
    ]
        )

        # PractitionerAtVenue
        transaction.insert(
            "PractitionerAtVenue",
            columns=["practitioner_id", "venue_id"],
            values=[
        ("P001", "V001"),  # Tomie Ando-Boadman → Elmfield Steiner School
        ("P002", "V002"),  # Marie-Reine → The Christian Community
        ("P003", "V003"),  # Ursula Werner → Elysia Therapeutic Centre
        ("P004", "V004"),  # Eurythmy West Midlands Stage Group → Glasshouse Arts Centre

        ("P005", "V005"),  # May → EthyOn Cafe
        ("P006", "V005"),  # Janet → EthyOn Cafe
        ("P007", "V005"),  # Haruko → EthyOn Cafe
        ("P008", "V005"),  # Chris → EthyOn Cafe
        ("P009", "V005"),  # Shelagh → EthyOn Cafe
        ("P010", "V005"),  # Ken → EthyOn Cafe

        ("P011", "V001"),  # Carl Higgs → Elmfield Steiner School

        ("P017", "V005"),  # Setsu Adachi → EthyOn Cafe
    ]
        )
        
        # PractitionerCanSupport
        transaction.insert(
            "PractitionerCanSupport",
            columns=["supporter_id", "supportee_id", "reason", "match_score", "specialism_id", "seek_id"],
            values=[
        (
            "P003",  # Ursula Werner (Therapeutic Eurythmy)
            "P010",  # Ken
            "Therapeutic eurythmy supports grounding and structure",
            0.78,
            "S004",  # Therapeutic Eurythmy
            "N009"   # Boundary and Structure
        ),
        (
            "P003",  # Ursula Werner
            "P009",  # Shelagh
            "Supports emotional regulation and grief processing",
            0.86,
            "S007",  # Moon Gesture / emotional work
            "N003"   # Grief and Loss
        ),
        (
            "P011",  # Carl Higgs (musician)
            "P008",  # Chris
            "Music accompaniment supports creative expression",
            0.72,
            "S016",  # Piano Accompaniment
            "N007"   # Creative Expression
        ),
    ]
        )
        
        # SpecialismTreatsNeed
        transaction.insert(
            "SpecialismTreatsNeed",
            columns=["specialism_id", "seek_id", 'strength', 'notes'],
            values=[
        ("S005", "N001", "primary", "Copper rod eurythmy directly grounds physical forces."),
        ("S005", "N009", "primary", "Supports boundary formation through structured copper gestures."),
        ("S005", "N002", "secondary", "Anchoring effect reduces anxiety through physical grounding."),

        ("S006", "N009", "primary", "Saturn gesture strengthens consolidation and boundary capacity."),
        ("S006", "N001", "primary", "Downward Saturn quality supports grounding and structure."),

        ("S007", "N005", "primary", "Moon gesture supports emotional regulation through fluid movement."),
        ("S007", "N003", "secondary", "Fluid Moon quality allows safe expression of grief."),

        ("S008", "N006", "primary", "Sun gesture restores vitality and life force."),
        ("S008", "N007", "secondary", "Radiant Sun quality supports creative expression."),

        ("S009", "N002", "primary", "Veil work calms anxiety through breath-led flow."),
        ("S009", "N003", "primary", "Flowing veil movement supports grief processing."),
        ("S009", "N007", "secondary", "Veil movement enhances artistic expression."),

        ("S010", "N011", "primary", "Fifth interval creates meditative, expansive consciousness."),
        ("S010", "N002", "secondary", "Expansive interval distance reduces anxious thought loops."),

        ("S011", "N003", "primary", "Third interval provides warmth and emotional holding."),
        ("S011", "N010", "primary", "Warm tonal quality supports belonging and connection."),

        ("S012", "N005", "primary", "Lemniscate movement integrates emotional polarity and balance."),
        ("S012", "N001", "secondary", "Rhythmic figure-of-eight supports grounding and centering."),

        ("S001", "N004", "primary", "Speech eurythmy makes language visible and supports communication development."),
        ("S001", "N008", "primary", "Core learning pathway for eurythmy practice."),

        ("S002", "N007", "primary", "Tone eurythmy enables artistic musical expression."),
        ("S002", "N006", "secondary", "Musical movement revitalizes energy and life force."),

        ("S014", "N010", "primary", "Group eurythmy builds belonging through shared spatial forms."),
        ("S014", "N012", "primary", "Ensemble work develops performance capability."),

        ("S004", "N002", "primary", "Therapeutic eurythmy supports anxiety regulation."),
        ("S004", "N003", "primary", "Supports grief and emotional processing."),
        ("S004", "N004", "primary", "Supports communication and speech development."),
        ("S004", "N005", "primary", "Helps regulate emotional imbalance."),
        ("S004", "N006", "primary", "Restores vitality and life force."),
        ("S004", "N009", "primary", "Strengthens boundaries and structural integration."),

        ("S003", "N008", "primary", "Pedagogical eurythmy supports learning and development."),
        ("S003", "N010", "secondary", "Group learning context fosters belonging and social connection."),
    ]
        )
    
    print("Inserting node data...")
    database.run_in_transaction(insert_nodes)
    print("Inserting edge data...")
    database.run_in_transaction(insert_edges)
    print("Data insertion complete!")


def create_graphs(database, graph_name):
    """Create property graphs."""
    
    graph1_ddl = f"""
    CREATE OR REPLACE PROPERTY GRAPH {graph_name}
      NODE TABLES (
        Venues KEY (venue_id) LABEL venue PROPERTIES (venue_id, name, location, type, pillar, notes),
        Practitioners KEY (practitioner_id) LABEL practitioner PROPERTIES (practitioner_id, name, role, pillar, bio, venue_id, notes, created_at),
        Seeks KEY (seek_id) LABEL Need PROPERTIES (seek_id, name, category, description),
        Materials KEY (material_id) LABEL Material PROPERTIES (material_id, name, type, icon, venue, description),
        Specialisms KEY (specialism_id) LABEL Specialism PROPERTIES (specialism_id, name, category, description, pillar),
      )
      EDGE TABLES (
        PractitionerHasSpecialism KEY (practitioner_id, specialism_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (specialism_id) REFERENCES Specialisms (specialism_id) LABEL HAS_Specialism PROPERTIES (level),
        ParticipantSeeks KEY (practitioner_id, seek_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (seek_id) REFERENCES Seeks (seek_id) LABEL HAS_SEEK PROPERTIES (status),
        PractitionerFoundMaterial KEY (practitioner_id, material_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (material_id) REFERENCES Materials (material_id) LABEL FOUND PROPERTIES (found_at),
        PractitionerAtVenue KEY (practitioner_id, venue_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (venue_id) REFERENCES Venues (venue_id) LABEL IN_venue PROPERTIES (practitioner_id, venue_id),
        PractitionerCanSupport KEY (supporter_id, supportee_id) SOURCE KEY (supporter_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (supportee_id) REFERENCES Practitioners (practitioner_id) LABEL CAN_HELP PROPERTIES (reason, match_score, specialism_id, seek_id),
        SpecialismTreatsNeed KEY (specialism_id, seek_id) SOURCE KEY (specialism_id) REFERENCES Specialisms (specialism_id) DESTINATION KEY (seek_id) REFERENCES Seeks (seek_id) LABEL TREATS PROPERTIES ( strength, notes)
      )
    """
    
    graph2_ddl = """
    CREATE OR REPLACE PROPERTY GRAPH EurythmyCommunity
      NODE TABLES (
        Venues KEY (venue_id) LABEL Venues PROPERTIES (venue_id, name, location, type, pillar, notes),
        Broadcasts KEY (broadcast_id) LABEL Broadcasts PROPERTIES (broadcast_id, practitioner_id, broadcast_type, title, gcs_uri, thumbnail_url, duration_seconds, transcript, processed, processed_at, created_at),
        Seeks KEY (seek_id) LABEL Seeks PROPERTIES (seek_id, name, category, description),
        Materials KEY (material_id) LABEL Materials PROPERTIES (material_id, name, type, icon, venue, description),
        Specialisms KEY (specialism_id) LABEL Specialisms PROPERTIES (specialism_id, name, category, description, pillar),
        Practitioners KEY (practitioner_id) LABEL Practitioners PROPERTIES (practitioner_id, name, role, pillar, bio, venue_id, notes, created_at)
      )
      EDGE TABLES (
        PractitionerHasSpecialism KEY (practitioner_id, specialism_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (specialism_id) REFERENCES Specialisms (specialism_id) LABEL PractitionerHasSpecialism PROPERTIES (practitioner_id, specialism_id, level),
        ParticipantSeeks KEY (practitioner_id, seek_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (seek_id) REFERENCES Seeks (seek_id) LABEL ParticipantSeeks PROPERTIES (practitioner_id, seek_id, status),
        PractitionerFoundMaterial KEY (practitioner_id, material_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (material_id) REFERENCES Materials (material_id) LABEL PractitionerFoundMaterial PROPERTIES (practitioner_id, material_id, found_at),
        PractitionerAtVenue KEY (practitioner_id, venue_id) SOURCE KEY (practitioner_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (venue_id) REFERENCES Venues (venue_id) LABEL PractitionerAtVenue PROPERTIES (practitioner_id, venue_id),
        PractitionerCanSupport KEY (supporter_id, supportee_id) SOURCE KEY (supporter_id) REFERENCES Practitioners (practitioner_id) DESTINATION KEY (supportee_id) REFERENCES Practitioners (practitioner_id) LABEL PractitionerCanSupport PROPERTIES (supporter_id, supportee_id, reason, match_score, specialism_id, seek_id),
        SpecialismTreatsNeed KEY (specialism_id, seek_id) SOURCE KEY (specialism_id) REFERENCES Specialisms (specialism_id) DESTINATION KEY (seek_id) REFERENCES Seeks (seek_id) LABEL SpecialismTreatsNeed PROPERTIES (specialism_id, seek_id, strength, notes)
      )
    """
    
    print(f"Creating {graph_name}...")
    operation = database.update_ddl([graph1_ddl])
    operation.result()
    
    print("Creating EurythmyCommunity...")
    operation = database.update_ddl([graph2_ddl])
    operation.result()
    
    print("Graphs created!")


def create_instance_with_enterprise(client, project_id, instance_id, region):
    """Create a Spanner instance with ENTERPRISE edition using the admin API."""
    config_name = f"projects/{project_id}/instanceConfigs/regional-{region}"
    instance_name = f"projects/{project_id}/instances/{instance_id}"
    
    instance_admin_client = client.instance_admin_api
    
    instance_pb = InstancePB(
        name=instance_name,
        config=config_name,
        display_name="Eurythmy Community",
        processing_units=100,
        edition=InstancePB.Edition.ENTERPRISE,
    )
    
    request = CreateInstanceRequest(
        parent=f"projects/{project_id}",
        instance_id=instance_id,
        instance=instance_pb,
    )
    
    operation = instance_admin_client.create_instance(request=request)
    return operation


def print_config():
    """Print current configuration."""
    print("\n" + "=" * 60)
    print("Current Configuration (from environment):")
    print("=" * 60)
    print(f"  PROJECT_ID:   {PROJECT_ID or 'Not set (use --project flag)'}")
    print(f"  INSTANCE_ID:  {INSTANCE_ID}")
    print(f"  DATABASE_ID:  {DATABASE_ID}")
    print(f"  GRAPH_NAME:   {GRAPH_NAME}")
    print(f"  REGION:       {REGION}")
    print("=" * 60 + "\n")


def main():
    parser = argparse.ArgumentParser(description='Setup Eurythmy Community Database')
    parser.add_argument('--project', help='Google Cloud Project ID (overrides PROJECT_ID env var)')
    parser.add_argument('--instance', help='Spanner Instance ID (overrides INSTANCE_ID env var)')
    parser.add_argument('--database', help='Spanner Database ID (overrides DATABASE_ID env var)')
    parser.add_argument('--graph', help='Graph name (overrides GRAPH_NAME env var)')
    parser.add_argument('--region', help='GCP Region (overrides REGION env var)')
    parser.add_argument('--skip-instance', action='store_true', help='Skip instance creation (if exists)')
    parser.add_argument('--force', action='store_true', help='Delete and recreate database if exists')
    parser.add_argument('--show-config', action='store_true', help='Show current configuration and exit')
    args = parser.parse_args()
    
    # Use command line args or fall back to environment variables
    project_id = args.project or PROJECT_ID
    instance_id = args.instance or INSTANCE_ID
    database_id = args.database or DATABASE_ID
    graph_name = args.graph or GRAPH_NAME
    region = args.region or REGION
    
    # Show config if requested
    if args.show_config:
        print_config()
        return
    
    # Validate project_id
    if not project_id:
        print("ERROR: PROJECT_ID is required.")
        print("Set it via:")
        print("  1. Environment variable: export PROJECT_ID=your-project-id")
        print("  2. .env file: PROJECT_ID=your-project-id")
        print("  3. Command line: python setup_database.py --project=your-project-id")
        return
    
    print("\n" + "=" * 60)
    print("Eurythmy Community Database Setup")
    print("=" * 60)
    print(f"  Project:   {project_id}")
    print(f"  Instance:  {instance_id}")
    print(f"  Database:  {database_id}")
    print(f"  Graph:     {graph_name}")
    print(f"  Region:    {region}")
    print("=" * 60 + "\n")
    
    client = spanner.Client(project=project_id)
    
    # Get instance reference and check if it exists
    instance = client.instance(instance_id)
    instance_exists = instance.exists()
    
    if instance_exists:
        print(f"Instance {instance_id} already exists. Using existing instance.")
    elif not args.skip_instance:
        print(f"Creating instance {instance_id} with ENTERPRISE edition...")
        operation = create_instance_with_enterprise(client, project_id, instance_id, region)
        print("Waiting for instance creation (this may take a few minutes)...")
        operation.result()
        print("Instance created!")
        # Refresh instance reference
        instance = client.instance(instance_id)
    else:
        print("ERROR: Instance does not exist and --skip-instance was specified.")
        return
    
    # Check if database exists
    database = instance.database(database_id)
    database_exists = database.exists()
    
    if database_exists:
        if args.force:
            print(f"Database {database_id} exists. Deleting (--force specified)...")
            database.drop()
            print("Database deleted. Waiting 5 seconds...")
            time.sleep(5)
        else:
            print(f"Database {database_id} already exists.")
            print("Use --force to delete and recreate it.")
            print(f"\nAccess your existing database at:")
            print(f"https://console.cloud.google.com/spanner/instances/{instance_id}/databases/{database_id}?project={project_id}")
            return
    
    # Create database with schema
    print(f"Creating database {database_id} with schema...")
    database = instance.database(database_id, ddl_statements=DDL_STATEMENTS)
    operation = database.create()
    operation.result()
    print("Database and tables created!")
    
    # Insert data
    database = instance.database(database_id)
    insert_data(database)
    
    # Create graphs
    create_graphs(database, graph_name)
    
    print("\n" + "=" * 60)
    print("SUCCESS! Database setup complete.")
    print("=" * 60)
    print(f"\nInstance:  {instance_id}")
    print(f"Database:  {database_id}")
    print(f"Graph:     {graph_name}")
    print(f"\nAccess your database at:")
    print(f"https://console.cloud.google.com/spanner/instances/{instance_id}/databases/{database_id}?project={project_id}")


if __name__ == "__main__":
    main()
    # Force exit to prevent annoying Google Cloud Spanner metrics export errors on shutdown
    # regarding "One or more points were written more frequently..."
    os._exit(0)

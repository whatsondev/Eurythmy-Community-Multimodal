
import os
import logging
from dotenv import load_dotenv
import vertexai
from vertexai.preview import reasoning_engines

# Import class-based types for Memory Bank
from vertexai import types
from google.genai import types as genai_types

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

load_dotenv()

PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION   = os.getenv("LOCATION", "us-central1")
AGENT_DISPLAY_NAME = "eurythmy_network_agent_engine"

if not PROJECT_ID:
    raise ValueError("PROJECT_ID not found in environment variables.")

# Basic configuration types
MemoryBankConfig         = types.ReasoningEngineContextSpecMemoryBankConfig
SimilaritySearchConfig   = types.ReasoningEngineContextSpecMemoryBankConfigSimilaritySearchConfig
GenerationConfig         = types.ReasoningEngineContextSpecMemoryBankConfigGenerationConfig

# Advanced configuration types
CustomizationConfig      = types.MemoryBankCustomizationConfig
MemoryTopic              = types.MemoryBankCustomizationConfigMemoryTopic
CustomMemoryTopic        = types.MemoryBankCustomizationConfigMemoryTopicCustomMemoryTopic
GenerateMemoriesExample  = types.MemoryBankCustomizationConfigGenerateMemoriesExample
ConversationSource       = types.MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSource
ConversationSourceEvent  = types.MemoryBankCustomizationConfigGenerateMemoriesExampleConversationSourceEvent
ExampleGeneratedMemory   = types.MemoryBankCustomizationConfigGenerateMemoriesExampleGeneratedMemory
Content = genai_types.Content
Part    = genai_types.Part


def register_agent_engine():
    """
    Registers an Agent Engine resource in Vertex AI to enable Sessions and Memory Bank.
    This does NOT deploy the agent code to the cloud.
    """
    logger.info(f"Initialising Vertex AI for project: {PROJECT_ID}, location: {LOCATION}")
    vertexai.init(project=PROJECT_ID, location=LOCATION)
    client = vertexai.Client(project=PROJECT_ID, location=LOCATION)

    # --- Define Custom Topics ---
    logger.info("Defining custom topics...")

    # BUG FIX 1: Topics still used codelab language (Survivors, Biomes, Specialisms
    #            as "Skills", geographic biomes like "Swamp Biome" / "Mountain Outpost").
    #            Replaced with eurythmy-appropriate topics and examples.
    custom_topics = [
        # Topic 1: Practitioner Search Preferences
        MemoryTopic(
            custom_memory_topic=CustomMemoryTopic(
                label="search_preferences",
                description="""Extract the user's preferences for how they search for practitioners and specialisms. Include:
                - Preferred search methods (semantic, keyword, hybrid)
                - Common filters used (venue, role, pillar)
                - Specific specialisms they value or frequently look for
                  (e.g. therapeutic eurythmy, veil work, speech eurythmy)
                - Geographic areas of interest (e.g. "Stourbridge", "Birmingham",
                  "West Midlands")
                - Pillars of interest (Art, Health, Education, Social)

                Example: "User prefers semantic search for finding therapeutic specialisms."
                Example: "User frequently asks about practitioners at Elmfield."
                """,
            )
        ),
        # Topic 2: Therapeutic and Community Context
        MemoryTopic(
            custom_memory_topic=CustomMemoryTopic(
                label="therapeutic_community_context",
                description="""Track the user's therapeutic needs or community interests they have mentioned. Include:
                - Specific Seeks (needs) they are exploring (e.g. anxiety, grief, grounding)
                - Practitioners or venues they are particularly interested in
                - Pillars they are working within (Health, Education, Art, Social)
                - Any context about who they are searching for
                  (themselves, a child, a group, a community project)

                Example: "User is looking for therapeutic eurythmy support for anxiety."
                Example: "User is interested in group eurythmy for community building."
                Example: "User is researching on behalf of a Steiner school."
                """,
            )
        ),
    ]

    # --- Define Few-Shot Examples ---
    logger.info("Defining few-shot examples...")

    # BUG FIX 2: Few-shot examples used codelab scenario language
    #            ("wound treatment", "Old Hospital", "Sector 7", "Bunker",
    #            "Medical Supplies", "Food").  Replaced with eurythmy-relevant
    #            conversations matching the agent's actual domain.
    few_shot_examples = [
        GenerateMemoriesExample(
            conversation_source=ConversationSource(
                events=[
                    ConversationSourceEvent(
                        content=Content(
                            role="user",
                            parts=[Part(text="I want to find something to help with anxiety — I prefer searching by meaning rather than exact words.")]
                        )
                    ),
                    ConversationSourceEvent(
                        content=Content(
                            role="model",
                            parts=[Part(text="I'll use semantic search to find specialisms and practitioners that address anxiety. Veil eurythmy and copper rod work both come up strongly for this.")]
                        )
                    ),
                    ConversationSourceEvent(
                        content=Content(
                            role="user",
                            parts=[Part(text="Great. Also, I'm specifically interested in what's available in Stourbridge.")]
                        )
                    ),
                ]
            ),
            generated_memories=[
                ExampleGeneratedMemory(fact="User prefers semantic search for finding specialisms"),
                ExampleGeneratedMemory(fact="User is looking for support with anxiety"),
                ExampleGeneratedMemory(fact="User is interested in practitioners and venues in Stourbridge"),
            ]
        ),
        GenerateMemoriesExample(
            conversation_source=ConversationSource(
                events=[
                    ConversationSourceEvent(
                        content=Content(
                            role="user",
                            parts=[Part(text="What therapeutic eurythmy options are available in the West Midlands?")]
                        )
                    ),
                    ConversationSourceEvent(
                        content=Content(
                            role="model",
                            parts=[Part(text="Ursula Werner at the Elysia Therapeutic Centre in Stourbridge is the primary therapeutic eurythmy practitioner in the network. She works with copper rod eurythmy, planetary gestures, and general therapeutic eurythmy.")]
                        )
                    ),
                    ConversationSourceEvent(
                        content=Content(
                            role="user",
                            parts=[Part(text="That's helpful — I'm particularly interested in support for grief and emotional regulation.")]
                        )
                    ),
                ]
            ),
            generated_memories=[
                ExampleGeneratedMemory(fact="User is exploring therapeutic eurythmy in the West Midlands"),
                ExampleGeneratedMemory(fact="User has a specific interest in support for grief"),
                ExampleGeneratedMemory(fact="User is interested in emotional regulation support"),
            ]
        ),
    ]

    # --- Create Customization Config ---
    customization_config = CustomizationConfig(
        memory_topics=custom_topics,
        generate_memories_examples=few_shot_examples,
    )

    logger.info(f"Creating/Registering Agent Engine: {AGENT_DISPLAY_NAME}")

    agent_engine = client.agent_engines.create(
        config={
            "display_name": AGENT_DISPLAY_NAME,
            "context_spec": {
                "memory_bank_config": {
                    "generation_config": {
                        "model": f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/gemini-2.5-flash"
                    },
                    "customization_configs": [customization_config],
                }
            },
        }
    )

    agent_engine_id = agent_engine.api_resource.name.split("/")[-1]
    logger.info("✅ Agent Engine Registered Successfully!")
    logger.info(f"Agent Engine ID: {agent_engine_id}")
    logger.info("\nIMPORTANT: Add the following line to your backend/.env file:")
    logger.info(f"AGENT_ENGINE_ID={agent_engine_id}")


if __name__ == "__main__":
    try:
        register_agent_engine()
    except Exception as e:
        logger.error(f"Failed to register Agent Engine: {e}")

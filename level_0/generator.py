"""
Level 0: Avatar Generator

This module generates your unique space explorer avatar using
multi-turn image generation with Gemini (Nano Banana) for
character consistency across portrait and icon.

=== CODELAB INSTRUCTIONS ===

You will implement three steps in the generate_explorer_avatar() function:

1. MODULE_5_STEP_1_CREATE_CHAT_SESSION
   Create a chat session to maintain character consistency

2. MODULE_5_STEP_2_GENERATE_PORTRAIT
   Generate the explorer portrait with your customizations

3. MODULE_5_STEP_3_GENERATE_ICON
   Generate a consistent map icon using the same chat session

Follow the instructions in the codelab to complete each step.
"""

from google import genai
from google.genai import types
from PIL import Image
import json
import os
import io

# Load configuration from setup (config.json is in project root)
CONFIG_PATH = "../config.json"

with open(CONFIG_PATH) as f:
    config = json.load(f)

USERNAME = config["username"]
SUIT_COLOR = config["suit_color"]
APPEARANCE = config["appearance"]

# Initialize the Gemini client for Vertex AI
client = genai.Client(
    vertexai=True,
    project=os.environ.get("GOOGLE_CLOUD_PROJECT", config.get("project_id")),
    location="us-central1"
)


def generate_explorer_avatar() -> dict:
    """
    Generate portrait and icon using multi-turn chat for consistency.

    The key technique here is using a CHAT SESSION rather than independent
    API calls. This allows Gemini to "remember" the character it created
    in the first turn, ensuring the icon matches the portrait.

    Returns:
        dict with portrait_path and icon_path
    """

    # =========================================================================
    # MODULE_5_STEP_1_CREATE_CHAT_SESSION
    # =========================================================================
    # TODO: Create a chat session for multi-turn generation
    #
    # Create a chat session using client.chats.create() with:
    # - model: "gemini-2.5-flash-image" (Nano Banana)
    # - config: GenerateContentConfig with response_modalities=["TEXT", "IMAGE"]
    #
    # Hint: You need to use types.GenerateContentConfig
    # =========================================================================
    chat = None # Replace this line

    # =========================================================================
    # MODULE_5_STEP_2_GENERATE_PORTRAIT
    # =========================================================================
    # TODO: Generate the explorer portrait
    #
    # 1. Create a portrait_prompt string that includes:
    #    - APPEARANCE, USERNAME, and SUIT_COLOR variables
    #    - Style requirements (digital illustration, white background, etc.)
    #
    # 2. Send the prompt using chat.send_message(portrait_prompt)
    #
    # 3. Extract the image from the response:
    #    - Loop through portrait_response.candidates[0].content.parts
    #    - Find the part where part.inline_data is not None
    #    - Convert to PIL Image: Image.open(io.BytesIO(part.inline_data.data))
    #    - Save to "outputs/portrait.png"
    #
    # 4. Print progress messages for user feedback
    # =========================================================================
    portrait_image = None # Replace this section

    # =========================================================================
    # MODULE_5_STEP_3_GENERATE_ICON
    # =========================================================================
    # TODO: Generate a consistent map icon
    #
    # 1. Create an icon_prompt that asks for the SAME character
    #    - Emphasize consistency: "SAME person, SAME face, SAME suit"
    #    - Request tighter crop (head and shoulders only)
    #    - Request white background and square aspect ratio
    #
    # 2. Send the prompt using chat.send_message(icon_prompt)
    #    - The chat session remembers the character from step 2!
    #
    # 3. Extract and save the icon image to "outputs/icon.png"
    #
    # 4. Print progress messages for user feedback
    # =========================================================================
    icon_image = None # Replace this section

    return {
        "portrait_path": "outputs/portrait.png",
        "icon_path": "outputs/icon.png"
    }


if __name__ == "__main__":
    # Create outputs directory if it doesn't exist
    os.makedirs("outputs", exist_ok=True)

    print(f"Generating avatar for {USERNAME}...")
    result = generate_explorer_avatar()
    print(f"✅ Avatar created!")
    print(f"   Portrait: {result['portrait_path']}")
    print(f"   Icon: {result['icon_path']}")

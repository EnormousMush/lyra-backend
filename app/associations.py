"""
associations.py — Use Claude to generate vivid synesthetic scene associations
from extracted audio features.
"""

import os
import json
from anthropic import Anthropic

client = Anthropic()

SYSTEM_PROMPT = """You are a synesthetic artist — someone who involuntarily experiences music as vivid visual scenes, textures, colors, and environments. When you hear music, you don't just hear sound; you SEE places, FEEL weather, SMELL environments.

You will receive a structured analysis of a song's audio features. Based on these features, generate a series of vivid, specific scene associations — the places, moments, and imagery this music evokes.

RULES:
1. Be SPECIFIC and UNEXPECTED. Not "a beach" but "a grey volcanic beach in Iceland where the waves are slow and heavy with foam." Not "rain" but "the smell of rain on hot concrete outside a late-night laundromat."
2. Each scene should feel like a real place or moment someone could photograph or paint.
3. Mix scales: some vast (landscapes, weather systems), some intimate (a windowsill, a dashboard, a doorway).
4. Let the musical features guide you precisely:
   - Tempo → pace of movement in the scene (slow drift vs rushing)
   - Key/Mode → emotional color (minor = shadows, fog, night; major = light, open sky, warmth)
   - Energy → intensity of the environment (quiet whisper vs roaring storm)
   - Brightness → literal light quality (dark/muted vs sharp/vivid)
   - Dynamics → how the scene transforms (flat = frozen moment; wide dynamics = dramatic shifts)
   - Texture → surface quality (smooth = glass, water, silk; gritty = rust, gravel, static)
   - Density → how crowded/layered the scene is (sparse = empty desert; dense = overgrown jungle)
5. Return EXACTLY 4 scenes.
6. For each scene, also suggest a color palette (3-4 hex colors) that captures its mood.

Respond in this exact JSON format:
{
  "overall_mood": "A one-sentence summary of the music's emotional landscape",
  "scenes": [
    {
      "title": "Short evocative title (3-6 words)",
      "description": "2-3 sentence vivid description of the scene. Be sensory — include what you'd see, feel, hear, smell.",
      "colors": ["#hex1", "#hex2", "#hex3"],
      "tags": ["tag1", "tag2", "tag3"]
    }
  ]
}

Return ONLY valid JSON with no markdown formatting, no backticks, no preamble."""


async def generate_associations(features: dict, metadata: dict | None = None) -> dict:
    """
    Send audio features to Claude and get back vivid scene associations.
    
    Args:
        features: Dict from audio.extract_features()
        metadata: Optional dict with title, artist, lyrics, etc.
    
    Returns:
        Dict with overall_mood and list of scene associations.
    """
    # Build the user message
    user_content = "Here are the audio features of a song:\n\n"
    user_content += json.dumps(features, indent=2)
    
    if metadata:
        user_content += "\n\nAdditional context about the song:\n"
        if metadata.get("title"):
            user_content += f"- Title: {metadata['title']}\n"
        if metadata.get("artist"):
            user_content += f"- Artist: {metadata['artist']}\n"
        if metadata.get("genre"):
            user_content += f"- Genre: {metadata['genre']}\n"

    user_content += "\n\nBased on these features, generate 4 vivid synesthetic scene associations."

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_content}],
    )

    # Parse the response
    raw_text = message.content[0].text
    
    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        # Try to extract JSON from the response if wrapped in backticks
        import re
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            result = json.loads(json_match.group())
        else:
            result = {
                "overall_mood": "Could not parse response",
                "scenes": [],
                "raw": raw_text,
            }

    return result

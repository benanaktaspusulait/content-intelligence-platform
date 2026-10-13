"""Start-frame image generation service.

Generates a first-frame candidate image from the saved production prompt's
opening beat. Uses DALL-E 3 via the OpenAI provider.

The generated image is stored as a start-frame candidate linked to:
- contentId
- promptVersionId
- character/reference bindings
- generator/settings provenance
"""

import hashlib
import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from ..llm.openai_provider import OpenAIProvider


def _extract_first_beat(prompt_text: str) -> str:
    """Extract the first beat/opening from a production prompt.
    
    Handles common formats:
    - "0-2s: ..." or "0-2s: ... -> ..."
    - "1. ..." or "1) ..."
    - "TIMED SHOT PLAN" section
    - "OPENING" section
    - Plain text (returns first sentence)
    """
    text = prompt_text.strip()
    
    # Try "0-2s:" format
    for line in text.split('\n'):
        line = line.strip()
        if line and (line.startswith('0-') or line.startswith('0 ')):
            # Remove timing prefix
            beat = line.split(':', 1)[-1].strip() if ':' in line else line
            # Remove consequence for image generation (we want the scene, not the result)
            if ' -> ' in beat:
                beat = beat.split(' -> ', 1)[0].strip()
            return beat
    
    # Try numbered format "1." or "1)"
    for line in text.split('\n'):
        line = line.strip()
        if line and (line.startswith('1.') or line.startswith('1)')):
            beat = line.split('.', 1)[-1].strip() if line.startswith('1.') else line.split(')', 1)[-1].strip()
            if ' -> ' in beat:
                beat = beat.split(' -> ', 1)[0].strip()
            return beat
    
    # Try TIMED SHOT PLAN section
    if 'TIMED SHOT PLAN' in text.upper():
        section = text.split('TIMED SHOT PLAN', 1)[1]
        for line in section.split('\n'):
            line = line.strip()
            if line and not line.startswith('#') and len(line) > 10:
                if ' -> ' in line:
                    line = line.split(' -> ', 1)[0].strip()
                return line
    
    # Try OPENING section
    if 'OPENING' in text.upper():
        section = text.split('OPENING', 1)[1].split('\n')[0].strip()
        return section
    
    # Fallback: return first sentence
    for delimiter in ['.', '\n']:
        parts = text.split(delimiter, 1)
        if len(parts[0].strip()) > 20:
            return parts[0].strip()
    
    return text[:200]


def _build_image_prompt(
    first_beat: str,
    character_name: str,
    character_description: str,
    aspect_ratio: str,
    content_profile: str,
) -> str:
    """Build a DALL-E image generation prompt from the first beat.
    
    The prompt emphasizes:
    - Character identity consistency
    - The impossible physical relationship
    - Clear readable composition
    - Aspect ratio appropriate framing
    """
    # Base prompt
    prompt_parts = [
        f"First frame of a short animation video.",
        f"Character: {character_name}.",
    ]
    
    if character_description:
        prompt_parts.append(f"Character design: {character_description}.")
    
    prompt_parts.append(f"Scene: {first_beat}.")
    
    # Composition requirements
    prompt_parts.append(
        "Clear readable composition with the character and central object clearly visible."
    )
    prompt_parts.append(
        "The impossible physical relationship must be immediately understandable."
    )
    
    # Aspect ratio framing
    if aspect_ratio in ("9:16", "3:4"):
        prompt_parts.append("Vertical composition, portrait orientation.")
    else:
        prompt_parts.append("Horizontal composition, landscape orientation.")
    
    # Style
    prompt_parts.append(
        "3D animated style, clean lighting, no text overlays, no additional characters."
    )
    
    return " ".join(prompt_parts)


def generate_start_frame(
    prompt_text: str,
    content_id: int,
    prompt_version_id: int,
    character_name: str = "",
    character_description: str = "",
    aspect_ratio: str = "9:16",
    content_profile: str = "AUTO",
    generator: str = "SEEDANCE_2_0_MINI",
    max_cost_usd: float = 0.10,
) -> dict[str, Any]:
    """Generate a start-frame candidate image.
    
    Args:
        prompt_text: The exact saved production prompt text
        content_id: Content workspace ID
        prompt_version_id: Prompt version ID
        character_name: Main character name
        character_description: Character appearance description
        aspect_ratio: Target aspect ratio (e.g., "9:16")
        content_profile: Content profile (e.g., "ABSURD_PHYSICS")
        generator: Target video generator
        max_cost_usd: Maximum allowed cost for this generation
    
    Returns:
        Dict with generation result including image_path, sha256, metadata
    """
    # Check cost ceiling
    dall_e_cost = 0.04  # DALL-E 3 standard quality ~$0.04 per image
    if max_cost_usd <= 0 or dall_e_cost > max_cost_usd:
        return {
            "status": "REJECTED_COST_CEILING",
            "reason": f"DALL-E 3 image generation cost (${dall_e_cost:.2f}) exceeds "
                      f"authorized ceiling (${max_cost_usd:.2f}).",
            "estimatedCost": dall_e_cost,
            "maxCostUsd": max_cost_usd,
        }
    
    # Extract first beat
    first_beat = _extract_first_beat(prompt_text)
    
    # Build image prompt
    image_prompt = _build_image_prompt(
        first_beat, character_name, character_description,
        aspect_ratio, content_profile
    )
    
    # Generate image
    try:
        provider = OpenAIProvider()
    except ValueError as e:
        return {
            "status": "PROVIDER_UNAVAILABLE",
            "reason": str(e),
            "provider": "openai",
        }
    
    # Resolve output directory
    output_dir = os.getenv("IMAGE_OUTPUT_DIR", "/tmp/pompom-images")
    content_dir = os.path.join(output_dir, str(content_id), str(prompt_version_id))
    os.makedirs(content_dir, exist_ok=True)
    
    result = provider.generate_image(
        prompt=image_prompt,
        aspect_ratio=aspect_ratio,
        model="dall-e-3",
        quality="standard",
        style="natural",
        output_dir=content_dir,
    )
    
    # Build candidate record
    candidate_id = f"start-frame-{uuid.uuid4().hex[:12]}"
    
    return {
        "status": "GENERATED",
        "candidateId": candidate_id,
        "contentId": content_id,
        "promptVersionId": prompt_version_id,
        "imagePath": result["image_path"],
        "imageUrl": result["image_url"],
        "sha256": result["sha256"],
        "width": result["width"],
        "height": result["height"],
        "firstBeat": first_beat,
        "imagePrompt": image_prompt,
        "characterName": character_name,
        "aspectRatio": aspect_ratio,
        "generator": generator,
        "model": result["model"],
        "requestId": result["requestId"],
        "cost": dall_e_cost,
        "maxCostUsd": max_cost_usd,
        "status_label": "CANDIDATE",
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "source": "GENERATED",
            "provider": "openai",
            "model": "dall-e-3",
            "promptVersionId": prompt_version_id,
            "contentId": content_id,
        },
    }

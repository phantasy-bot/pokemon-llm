"""
Name Generator for Pokemon LLM Agent

Generates unique, funny names for rivals and Pokemon via LLM calls.
Used at run start (rival) and Oak's Lab (starter choice + nickname).
Falls back to predefined lists on LLM failure.
"""

import logging
import random
import re
from typing import Optional, Tuple
from dataclasses import dataclass

log = logging.getLogger("name_generator")

# Fallback rival name suggestions (from name_planner.py)
RIVAL_NAME_SUGGESTIONS = [
    "CUTIE",
    "MEANY",
    "BULLY",
    "DUMMY",
    "CRUSH",
    "RIVAL",
    "LOSER",
    "JERK",
    "STINKY",
    "BUTT",
    "DORK",
    "NERD",
    "DOOFUS",
    "IDIOT",
]

# Fallback Pokemon nicknames (cute/silly)
POKEMON_NICKNAME_SUGGESTIONS = [
    "SPARKY",
    "BUBBLES",
    "FLAME",
    "LEAFY",
    "CHOMPY",
    "SQUISH",
    "SNAPPY",
    "ZAPPY",
    "BURNY",
    "SPLASHY",
    "VINNY",
    "BITEY",
    "CUDDLES",
    "WOBBLES",
    "PEBBLES",
    "SNUGGLES",
]

# Valid starter Pokemon
VALID_STARTERS = ["CHARMANDER", "SQUIRTLE", "BULBASAUR"]


@dataclass
class StarterChoice:
    """Represents the AI's starter Pokemon choice."""

    species: str  # CHARMANDER, SQUIRTLE, or BULBASAUR
    nickname: str  # Cute nickname for the Pokemon


def sanitize_name(name: str, max_length: int = 7) -> str:
    """
    Sanitize a name for Pokemon Red's keyboard input.
    - Uppercase only
    - Remove invalid characters (keep A-Z and space only)
    - Trim to max length
    """
    if not name:
        return ""

    # Uppercase and strip
    name = name.upper().strip()

    # Remove invalid characters (Pokemon Red keyboard only has A-Z, space, and some symbols)
    # For simplicity, keep only alphanumeric
    name = re.sub(r"[^A-Z]", "", name)

    # Trim to max length
    return name[:max_length]


def generate_rival_name_sync(client, model: str, temperature: float = 0.9) -> str:
    """
    Generate a funny rival name using the LLM.

    Args:
        client: OpenAI-compatible client
        model: Model name to use
        temperature: Higher = more creative

    Returns:
        Sanitized rival name (4-7 chars, uppercase)
    """
    prompt = """You are Lass, a playful AI streamer playing Pokemon Red.
Pick a funny, silly, or teasing name for your rival (4-7 letters only).
The name should be something a mischievous girl would call an annoying boy.

Examples of good names: STINKY, DWEEB, DOOFUS, MEANIE, DORK, BOOGER, WEIRDO

Respond with ONLY the name in capital letters, nothing else. No quotes, no explanation."""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=20,
        )

        raw_name = response.choices[0].message.content.strip()
        sanitized = sanitize_name(raw_name, max_length=7)

        # Validate: must be 4-7 chars
        if 4 <= len(sanitized) <= 7:
            log.info(f"LLM generated rival name: '{sanitized}'")
            return sanitized
        else:
            log.warning(
                f"LLM rival name '{raw_name}' -> '{sanitized}' invalid length, using fallback"
            )
            return random.choice(RIVAL_NAME_SUGGESTIONS)

    except Exception as e:
        log.error(f"Failed to generate rival name via LLM: {e}")
        fallback = random.choice(RIVAL_NAME_SUGGESTIONS)
        log.info(f"Using fallback rival name: '{fallback}'")
        return fallback


def generate_starter_choice_sync(
    client, model: str, temperature: float = 0.9
) -> StarterChoice:
    """
    Generate starter Pokemon choice and nickname using the LLM.

    Args:
        client: OpenAI-compatible client
        model: Model name to use
        temperature: Higher = more creative

    Returns:
        StarterChoice with species and nickname
    """
    prompt = """You are Lass, a playful AI streamer playing Pokemon Red.
Professor Oak is letting you choose your first Pokemon!

Available starters:
- CHARMANDER (Fire type) - Cute lizard, evolves to Charizard
- SQUIRTLE (Water type) - Adorable turtle, evolves to Blastoise
- BULBASAUR (Grass/Poison type) - Sweet bulb dinosaur, evolves to Venusaur

1. Pick which Pokemon you want based on your personality!
2. Give it a cute or silly nickname (1-10 characters)

Respond in this EXACT format (no other text):
POKEMON: [name]
NICKNAME: [nickname]

Example response:
POKEMON: SQUIRTLE
NICKNAME: BUBBLES"""

    try:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=50,
        )

        raw_response = response.choices[0].message.content.strip()
        log.debug(f"LLM starter response: {raw_response}")

        # Parse response
        species = None
        nickname = None

        for line in raw_response.split("\n"):
            line = line.strip().upper()
            if line.startswith("POKEMON:"):
                species_raw = line.replace("POKEMON:", "").strip()
                # Match to valid starters
                for valid in VALID_STARTERS:
                    if valid in species_raw:
                        species = valid
                        break
            elif line.startswith("NICKNAME:"):
                nickname_raw = line.replace("NICKNAME:", "").strip()
                nickname = sanitize_name(nickname_raw, max_length=10)

        # Validate
        if species and nickname and len(nickname) >= 1:
            log.info(f"LLM chose starter: {species} nicknamed '{nickname}'")
            return StarterChoice(species=species, nickname=nickname)
        else:
            log.warning(
                f"Failed to parse LLM starter response: species={species}, nickname={nickname}"
            )
            raise ValueError("Invalid LLM response format")

    except Exception as e:
        log.error(f"Failed to generate starter choice via LLM: {e}")
        # Fallback: random starter with random cute nickname
        fallback_species = random.choice(VALID_STARTERS)
        fallback_nickname = random.choice(POKEMON_NICKNAME_SUGGESTIONS)
        log.info(
            f"Using fallback starter: {fallback_species} nicknamed '{fallback_nickname}'"
        )
        return StarterChoice(species=fallback_species, nickname=fallback_nickname)


async def generate_rival_name(client, model: str, temperature: float = 0.9) -> str:
    """
    Async wrapper for rival name generation.
    Runs the sync function in the default executor.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, generate_rival_name_sync, client, model, temperature
    )


async def generate_starter_choice(
    client, model: str, temperature: float = 0.9
) -> StarterChoice:
    """
    Async wrapper for starter choice generation.
    Runs the sync function in the default executor.
    """
    import asyncio

    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, generate_starter_choice_sync, client, model, temperature
    )

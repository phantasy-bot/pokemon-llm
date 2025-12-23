"""
Prompts for generating tweets and social media content.
Loads templates from data/tweet_templates.yaml for a Docs-as-Code approach.
"""

import logging
from pathlib import Path
from typing import Optional, Dict, Any

log = logging.getLogger("prompts.tweets")

# Default templates if YAML is missing
TWEET_PROMPT_FRESH_START = """You are Lass, a bubbly female AI playing Pokemon Red on stream.
You're about to start a brand new adventure and want to tweet about it!

Generate a short, enthusiastic tweet announcing your new Pokemon Red run.

Requirements:
- Max 260 characters (leave room for hashtags)
- First person, excited and genuine
- Include 1-2 hashtags from: #Pokemon #PokemonRed #LLMLetsPlay #AIStreamer
- Express excitement about the new journey ahead
- Be specific about Pokemon Red (mention Kanto, becoming champion, catching Pokemon, etc.)
- Do NOT use emojis

Return ONLY the tweet text, nothing else."""

TWEET_PROMPT_CONTINUING = """You are Lass, a bubbly female AI playing Pokemon Red on stream.
You're resuming your adventure and want to tweet about it!

Current Game State:
- Location: {location}
- Team: {team}
- Badges: {badges}
- Playtime: {playtime}
- Current Goal: {primary_goal}
- Recent Progress: {latest_memory}

Generate a short tweet about resuming your Pokemon adventure.

Requirements:
- Max 260 characters (leave room for hashtags)
- First person, enthusiastic
- Include 1-2 hashtags from: #Pokemon #PokemonRed #LLMLetsPlay #AIStreamer
- Reference where you are and what you're doing
- Be specific! Mention your team, location, or current goal
- Do NOT use emojis

Return ONLY the tweet text, nothing else."""

# Gym leader names for badge tweets
BADGE_GYM_LEADERS = {
    "Boulder": "Brock",
    "Cascade": "Misty",
    "Thunder": "Lt. Surge",
    "Rainbow": "Erika",
    "Soul": "Koga",
    "Marsh": "Sabrina",
    "Volcano": "Blaine",
    "Earth": "Giovanni",
}

_templates_cache: Optional[Dict[str, str]] = None


def _load_tweet_templates() -> Dict[str, str]:
    """Load tweet templates from YAML with caching."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache

    data_path = Path(__file__).parent.parent.parent / "data" / "tweet_templates.yaml"
    if not data_path.exists():
        log.warning(f"Tweet templates YAML not found: {data_path}")
        return {}

    try:
        import yaml

        with open(data_path, "r") as f:
            _templates_cache = yaml.safe_load(f)
        return _templates_cache or {}
    except Exception as e:
        log.error(f"Failed to load tweet templates YAML: {e}")
        return {}


def build_tweet_prompt(
    is_continuing_run: bool,
    run_state=None,
    game_state: Optional[Dict[Any, Any]] = None,
) -> str:
    """
    Build a prompt for generating tweet text.

    Args:
        is_continuing_run: Whether this is continuing an existing run.
        run_state: RunState object with run context.
        game_state: Current game state dictionary.

    Returns:
        The formatted prompt string.
    """
    if not is_continuing_run:
        return TWEET_PROMPT_FRESH_START

    # Build context for continuing run
    location = "Kanto"
    team = "My Pokemon team"
    badges = "0"
    playtime = "a while"
    primary_goal = "exploring"
    latest_memory = "Making progress on my adventure"

    if game_state:
        map_name = game_state.get("map_name", "")
        if map_name:
            location = map_name.replace("_", " ").title()

        badge_list = game_state.get("badges")
        if isinstance(badge_list, list):
            badges = str(len(badge_list))

        party = game_state.get("party")
        if party and isinstance(party, list):
            team_strs = []
            for p in party[:3]:
                if isinstance(p, dict):
                    name = p.get("nickname") or p.get("species", "???")
                    level = p.get("level", "?")
                    team_strs.append(f"{name} (Lv{level})")
            if team_strs:
                team = ", ".join(team_strs)

    if run_state:
        elapsed = getattr(run_state, "elapsed_seconds", 0)
        if elapsed:
            hours = elapsed / 3600
            playtime = f"{hours:.1f} hours"

        goals = getattr(run_state, "goals", {})
        if goals and goals.get("primary"):
            primary_goal = goals["primary"]

        memory = getattr(run_state, "latest_memory", "")
        if memory:
            latest_memory = memory[:100]

    return TWEET_PROMPT_CONTINUING.format(
        location=location,
        team=team,
        badges=badges,
        playtime=playtime,
        primary_goal=primary_goal,
        latest_memory=latest_memory,
    )


def build_achievement_tweet_prompt(
    achievement,
    run_state=None,
    game_state: Optional[Dict[Any, Any]] = None,
) -> str:
    """
    Build a prompt for generating achievement-specific tweet text.

    Args:
        achievement: Achievement object with type and context.
        run_state: RunState object with run context.
        game_state: Current game state dictionary.

    Returns:
        The formatted prompt string.
    """
    from trackers.achievement_tracker import AchievementType

    achievement_type = achievement.achievement_type
    context = achievement.context or {}
    templates = _load_tweet_templates()

    # Map achievement types to template keys
    type_to_template = {
        AchievementType.STREAM_START: "stream_start",
        AchievementType.FIRST_POKEMON: "first_pokemon",
        AchievementType.ROUTE_1_FLOWER: "route_1_flower",
        AchievementType.FIRST_CATCH: "first_catch",
        AchievementType.VIRIDIAN_FOREST_BREAK: "viridian_forest_break",
        AchievementType.STARTER_EVOLUTION_1: "starter_evolution_1",
        AchievementType.STARTER_EVOLUTION_2: "starter_evolution_2",
        AchievementType.BADGE_BOULDER: "badge",
        AchievementType.BADGE_CASCADE: "badge",
        AchievementType.BADGE_THUNDER: "badge",
        AchievementType.BADGE_RAINBOW: "badge",
        AchievementType.BADGE_SOUL: "badge",
        AchievementType.BADGE_MARSH: "badge",
        AchievementType.BADGE_VOLCANO: "badge",
        AchievementType.BADGE_EARTH: "badge",
        AchievementType.LEGENDARY_ARTICUNO: "legendary",
        AchievementType.LEGENDARY_ZAPDOS: "legendary",
        AchievementType.LEGENDARY_MOLTRES: "legendary",
        AchievementType.LEGENDARY_MEWTWO: "legendary",
        AchievementType.POKEMON_CHAMPION: "pokemon_champion",
        AchievementType.SS_ANNE_DECK: "ss_anne_deck",
        AchievementType.POKEMON_TOWER_SPOOKED: "pokemon_tower_spooked",
        AchievementType.GAME_CORNER_SLOTS: "game_corner_slots",
        AchievementType.FIGHTING_DOJO: "fighting_dojo",
        AchievementType.SAFARI_ZONE_EXPLORER: "safari_zone_explorer",
        AchievementType.TEAM_ROCKET_FIRST: "team_rocket_first",
        AchievementType.CERULEAN_CAPE: "cerulean_cape",
        AchievementType.MT_MOON_EXIT: "mt_moon_exit",
        AchievementType.ROCK_TUNNEL_EXIT: "rock_tunnel_exit",
        AchievementType.CYCLING_ROAD: "cycling_road",
        AchievementType.SEAFOAM_ISLANDS: "seafoam_islands",
        AchievementType.ROUTE_12_FISHING: "route_12_fishing",
        AchievementType.PEWTER_GYM_ENTRANCE: "pewter_gym_entrance",
        AchievementType.INDIGO_PLATEAU: "indigo_plateau",
        AchievementType.DAYCARE_VISIT: "daycare_visit",
    }

    template_key = type_to_template.get(achievement_type, "stream_start")
    template = templates.get(template_key)

    if not template:
        log.warning(f"No template found for {template_key}, using default stream_start")
        template = templates.get("stream_start", TWEET_PROMPT_FRESH_START)

    # Build format kwargs based on achievement type
    format_kwargs = {}

    if template_key == "first_pokemon":
        format_kwargs["pokemon"] = context.get("pokemon", "a new Pokemon")
        format_kwargs["nickname"] = context.get("nickname", "my new friend")
    elif template_key == "first_catch":
        format_kwargs["pokemon"] = context.get("pokemon", "a wild Pokemon")
    elif template_key == "starter_evolution_1":
        format_kwargs["evolved_from"] = context.get("evolved_from", "my starter")
        format_kwargs["pokemon"] = context.get("pokemon", "its evolved form")
    elif template_key == "starter_evolution_2":
        format_kwargs["starter"] = context.get("starter", "my starter")
        format_kwargs["pokemon"] = context.get("pokemon", "its final form")
    elif template_key == "badge":
        badge_name = context.get("badge_name", "a new")
        total_badges = context.get("total_badges", 1)
        gym_leader = BADGE_GYM_LEADERS.get(badge_name, "the gym leader")
        format_kwargs["badge_name"] = badge_name
        format_kwargs["total_badges"] = total_badges
        format_kwargs["gym_leader"] = gym_leader
    elif template_key == "legendary":
        format_kwargs["pokemon"] = context.get("pokemon", "a legendary Pokemon")

    try:
        return template.format(**format_kwargs)
    except Exception:
        return template

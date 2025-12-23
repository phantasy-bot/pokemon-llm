#!/usr/bin/env python3
"""
Generate GAME_DATA.md documentation from data/game_data.yaml.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


def generate_markdown(data: dict) -> str:
    """Generate markdown documentation from YAML data."""
    lines = []
    lines.append("# Pokemon Game Data Reference")
    lines.append("")
    lines.append("> **Auto-generated** from `data/game_data.yaml`")
    lines.append("")

    # Locations
    lines.append("## Locations")
    lines.append("")
    locs = data.get("locations", {})
    for category, items in locs.items():
        lines.append(f"### {category.title()}")
        for item in sorted(items):
            lines.append(f"- {item}")
        lines.append("")

    # Items
    lines.append("## Items")
    lines.append("")
    items = data.get("items", {})
    for category, item_list in items.items():
        lines.append(f"### {category.replace('_', ' ').title()}")
        for item in sorted(item_list):
            lines.append(f"- {item}")
        lines.append("")

    # Pokemon
    lines.append("## Pokemon")
    lines.append("")
    poke = data.get("pokemon", {})

    lines.append("### Legendaries")
    for p in sorted(poke.get("legendaries", [])):
        lines.append(f"- {p}")
    lines.append("")

    # Photo Moments
    lines.append("## Photo Moments")
    lines.append("")
    lines.append("| ID | Map ID(s) | Trigger Condition |")
    lines.append("|----|-----------|-------------------|")
    photos = data.get("photo_moments", {})
    for photo_id, info in sorted(photos.items()):
        map_ids = info.get("map_id") or info.get("map_ids")
        if isinstance(map_ids, list):
            map_str = ", ".join([hex(m) for m in map_ids])
        else:
            map_str = hex(map_ids) if map_ids else "Any"

        condition = "Entry"
        if "position" in info:
            condition = f"Near {info['position']} (range {info.get('range', 1)})"
        elif "min_x" in info:
            condition = f"X >= {info['min_x']}"
        elif "min_y" in info:
            condition = f"Y >= {info['min_y']}"

        lines.append(f"| {photo_id} | {map_str} | {condition} |")
    lines.append("")

    return "\n".join(lines)


def main():
    yaml_path = PROJECT_ROOT / "data" / "game_data.yaml"
    output_path = PROJECT_ROOT / "docs" / "reference" / "GAME_DATA.md"

    if not yaml_path.exists():
        print(f"ERROR: YAML file not found: {yaml_path}")
        sys.exit(1)

    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f)

    markdown = generate_markdown(data)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(markdown)

    print(f"Generated: {output_path}")


if __name__ == "__main__":
    main()

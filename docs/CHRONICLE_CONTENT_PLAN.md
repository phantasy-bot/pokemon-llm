# Chronicle Content & Gating Plan

This document outlines every type of content the agent generates on Zora, its frequency, and the opportunities for token-gated exclusive rewards.

## 🏆 Achievement Tiers

### 1. Major Achievements (High Value)
**Platform:** Twitter + Zora (Mintable)
**Gating Potential:** ⭐⭐⭐⭐⭐ (High)
**Content:** AI-Generated Image + Exclusive File (Save file, High-res Art, Battle Log)

| Achievement | Description | Est. Frequency | Gated Content Idea |
|-------------|-------------|----------------|--------------------|
| **Stream Start** | Beginning a new run | Once per run | Initial Save File (`.sav`) |
| **Gym Badges** | Defeating Gym Leaders (Boulder, Cascade, etc.) | 8 per run | Full Battle Log / Gym Selfie |
| **Elite 4 / Champion** | Beating the game | Once per run | Final Save File / Hall of Fame Art |
| **Legendary Catch** | Catching Articuno, Zapdos, Moltres, Mewtwo | 4 max per run | High-res "Legendary Encounter" Art |
| **Starter Evolution** | Starter reaching Stage 2 or 3 | 2 per run | "Growing Up" Photo Album |

### 2. Minor Achievements (Volume / Documentation)
**Platform:** Zora Only
**Gating Potential:** ⭐⭐ (Low - mostly for collecting)
**Content:** Game Screenshot

| Achievement | Description | Est. Frequency | Gated Content Idea |
|-------------|-------------|----------------|--------------------|
| **New Location** | Entering a new Route, City, or Dungeon | ~30-40 unique maps | None / Location Metadata |
| **First Catch (Species)** | First time catching a specific Pokemon | ~151 max | Pokedex Entry Raw Data |
| **Evolution** | Any non-starter Pokemon evolving | Varies | Evolution Animation GIF |
| **Rival/Rocket Defeated** | Winning key storyline battles | ~10-15 battles | Battle Stats |
| **Key Item / HM** | Finding important items (Bike, Surf, etc.) | ~15 items | Item Description / Lore |
| **Pokedex Milestone** | Every 10 Pokemon caught | ~15 times | Full Pokedex Export |

### 3. Progress Updates (Consistency)
**Platform:** Zora Only
**Gating Potential:** ⭐ (Low)
**Content:** Screenshot Collage (Gallery of last 6 moments)

| Trigger | Description | Frequency |
|---------|-------------|-----------|
| **Cycle Checkpoint** | Posted if no achievements occur for 60 cycles (~1 hour) | Periodic |

## 🔒 Gated Content Strategy

The **Chronicle Server** allows attaching an *Exclusive File* to any drop.

### Proposed Gating Model

1.  **"The Trainer's Save"**:
    *   **Trigger**: Gym Badge Wins & Champion Victory.
    *   **Locked Content**: The actual `.sav` file (or a state file) from that exact moment.
    *   **Value**: Holders can load the save and play *as* the agent from that victory point.

2.  **"High-Res Memories"**:
    *   **Trigger**: Legendary Catches & Starter Evolutions.
    *   **Locked Content**: 4K Upscaled AI Art (Public post gets 1024px, Holders get 4K).

3.  **"Battle Recorder"**:
    *   **Trigger**: Rival/Rocket Battles.
    *   **Locked Content**: Full JSON log of every turn, move, and damage calculation in the battle.

## 📊 Volume Estimates

For a typical run (20-40 hours):

*   **Major Drops**: ~15-20 total. (High value, scarce).
*   **Minor Drops**: ~100-200 total. (High volume, low cost, builds timeline).
*   **Progress Drops**: ~20-40 total. (Fills gaps).

**Total Zora Coins**: ~150-250 per playthrough.
**Cost Estimate (Base L2)**: ~$5-10 USD total gas for the whole run.

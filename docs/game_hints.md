# Pokemon Red Area Hints & Walkthrough

This document provides sequential navigation hints for the AI agent to complete Pokemon Red.

## ⚠️ GENERAL NAVIGATION RULES

- **Vision Uncertainty**: Your vision is uncertain. If you are struggling to make something work, you may want to reconsider your visual assumptions.
- **Trust Game State**: Always trust `map_name`, `coordinates`, and `dialog_text` over visual analysis.
- **Stuck?**: If you can't find a path, check for "invisible" NPCs or narrow passages.

---

## 📍 PALLET TOWN & ROUTE 1

### Player's House (Bedroom) - PLAYERS_HOUSE_2F

- **STAIRCASE LOCATION**: The exit stairs are at coordinates **(7,1)** in the **TOP-RIGHT (NORTHEAST) corner** of the room.
- **COMMON MISTAKE**: The **WEST/SOUTHWEST edge** of the room is the player's **BED**, NOT an exit. Do NOT try to find a door or stairs there.
- **To exit**: Walk to the TOP-RIGHT corner toward (7,1). The staircase leads down to PLAYERS_HOUSE_1F.
- The room is small - the exit is the ONLY tile transition in the top-right.

### Pallet Town (Initial)

- Go **North** into the tall grass at the edge of town to trigger Professor Oak.
- **Do not** go to the Lab first; you must be stopped by Oak in the grass.
- In the Lab: Talk to Oak (at top of room), select a ball (table), and try to leave to trigger Rival battle.

### Route 1 (Toward Viridian)

- Go **North**. The path is straightforward. Enter patches of grass if needed.
- Destination: Viridian City (North).

---

## 📍 VIRIDIAN CITY (The Parcel Quest)

### Identifying Buildings

- **Pokemon Center**: Lower building, sign says "POKE".
- **Pokemart**: Northeast of the Pokemon Center. Sign says "MART".
- **Distinction**: Do not confuse them! Read the text or check relative positions.

### The Parcel Mission

- **Goal**: You cannot get a Pokedex yet! You must get **Oak's Parcel** first.
- **Action**: Go to the **Pokemart**.
- **Inside Mart**: The shopkeeper is at **(0,5)** (top left). You cannot stand on (1,5). Stand at **(2,5)** facing **LEFT** and press A to talk.
- **Result**: You will receive Oak's Parcel.
- **Next**: Return **South** to Pallet Town immediately.

### Pokemon Center (Healing)

- Nurse is at **(3,1)** behind the counter.
- Stand at **(3,3)** facing **UP** and press A to heal.

---

## 📍 BACK TO PALLET (Delivering Parcel)

### Oak's Lab

- Talk to Professor Oak (at the back).
- **Result**: He will take the Parcel and give you the **Pokedex**.
- **Daisy (Rival's House)**: After getting Pokedex, visit Rival's house (right of yours). Talk to his sister (Daisy) to get the **Town Map**.

---

## 📍 PEWTER CITY & MT MOON

### Viridian Forest

- Pass through Viridian Forest (North of Route 2).
- It is a maze, but generally head **North-West** then **North-East**.
- **Exit**: Takes you to Pewter City.

### Pewter City

- **Gym**: Located in the **North-West** area. Defeat Brock to proceed.
- **Route 3**: East exit is blocked until you beat Brock.

### Mt Moon

- **Navigation**: Entering looking for "Fossils" means you are near the end.
- **Fossil Choice**: When you find a fossil (Dome/Helix), pick one.
- **CRITICAL EXIT HINT**: After picking a fossil, the exit is **UP/Past** where the fossil was.
  - **Do NOT turn back**. Do not go back down the stairs you came from.
  - Explore the area **beyond** the fossil to find the exit ladder.
- **Vision Warning**: You often misidentify rocks as trainers or fossils. Verify with collision/dialog.

---

## 📍 ROUTE 4 & CERULEAN

### Route 4 (The Ledges)

- This area has many **One-Way Ledges** (lines on ground).
- You can HOP DOWN them, but NEVER up.
- **Tool Use**: Use `use_emulator` to hop ledges if standard movement fails.
- **Warning**: Once you hop down the final ledges to Cerulean, you cannot return to Mt Moon easily.

### Cerulean City

- **Goal**: Get the S.S. Anne Ticket from Bill.
- **Nugget Bridge**: Go **North**. Beat 5 trainers.
- **Route 24/25**: Go East to Bill's Sea Cottage. Talk to Bill (looks like a Pokemon). Help him (use PC). Talk again to get **S.S. Ticket**.
- **Misty**: Defeat Misty at the Gym (Center of city).

### Path to Vermillion (Route 5)

- **Blocked House**: The exit South is blocked by a guard.
- **Solution**: Go to the **Northeast corner** of Cerulean City.
- **Trashed House**: Enter the house with the hole in the wall. Go through the hole to the backyard.
- **Route 5**: This path leads South to Route 5, bypassing the guard.

---

## 📍 VERMILLION CITY (SS Anne)

### Route 5 / Underground Path

- Take the **Underground Path** (small building) to skip Saffron City (guards will stop you).
- Emerging on Route 6, go South to Vermillion.

### Vermillion City

- **S.Ś. Anne**: Go South-East to the harbor. Show Ticket.
- **Goal**: Find the Captain in the Captain's Quarters (far left of top deck).
- **Action**: Rub his back (talk to him). Get **HM01 (Cut)**.
- **Leaving**: Leave the ship. It will depart.

### Lt. Surge (Gym)

- **Requirement**: You need a Pokemon with **Cut** to remove the bush blocking the Gym.
- **Puzzle**: Trash cans. You need luck or persistent trial and error to find the switches.
- **Badge**: Thunder Badge allows finding Fly (later).

---

## 📍 ROCK TUNNEL & LAVENDER TOWN

### Route 9 / 10

- From Cerulean, go **East** (need Cut).
- Navigate Route 9 ledges carefully to reach Rock Tunnel Pokemon Center.

### Rock Tunnel

- **Darkness**: Only navigate if you have **Flash** (HM05) or are willing to try blind (wall follow).
- **Flash Source**: Get HM05 from Aide on Route 2 (needs 10 Pokemon caught) OR navigate blindly.
- **Map**: Generally head **South-East** through the floors.

### Lavender Town

- **Pokemon Tower**: You cannot fight ghosts yet (need Silph Scope).
- Proceed **West** to Route 8 -> Underground Path -> Celadon City.

---

## 📍 CELADON CITY (The Big City)

### Department Store

- **Roof**: Buy Fresh Water / Soda Pop / Lemonade from vending machines.
- **Give to Guard**: Give a drink to the guards at Saffron City gates to open them.

### Rocket Hideout (Game Corner)

- **Location**: Building with "GAME" or "CASINO" sign (South-Central).
- **Poster**: Approach the poster at the back wall (Right side). Press A to reveal switch.
- **Stairs**: Enter hideout.
- **Goal**: Find **Lift Key** (dropped by Rocket), use Elevator to B4F, beat Giovanni.
- **Reward**: **Silph Scope**.

### Erika (Gym)

- Need Cut to enter. Grass type gym.

---

## 📍 SAFFRON CITY (Silph Co)

### Access

- Must give **Drink** (from Celadon Roof) to any guard at the gates.

### Silph Co (Center Skyscraper)

- **Goal**: Rescue President on 11F.
- **Key Item**: Find **Card Key** (5F South). Opens doors.
- **Teleporters**: If stuck, try diamond-pattern floor tiles.
- **Rival**: Battle on 7F (or nearby).
- **Giovanni**: Battle on 11F.
- **Reward**: **Master Ball**.

### Sabrina (Gym)

- Teleporter maze. General rule: Keep taking the teleporter directly above/below/opposite you, or strictly stick to one direction.

---

## 📍 FUCHSIA CITY (Safari & Koga)

### Getting There

- **Cycling Road (Route 17)**: West of Celadon (Need Bike + Snorlax awake?).
- **Silence Bridge (Route 12)**: South of Lavender (Need Poke Flute).
- **Poke Flute**: Get from Mr. Fuji in Lavender Tower (requires Silph Scope).

### Safari Zone (North Fuchsia)

- **Goal 1**: Get **Gold Teeth** (Deep in Area 3).
- **Goal 2**: Get **HM03 (Surf)** from Secret House (Area 3).
- **Time Limit**: Limited steps! Optimize path.

### Warden's House

- Give **Gold Teeth** to Warden (SE Fuchsia).
- **Reward**: **HM04 (Strength)**.

### Koga (Gym)

- **Invisible Walls**: Hug the walls. Look for "dots" in the floor pattern.

---

## 📍 CINNABAR ISLAND

### Getting There

- Fly to Pallet Town, Surf **South**.

### Pokemon Mansion (Abandoned Building)

- **Goal**: Find **Secret Key** (Basement).
- **Puzzle**: Toggle statues (eyes glow) to open/close gates.
- **Jump**: You often need to jump off ledges into holes in the floor to reach lower levels.

### Blaine (Gym)

- **Locked**: Need Secret Key.
- **Quiz**: Answer correctly to skip trainers, or fight them for XP.

---

## 📍 VIRIDIAN GYM (Giovanni Returns)

- Return to Viridian City.
- The Gym is now open.
- Defeat Giovanni for the Earth Badge.

---

## 📍 VICTORY ROAD

- Go West from Viridian -> Route 22.
- Enter League Gate.
- **Victory Road Cave**:
  - Need **Strength** to move boulders onto switches.
  - Switches remove white barriers.
  - Linear but confusing path.

---

## 📍 INDIGO PLATEAU (Elite Four)

- **Lorelei (Ice)**
- **Bruno (Fighting)**
- **Agatha (Ghost)**
- **Lance (Dragon)**
- **Rival (Champion)**

---

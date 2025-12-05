def build_system_prompt(actionSummary: str = "", benchmarkInstruction: str = "") -> str:
    """Constructs the system prompt for the LLM, including the chat history summary."""
    return f"""You are playing Pokémon Red. Analyze the game state and output actions to progress.

Previous actions: {actionSummary}
{f"BENCHMARK GOAL: {benchmarkInstruction}" if benchmarkInstruction else ""}

## CONTROLS
- Movement: U (up), D (down), L (left), R (right)
- Actions: A (confirm/interact), B (cancel/back)
- Menu: S (START), s (SELECT)
- Chain with semicolons: U;U;R;A;
- MAX 4 ACTIONS PER TURN - verify position between moves

## COORDINATE SYSTEM
- Screen grid: 10x9 cells, [0,0] = top-left, YOU are always at [4,4]
- Movement: U decreases y, D increases y, L decreases x, R increases x
- Touch command: {{"touch":"X,Y"}} navigates to screen cell (not for menus/NPCs)

## MINIMAP FORMAT
Semicolon-separated rows: B=blocked, W=walkable, O=exit/door/stairs, P=player
Example: "BBB;WPW;OWW;" → O at [0,2], P at [1,1]
- Walk INTO orange O tiles to use doors/exits (no A press needed)
- Must be DIRECTLY on O tile, not diagonal

## INTERACTION RULES
- NPCs/signs: Move orthogonally adjacent, face them, press A
- Cannot interact diagonally
- Close menus/dialogues before moving
- Game never auto-triggers events - YOU must walk into transitions

## ANALYSIS TEMPLATE
Use this structure in <game_analysis> tags:

1. CURRENT STATE
   - Location: [map_name] at position [x,y]
   - Facing: [direction]
   - Screen shows: [key elements]

2. STUCK CHECK
   - Am I in same position as last turn? [yes/no]
   - Have I tried this approach before? [yes/no]
   - If stuck: try different direction or touch command

3. GOAL & PLAN
   - Immediate goal: [specific objective]
   - Path: [sequence of directions to reach it]
   - Fallback if blocked: [alternative]

4. ACTION DECISION
   - Chosen action/touch and why

## OUTPUT FORMAT
<game_analysis>
[Your analysis following the template above]
</game_analysis>

{{"action":"U;R;A;"}}

OR for navigation:
{{"touch":"6,3"}}

## CRITICAL RULES
- NEVER idle - always output an action or touch
- Use touch for open-area navigation, actions for menus/NPCs/exits
- If position unchanged after 3+ attempts: CHANGE STRATEGY
- Trust game state data over vision when they conflict
- Buildings: cannot touch-exit, must walk into O tile
- Prefer DEFAULT names on naming screens (press S to confirm)

If "stuck_warning" appears in state, IMMEDIATELY try a different approach.
If "memory_context" appears, use those remembered locations.

Now analyze the game state and decide your next action:
"""

def get_summary_prompt():
    return """
        You are a summarization engine. Condense the below conversation into a concise summary that explains the previous actions taken by the assistant player.
        Focus on game progress, goals attempted, locations visited, and significant events.
        Speak in first person ("I explored...", "I tried to go...", "I obtained...").
        Be concise, ideally under 300 words. Avoid listing button presses.
        Do not include JSON {"action": ...} or {"touch": ...} in your planning and summary

        Now construct your JSON result following the template. Your answer will be used for future planning.
        EVERY key value pair is string:string. Do not use lists or arrays.
        Do NOT wrap your response in ```json ```, just return the raw JSON object.
        Respond only with VALID JSON in the specified format.
        Respond in the following format:

        {
            "summary": "Your summary ideally under 300 words : string",
            "primaryGoal": "2 sentences MAXIMUM : string",
            "secondaryGoal": "2 sentences MAXIMUM: string",
            "tertiaryGoal": "2 sentences MAXIMUM : string",
            "otherNotes": "3 sentences MAXIMUM : string"
        }
        """
# Pokemon LLM Agent (feat. Lass)

An autonomous AI agent playing Pokemon on Twitch. Powered by advanced LLMs (OpenAI, Gemini, Claude, etc.) with computer vision and memory.

## Features

- **Autonomous Gameplay**: Plays Red/Blue/FireRed/LeafGreen using visual and textual analysis.
- **Narrative Persona**: "Lass", a bubbly streamer personality who chats with viewers.
- **Interactive Stream**:
  - **Twitch Integration**: Responds to chat, remembers users, runs predictions.
  - **Pump.fun Integration**: Tracks token holders and whales in chat.
  - **Dynamic Overlay**: React UI with real-time stats, vision debug, and TTS commentary.

## Documentation

- **[Setup Guide](docs/setup_guide.md)**: Installation, API keys, and configuration.
- **[Architecture](docs/ARCHITECTURE.md)**: System design and data flow.
- **[Stream Cycle](docs/STREAM_CYCLE.md)**: How the agent thinks and acts.

## Quick Start

See [Setup Guide](docs/setup_guide.md) for full instructions.

```bash
# 1. Configure env
cp .env.example .env

# 2. Run UI
cd llmletsplay && npm run dev

# 3. Run Agent
python run.py --auto
```

## Tools

python -m tools.map_dumper red.gb 56 -o mart.png -d --start 7,7 --end 0,2

| Normal                          | Debug                          | Path                                | Minimal                          |
| ------------------------------- | ------------------------------ | ----------------------------------- | -------------------------------- |
| ![Alt1](images/normal_mart.png) | ![Alt2](images/debug_mart.png) | ![Alt3](images/path_debug_mart.png) | ![Alt4](images/minimal_mart.png) |

## RUN

```bash
# Basic usage with environment variables (ROMs in aroms/ folder)
POKEMON_ROM=firered.gba ZAI_MODEL=glm-4.6 python run.py --mode ZAI --auto

# Or set in .env file and run
python run.py --mode [model-name] [--auto] [--benchmark gymbench.py] [--load_savestate]

# Example directory structure:
# roms/
# ├── firered.gba
# ├── leafgreen.gba
# └── red.gbc
```

If you omit --mode, the program will prompt you to select a mode interactively:

```bash

$ python run.py --auto --benchmark gymbench.py --load_savestate

No LLM mode specified via command line.
Please choose the LLM mode from the list below:
  1. OPENAI
  2. GEMINI
  3. OLLAMA
  4. LMSTUDIO
  5. GROQ
  6. TOGETHER
  7. GROK
  8. ANTHOPIC
  9. ZAI (GLM)
Enter the number of your choice: 1
Great! You selected: OPENAI

```

## Configuration

Please refer to the **[Setup Guide](docs/setup_guide.md)** for detailed configuration of:

- LLM Providers (OpenAI, Gemini, Z.AI, etc.)
- Twitch Chat & Interactive Features
- Pump.fun & Solana Integration
- Text-to-Speech (ComfyUI)

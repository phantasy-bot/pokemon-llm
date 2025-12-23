# 🤖 Pokemon LLM Agent

**Autonomous AI Agent that plays Pokemon Red/FireRed using LLMs.**

![Web UI](images/ui.png)

## 🌟 Key Features
*   **Visual Gameplay**: Uses Vision Models (GLM-4V, GPT-4o) to "see" the game screen.
*   **Smart Navigation**: A* Pathfinding with caching and cross-map routing.
*   **Narrative Engine**: Generates live commentary and TTS audio.
*   **Chronicle Ecosystem**: Mints achievements as Zora Coins on Base L2.
*   **24/7 Autonomy**: Resilient loop with error recovery and state persistence.

## 📚 Documentation

The full technical documentation is available at **[docs.llmletsplay.com](https://docs.llmletsplay.com)**.

### 🚀 Getting Started
*   **[Installation Guide](docs/setup/INSTALLATION.md)**: Setup Python, mGBA, and ROMs.
*   **[Cloudflare Setup](docs/setup/CLOUDFLARE.md)**: Deploy the Chronicle backend.
*   **[Socials Setup](docs/setup/SOCIALS.md)**: Configure Twitter & Discord bots.

### 🧠 Architecture
*   **[System Overview](docs/architecture/SYSTEM_OVERVIEW.md)**: High-level diagrams.
*   **[Stream Cycle](docs/architecture/STREAM_CYCLE.md)**: The main event loop timing.
*   **[Pathfinding](docs/architecture/PATHFINDING.md)**: Deep dive into navigation logic.
*   **[Chronicle System](docs/architecture/CHRONICLE.md)**: Token-gated content architecture.

### 🛠️ Guides
*   **[Testing Runbook](docs/guides/TESTING.md)**: End-to-end testing procedures.
*   **[Dev Markers](docs/guides/DEV_MARKERS.md)**: How to annotate maps for the AI.

---

## ⚡ Quick Run
```bash
python run.py --mode ZAI --auto
```

## 🛠️ Development

### Building Documentation
To build and serve the documentation site locally:
```bash
# Install dependencies
pip install -r requirements.txt

# Build and serve
python -m mkdocs serve
```
The site will be available at `http://127.0.0.1:8000`.

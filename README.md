# 🤖 Pokemon LLM Agent

**Autonomous AI Agent that plays Pokemon Red/FireRed using LLMs.**

![Web UI](../images/ui.png)

## 🌟 Key Features
*   **Visual Gameplay**: Uses Vision Models (GLM-4V, GPT-4o) to "see" the game screen.
*   **Smart Navigation**: A* Pathfinding with caching and cross-map routing.
*   **Narrative Engine**: Generates live commentary and TTS audio.
*   **Chronicle Ecosystem**: Mints achievements as Zora Coins on Base L2.
*   **24/7 Autonomy**: Resilient loop with error recovery and state persistence.

## 📚 Documentation

### 🚀 Getting Started
*   **[Installation Guide](setup/INSTALLATION.md)**: Setup Python, mGBA, and ROMs.
*   **[Cloudflare Setup](setup/CLOUDFLARE.md)**: Deploy the Chronicle backend.
*   **[Socials Setup](setup/SOCIALS.md)**: Configure Twitter & Discord bots.

### 🧠 Architecture
*   **[System Overview](architecture/SYSTEM_OVERVIEW.md)**: High-level diagrams.
*   **[Stream Cycle](architecture/STREAM_CYCLE.md)**: The main event loop timing.
*   **[Pathfinding](architecture/PATHFINDING.md)**: Deep dive into navigation logic.
*   **[Chronicle System](architecture/CHRONICLE.md)**: Token-gated content architecture.

### 🛠️ Guides
*   **[Testing Runbook](guides/TESTING.md)**: End-to-end testing procedures.
*   **[Dev Markers](guides/DEV_MARKERS.md)**: How to annotate maps for the AI.

---

## ⚡ Quick Run
```bash
python run.py --mode ZAI --auto
```

# Installation & Setup

## 📦 Requirements
- **Python 3.10+**
- **Node.js 18+** (for Cloudflare Workers & UI)
- **mGBA** (Development Build with Scripting support)
- **Pokemon ROM** (FireRed `.gba` recommended)

## 🔧 Local Setup

1.  **Clone & Install Python Deps**:
    ```bash
    git clone https://github.com/your-repo/pokemon-llm.git
    cd pokemon-llm
    pip install -r requirements.txt
    ```

2.  **Configure Environment**:
    ```bash
    cp .env.example .env
    # Edit .env with your API keys (OpenAI, Z.AI, etc.)
    ```

3.  **ROM Setup**:
    Place your ROM in the `roms/` folder:
    ```bash
    # Update .env
    POKEMON_ROM=roms/firered.gba
    ```

## 🏃 Running the Agent

```bash
# Basic Run (Interactive Mode Selection)
python run.py

# Auto-Mode with Specific Model
python run.py --mode ZAI --auto

# Run with Benchmarking
python run.py --benchmark scripts/gymbench.py
```

## 🌐 Chronicle Web UI

The UI is hosted on Cloudflare, but for local development:

```bash
cd apps/chronicle-ui
npm install
npm run dev
```
Access at `http://localhost:5173`.

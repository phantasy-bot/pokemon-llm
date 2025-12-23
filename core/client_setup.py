# client_setup.py
import argparse
import os
import logging
from openai import OpenAI, APIError
from core.opencode_client import OpenCodeClient
from dotenv import load_dotenv
import httpx

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger("llm_client_setup")

# --- Configuration Defaults ---
DEFAULT_MODE = "ZAI"  # OPENAI, GEMINI, OLLAMA, LMSTUDIO, GROQ, TOGETHER, GROK, ANTHOPIC, ZAI, ZAI_DIRECT
DEFAULT_OPENAI_MODEL = "o3"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-preview-05-20"
DEFAULT_OLLAMA_MODEL = "gemma3:27b-it-q4_K_M"
DEFAULT_LMSTUDIO_MODEL = "google/gemma-3-27b"
DEFAULT_GROQ_MODEL = "meta-llama/llama-4-maverick-17b-128e-instruct"
DEFAULT_TOGETHER_MODEL = "Qwen/Qwen2.5-VL-72B-Instruct"
DEFAULT_GROK_MODEL = "grok-3-mini"
DEFAULT_ANTHOPIC_MODEL = "claude-sonnet-4-20250514"
DEFAULT_Z_AI_MODEL = "glm-4v"
DEFAULT_Z_AI_DIRECT_MODEL = (
    "glm-4.6v-flash"  # Free multimodal model - combined vision+text
)
DEFAULT_OPENCODE_MODEL = (
    "xai/grok-code-fast-1"  # Default to free/fast model on OpenCode
)
DEFAULT_FEATHERLESS_MODEL = "zai-org/GLM-4.6"

DEFAULT_MODEL_BY_MODE = {
    "OPENAI": DEFAULT_OPENAI_MODEL,
    "GEMINI": DEFAULT_GEMINI_MODEL,
    "OLLAMA": DEFAULT_OLLAMA_MODEL,
    "LMSTUDIO": DEFAULT_LMSTUDIO_MODEL,
    "GROQ": DEFAULT_GROQ_MODEL,
    "TOGETHER": DEFAULT_TOGETHER_MODEL,
    "GROK": DEFAULT_GROK_MODEL,
    "ANTHOPIC": DEFAULT_ANTHOPIC_MODEL,
    "ZAI": DEFAULT_Z_AI_MODEL,
    "ZAI_DIRECT": DEFAULT_Z_AI_DIRECT_MODEL,  # Combined vision+text in single call
    "OPENCODE": DEFAULT_OPENCODE_MODEL,
    "FEATHERLESS": DEFAULT_FEATHERLESS_MODEL,
}

# --- Vision Configuration ---
# Valid providers: "ZAI", "ZAI_DIRECT", "COMFYUI", "DEFAULT" (uses main LLM if possible)
DEFAULT_VISION_PROVIDER = "DEFAULT"
# Models to use when VISION_PROVIDER is ZAI/ZAI_DIRECT
DEFAULT_VISION_MODEL = "glm-4.6v-flash"

MODES = list(DEFAULT_MODEL_BY_MODE.keys())

load_dotenv()  # Load variables from .env file


def get_config(env_var: str, default_value: str) -> str:
    """Gets configuration from environment variable or returns default."""
    value = os.getenv(env_var, default_value)
    source = "Env Var" if os.getenv(env_var) else "Default"
    # Avoid logging sensitive keys like API keys directly
    if "API_KEY" not in env_var:
        log.info(f"Config '{env_var}': {value} (Source: {source})")
    else:
        # Log API keys securely (presence only)
        log.info(
            f"Config '{env_var}': {'Present' if value else 'Not Set'} (Source: {source})"
        )
    return value


# --- Additional Configuration ---
REASONING_EFFORT = get_config(
    "REASONING_EFFORT", "high"
)  # can be "low", "medium", or "high"
ONE_IMAGE_PER_PROMPT = os.getenv("ONE_IMAGE_PER_PROMPT", "True").lower() == "true"
MINIMAP_ENABLED = os.getenv("MINIMAP_ENABLED", "True").lower() == "true"
MINIMAP_2D = os.getenv("MINIMAP_2D", "True").lower() == "true"
REASONING_ENABLED = os.getenv("REASONING_ENABLED", "True").lower() == "true"
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "2048"))
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.7"))
IMAGE_DETAIL = get_config("IMAGE_DETAIL", "high")  # can be "low", or "high"

SYSTEM_PROMPT_UNSUPPORTED = (
    False  # Instead it will be injected into messages. (NOT IMPLEMENTED YET)
)
USES_MAX_COMPLETION_TOKENS = True  # Some models (OAI o3) require setting max_completion_tokens instead of max_tokens
USES_DEFAULT_TEMPERATURE = True  # Some models (OAI o3) don't support temperature, so we use a default value (1)

TIMEOUT = httpx.Timeout(15.0, read=15.0, write=10.0, connect=10.0)


# helper function for selecting AI model
def parse_mode_arg(modes, default_mode=DEFAULT_MODE):
    parser = argparse.ArgumentParser(
        description="Parse LLM mode argument", add_help=False
    )

    parser.add_argument(
        "--mode",
        choices=modes,
        help="LLM mode to use (choose from the supported modes)",
    )

    # Use parse_known_args to ignore other arguments
    args, _ = parser.parse_known_args()
    mode = args.mode

    if not mode:
        # Prioritize LLM_PROVIDER
        env_mode = os.getenv("LLM_PROVIDER")
        if env_mode and env_mode in modes:
            print(f"\nNo LLM mode specified via command line.")
            print(f"Using LLM_PROVIDER from .env: {env_mode}")
            mode = env_mode
        else:
            if env_mode:
                print(
                    f"\nWarning: LLM_PROVIDER='{env_mode}' in .env is not valid. Valid modes: {modes}"
                )
            print(f"No LLM mode specified via command line or .env.")
            print(f"Using default mode: {default_mode}")
            mode = default_mode
    else:
        print(f"LLM mode specified via command line: {mode}")

    # Show the actual model that will be used (from env var or default)
    # Handle the Z_AI naming convention shift for model config lookups
    mode_str = str(mode) if mode else DEFAULT_MODE

    if mode_str == "ZAI":
        model_env_var = "Z_AI_MODEL"
    elif mode_str == "ZAI_DIRECT":
        model_env_var = "Z_AI_DIRECT_MODEL"
    else:
        model_env_var = f"{mode_str}_MODEL"

    actual_model = get_config(
        model_env_var, DEFAULT_MODEL_BY_MODE.get(mode_str, "UNKNOWN")
    )
    print(f"Using model: {actual_model}")

    return mode_str


def setup_llm_client(mode: str = None) -> tuple[OpenAI | None, str | None, bool]:
    if mode is None:
        MODE = parse_mode_arg(MODES)
    else:
        MODE = mode

    # Ensure MODE is a string for type safety
    if MODE is None:
        MODE = DEFAULT_MODE

    client = None
    model = None
    supports_reasoning = False

    log.info(f"--- Initializing LLM Client (Mode: {MODE}) ---")

    # Determine if LLM supports vision natively (can be overridden by env var)
    # Default assumption: Most modern models support vision, but specific text-only models don't.
    # User should set LLM_SUPPORTS_VISION=false for text-only models like o1-preview or deepseek-reasoner
    llm_supports_vision_default = True
    if MODE == "OLLAMA" and "llama" in get_config("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL):
        # Heuristic: base llamas often text-only unless explicitly vision
        pass

    if MODE == "OPENCODE":
        opencode_model = get_config("OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL)
        if "grok-code" in opencode_model:
            llm_supports_vision_default = False

    llm_supports_vision_str = os.getenv(
        "LLM_SUPPORTS_VISION", str(llm_supports_vision_default)
    ).lower()
    llm_supports_vision = llm_supports_vision_str in ("true", "1", "yes", "on")

    log.info(f"LLM Vision Support: {llm_supports_vision}")

    if MODE == "OPENAI":
        # OpenAI requires a real API key from environment
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            log.error(
                "MODE is OPENAI but OPENAI_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(api_key=api_key, timeout=TIMEOUT)
            model = get_config("OPENAI_MODEL", DEFAULT_OPENAI_MODEL)
            supports_reasoning = True
            log.info(f"Using OpenAI Mode. Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize OpenAI client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "GEMINI":
        # Gemini requires a real API key from environment
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            log.error(
                "MODE is GEMINI but GEMINI_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                timeout=TIMEOUT,
            )
            model = get_config("GEMINI_MODEL", DEFAULT_GEMINI_MODEL)
            supports_reasoning = True
            log.info(f"Using Gemini Mode (via OpenAI client). Model: {model}")
        except Exception as e:
            log.error(
                f"Failed to initialize Gemini client (via OpenAI compat): {e}",
                exc_info=True,
            )
            return None, None, False

    elif MODE == "OLLAMA":
        ollama_base_url = get_config("OLLAMA_BASE_URL", "http://localhost:11434/v1")
        try:
            client = OpenAI(
                base_url=ollama_base_url,
                api_key="ollama",  # Hardcoded placeholder key for Ollama
            )
            model = get_config("OLLAMA_MODEL", DEFAULT_OLLAMA_MODEL)
            # supports_reasoning = True # Not sure for this
            log.info(
                f"Using Ollama Mode. Base URL: {ollama_base_url}, Model: {model} (API Key: Placeholder)"
            )
        except Exception as e:
            log.error(f"Failed to initialize Ollama client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "LMSTUDIO":
        lmstudio_base_url = get_config("LMSTUDIO_BASE_URL", "http://localhost:1234/v1")
        try:
            client = OpenAI(
                base_url=lmstudio_base_url,
                api_key="lmstudio",  # Hardcoded placeholder key for LMStudio
            )
            model = get_config("LMSTUDIO_MODEL", DEFAULT_LMSTUDIO_MODEL)
            log.info(
                f"Using LMStudio Mode. Base URL: {lmstudio_base_url}, Model: {model} (API Key: Placeholder)"
            )
        except Exception as e:
            log.error(f"Failed to initialize LMStudio client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "GROQ":
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            log.error(
                "MODE is GROQ but GROQ_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=api_key,
                timeout=TIMEOUT,
            )
            model = get_config("GROQ_MODEL", DEFAULT_GROQ_MODEL)
            log.info(f"Using Groq Mode (via OpenAI client). Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize Groq client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "GROK":
        api_key = os.getenv("GROK_API_KEY")
        if not api_key:
            log.error(
                "MODE is GROK but GROK_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(
                base_url="https://api.x.ai/v1", api_key=api_key, timeout=TIMEOUT
            )
            supports_reasoning = True  # Grok supports reasoning
            model = get_config("GROK_MODEL", DEFAULT_GROK_MODEL)
            log.info(f"Using Grok Mode (via OpenAI client). Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize Grok client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "ANTHOPIC":
        api_key = os.getenv("ANTHOPIC_API_KEY")
        if not api_key:
            log.error(
                "MODE is ANTHOPIC but ANTHOPIC_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(
                base_url="https://api.anthropic.com/v1/",
                api_key=api_key,
                timeout=TIMEOUT,
            )
            supports_reasoning = True
            model = get_config("ANTHOPIC_MODEL", DEFAULT_ANTHOPIC_MODEL)
            log.info(f"Using ANTHOPIC Mode (via OpenAI client). Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize ANTHOPIC client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "TOGETHER":
        api_key = os.getenv("TOGETHER_API_KEY")
        if not api_key:
            log.error(
                "MODE is TOGETHER but TOGETHER_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            client = OpenAI(
                base_url="https://api.together.xyz/v1", api_key=api_key, timeout=TIMEOUT
            )
            model = get_config("TOGETHER_MODEL", DEFAULT_TOGETHER_MODEL)
            log.info(f"Using Together Mode (via OpenAI client). Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize Together client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "ZAI":
        # Standardize on Z_AI_API_KEY
        api_key = os.getenv("Z_AI_API_KEY")
        if not api_key:
            log.error(
                "MODE is ZAI but Z_AI_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            # Use Z.AI coding plan endpoint for reasoning capabilities
            # Standardize on Z_AI_BASE_URL
            base_url = get_config(
                "Z_AI_BASE_URL", "https://api.z.ai/api/coding/paas/v4"
            )
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=TIMEOUT)
            # Standardize on Z_AI_MODEL
            model = get_config("Z_AI_MODEL", DEFAULT_Z_AI_MODEL)
            supports_reasoning = True  # GLM-4.6 supports reasoning
            log.info(
                f"Using Z.AI Standard API for multimodal capabilities (via OpenAI client). Model: {model}"
            )
        except Exception as e:
            log.error(f"Failed to initialize Z.AI client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "ZAI_DIRECT":
        # ZAI_DIRECT: Use standard Z.AI API with GLM-4.6V-flash for combined vision+text
        # This mode embeds images directly in the API call, eliminating the need for separate vision analysis
        api_key = os.getenv("Z_AI_API_KEY")  # Same API key as ZAI
        if not api_key:
            log.error(
                "MODE is ZAI_DIRECT but Z_AI_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            # Standard API endpoint (not coding plan)
            # Standardize on Z_AI_DIRECT_BASE_URL? Or just default if not set.
            # Keeping ZAI_DIRECT prefix for specific mode override seems ok, but let's check consistent naming.
            # Z_AI_BASE_URL is for the main one. Let's use Z_AI_DIRECT_BASE_URL for this if needed.
            base_url = get_config(
                "Z_AI_DIRECT_BASE_URL", "https://api.z.ai/api/paas/v4"
            )
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=TIMEOUT)
            # Standardize on Z_AI_DIRECT_MODEL
            model = get_config("Z_AI_DIRECT_MODEL", DEFAULT_Z_AI_DIRECT_MODEL)
            supports_reasoning = False  # Standard API doesn't use thinking param
            log.info(
                f"Using Z.AI Direct API (combined vision+text). Base URL: {base_url}, Model: {model}"
            )
        except Exception as e:
            log.error(f"Failed to initialize Z.AI Direct client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "OPENCODE":
        base_url = get_config("OPENCODE_BASE_URL", "http://localhost:4096")
        try:
            client = OpenCodeClient(base_url=base_url)
            model = get_config("OPENCODE_MODEL", DEFAULT_OPENCODE_MODEL)
            supports_reasoning = True
            log.info(f"Using OpenCode Mode. Base URL: {base_url}, Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize OpenCode client: {e}", exc_info=True)
            return None, None, False

    elif MODE == "FEATHERLESS":
        api_key = os.getenv("FEATHERLESS_API_KEY")
        if not api_key:
            log.error(
                "MODE is FEATHERLESS but FEATHERLESS_API_KEY not found in environment variables."
            )
            return None, None, False
        try:
            base_url = get_config(
                "FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"
            )
            client = OpenAI(base_url=base_url, api_key=api_key, timeout=TIMEOUT)
            model = get_config("FEATHERLESS_MODEL", DEFAULT_FEATHERLESS_MODEL)
            supports_reasoning = False
            log.info(f"Using Featherless Mode. Base URL: {base_url}, Model: {model}")
        except Exception as e:
            log.error(f"Failed to initialize Featherless client: {e}", exc_info=True)
            return None, None, False

    else:
        log.error(
            f"Invalid MODE selected: {MODE}. Set LLM_PROVIDER or MODE environment variable correctly (e.g., OPENAI, GEMINI, OLLAMA, LMSTUDIO, ZAI, ZAI_DIRECT, OPENCODE)."
        )
        return None, None, False

    if client and model:
        try:
            log.info(f"Attempting to verify connection to {MODE} service...")
            models_list = client.models.list()
            log.info(
                f"Successfully connected to {MODE} service (Base URL: {client.base_url}). Found {len(models_list.data)} models."
            )
        except APIError as e:
            log.error(
                f"APIError verifying connection to {MODE}: {e}. Check URL/Permissions/Service Status."
            )
        except Exception as e:
            log.warning(
                f"Unexpected error verifying {MODE} connection: {e}. Proceeding cautiously."
            )

    log.info(f"LLM Client setup complete. Image Detail: {IMAGE_DETAIL}")
    print(f"Client: {client}, model: {model}, supports_reasoning: {supports_reasoning}")

    if not llm_supports_vision:
        log.warning(
            "⚠️ LLM configured as TEXT-ONLY. Images will NOT be sent to the main model."
        )

    return client, model, supports_reasoning

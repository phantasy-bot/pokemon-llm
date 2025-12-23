#!/usr/bin/env python3
"""
Master build script for Lass Pokemon Agent Documentation.
Orchestrates modular doc generators and runs MkDocs.
"""

import subprocess
import sys
import os
from pathlib import Path

# Configuration
PROJECT_ROOT = Path(__file__).parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
PYTHON_EXE = sys.executable  # Use current interpreter


def run_script(script_name: str):
    """Run a documentation subscript."""
    print(f"--- Running {script_name} ---")
    script_path = SCRIPTS_DIR / script_name
    if not script_path.exists():
        print(f"Error: Script {script_name} not found at {script_path}")
        return False

    try:
        result = subprocess.run(
            [PYTHON_EXE, str(script_path)], check=True, capture_output=True, text=True
        )
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {script_name}:")
        print(e.stderr)
        return False


def run_typedoc(app_dir: str):
    """Run TypeDoc for a specific frontend app."""
    print(f"--- Running TypeDoc for {app_dir} ---")
    app_path = PROJECT_ROOT / "apps" / app_dir
    if not app_path.exists():
        print(f"Error: App directory {app_dir} not found")
        return False

    try:
        # Use npx to run typedoc with skipErrorChecking to avoid dependency errors
        result = subprocess.run(
            ["npx", "typedoc", "--skipErrorChecking"],
            cwd=app_path,
            check=True,
            capture_output=True,
            text=True,
        )
        print(f"TypeDoc completed for {app_dir}")
        return True

    except subprocess.CalledProcessError as e:
        print(f"Error running TypeDoc for {app_dir}:")
        print(e.stderr)
        return False
    except FileNotFoundError:
        print("Error: 'npx' or 'typedoc' not found. Please install node/npm.")
        return False


def build_mkdocs():
    """Run mkdocs build."""
    print("--- Building MkDocs Site ---")
    try:
        # Use python -m mkdocs to ensure we use the correct environment
        result = subprocess.run(
            [PYTHON_EXE, "-m", "mkdocs", "build"],
            check=True,
            capture_output=True,
            text=True,
        )
        print(result.stdout)
        print("Success: Documentation built in site/ directory")
        return True
    except subprocess.CalledProcessError as e:
        print("Error building MkDocs:")
        print(e.stderr)
        return False
    except Exception as e:
        print(f"Unexpected error building MkDocs: {e}")
        return False


def main():
    # 1. Run modular generators (YAML -> MD)
    subscripts = [
        "generate_game_docs.py",
        "generate_prompt_docs.py",
    ]

    success = True
    for script in subscripts:
        if not run_script(script):
            success = False

    # 2. Run TypeDoc for frontend apps
    frontend_apps = [
        "livestream",
        "chronicle-ui",
        "chronicle-worker",
    ]
    for app in frontend_apps:
        if not run_typedoc(app):
            success = False

    if not success:
        print(
            "Warning: One or more subscripts or TypeDoc builds failed. Continuing to MkDocs build..."
        )

    # 3. Build the site
    if build_mkdocs():
        print("\nDocumentation build complete!")
    else:
        print("\nDocumentation build failed.")
        sys.exit(1)


if __name__ == "__main__":
    main()

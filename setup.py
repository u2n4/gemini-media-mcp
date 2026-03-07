#!/usr/bin/env python3
"""
Gemini Media MCP -- Interactive Setup Script

Cross-platform installer for VEO 3.1 and NanoBanana MCP servers.
Installs dependencies, configures environment, and registers servers
with Claude Desktop and/or Claude Code.

Requirements: Python 3.10+, stdlib only.
"""

import json
import os
import platform
import subprocess
import sys
from pathlib import Path


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent
VEO_SERVER_PATH = REPO_ROOT / "servers" / "veo" / "server.py"
VEO_REQUIREMENTS = REPO_ROOT / "servers" / "veo" / "requirements.txt"
NANOBANANA_REQUIREMENTS = REPO_ROOT / "servers" / "nanobanana" / "requirements.txt"
ENV_EXAMPLE = REPO_ROOT / ".env.example"
ENV_FILE = REPO_ROOT / ".env"

CHOICE_VEO = "1"
CHOICE_NANOBANANA = "2"
CHOICE_BOTH = "3"


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def banner() -> None:
    print()
    print("=" * 60)
    print("  Gemini Media MCP -- Setup")
    print("  VEO 3.1 Video + NanoBanana Image Generation")
    print("=" * 60)
    print()


def detect_os() -> str:
    """Return 'windows', 'macos', or 'linux'."""
    system = platform.system().lower()
    if system == "windows":
        return "windows"
    if system == "darwin":
        return "macos"
    return "linux"


def get_python_cmd() -> str:
    """Return the Python executable path used to run this script."""
    return sys.executable


def get_video_output_dir(os_name: str) -> str:
    """Return the default VIDEO_OUTPUT_DIR for the detected OS."""
    home = Path.home()
    return str(home / "veo-videos")


def get_claude_desktop_config_path(os_name: str) -> Path | None:
    """Return the path to claude_desktop_config.json for the detected OS."""
    if os_name == "windows":
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "Claude" / "claude_desktop_config.json"
        return None
    if os_name == "macos":
        return Path.home() / "Library" / "Application Support" / "Claude" / "claude_desktop_config.json"
    # linux
    return Path.home() / ".config" / "claude" / "claude_desktop_config.json"


def prompt_yes_no(question: str, default_yes: bool = True) -> bool:
    """Prompt the user for a yes/no answer."""
    suffix = " [Y/n]: " if default_yes else " [y/N]: "
    answer = input(question + suffix).strip().lower()
    if not answer:
        return default_yes
    return answer in ("y", "yes")


def run_pip_install(args: list[str], description: str) -> bool:
    """Run a pip install command. Returns True on success."""
    cmd = [get_python_cmd(), "-m", "pip", "install"] + args
    print(f"  Running: {' '.join(cmd)}")
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            print(f"  [ERROR] {description} failed:")
            print(f"  {result.stderr.strip()}")
            return False
        print(f"  [OK] {description} succeeded.")
        return True
    except subprocess.TimeoutExpired:
        print(f"  [ERROR] {description} timed out after 5 minutes.")
        return False
    except Exception as exc:
        print(f"  [ERROR] {description} failed: {exc}")
        return False


# ---------------------------------------------------------------------------
# Installation steps
# ---------------------------------------------------------------------------

def install_veo_deps() -> bool:
    """Install VEO server dependencies from requirements.txt."""
    print()
    print("--- Installing VEO 3.1 dependencies ---")
    if not VEO_REQUIREMENTS.exists():
        print(f"  [ERROR] Requirements file not found: {VEO_REQUIREMENTS}")
        return False
    return run_pip_install(
        ["-r", str(VEO_REQUIREMENTS)],
        "VEO dependencies",
    )


def install_nanobanana_deps() -> bool:
    """Install NanoBanana via pip package."""
    print()
    print("--- Installing NanoBanana dependencies ---")
    print("  Attempting pip install nanobanana-mcp-server ...")
    success = run_pip_install(
        ["nanobanana-mcp-server"],
        "NanoBanana (pip package)",
    )
    if not success:
        print("  pip package install failed. Falling back to bundled requirements ...")
        if NANOBANANA_REQUIREMENTS.exists():
            success = run_pip_install(
                ["-r", str(NANOBANANA_REQUIREMENTS)],
                "NanoBanana (bundled requirements)",
            )
        else:
            print(f"  [ERROR] Bundled requirements not found: {NANOBANANA_REQUIREMENTS}")
    return success


def setup_env_file() -> str:
    """
    Create .env from .env.example if needed, prompting for GEMINI_API_KEY.
    Returns the API key string (may be empty if user skips).
    """
    print()
    print("--- Environment configuration ---")

    api_key = ""

    if ENV_FILE.exists():
        print(f"  .env file already exists at: {ENV_FILE}")
        # Read existing key
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("GEMINI_API_KEY=") and not line.startswith("GEMINI_API_KEY_BACKUP"):
                    api_key = line.split("=", 1)[1].strip()
                    break
        if api_key and api_key != "your_gemini_api_key_here":
            print("  GEMINI_API_KEY is already set.")
            return api_key
        print("  GEMINI_API_KEY is not configured yet.")
    else:
        print(f"  Creating .env from .env.example ...")
        if ENV_EXAMPLE.exists():
            with open(ENV_EXAMPLE, "r", encoding="utf-8") as src:
                content = src.read()
            with open(ENV_FILE, "w", encoding="utf-8") as dst:
                dst.write(content)
            print(f"  [OK] Created: {ENV_FILE}")
        else:
            # Create a minimal .env
            with open(ENV_FILE, "w", encoding="utf-8") as dst:
                dst.write("GEMINI_API_KEY=your_gemini_api_key_here\n")
            print(f"  [OK] Created minimal .env at: {ENV_FILE}")

    print()
    print("  A Gemini API key is required for both servers.")
    print("  Get one free at: https://aistudio.google.com/apikey")
    print()
    api_key = input("  Enter your GEMINI_API_KEY (or press Enter to skip): ").strip()

    if api_key:
        # Update .env file with the new key
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()

        updated = False
        new_lines = []
        for line in lines:
            if line.strip().startswith("GEMINI_API_KEY=") and not line.strip().startswith("GEMINI_API_KEY_BACKUP"):
                new_lines.append(f"GEMINI_API_KEY={api_key}\n")
                updated = True
            else:
                new_lines.append(line)

        if not updated:
            new_lines.insert(0, f"GEMINI_API_KEY={api_key}\n")

        with open(ENV_FILE, "w", encoding="utf-8") as f:
            f.writelines(new_lines)

        print("  [OK] GEMINI_API_KEY saved to .env")
    else:
        print("  [SKIP] No key entered. You can set it later in .env")

    return api_key


def build_veo_config(api_key: str, video_output_dir: str) -> dict:
    """Build the Claude Desktop MCP config entry for VEO."""
    env = {"GEMINI_API_KEY": api_key or "YOUR_GEMINI_API_KEY"}
    env["VIDEO_OUTPUT_DIR"] = video_output_dir
    return {
        "command": "python",
        "args": [str(VEO_SERVER_PATH)],
        "env": env,
    }


def build_nanobanana_config(api_key: str) -> dict:
    """Build the Claude Desktop MCP config entry for NanoBanana."""
    return {
        "command": "python",
        "args": ["-m", "nanobanana_mcp_server.server"],
        "env": {
            "GEMINI_API_KEY": api_key or "YOUR_GEMINI_API_KEY",
        },
    }


def read_existing_config(config_path: Path) -> dict:
    """Read existing Claude Desktop config, preserving all entries."""
    if not config_path.exists():
        return {}
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Strip UTF-8 BOM if present (we will write without BOM)
        if content.startswith("\ufeff"):
            content = content[1:]
        return json.loads(content)
    except (json.JSONDecodeError, OSError) as exc:
        print(f"  [WARNING] Could not parse existing config: {exc}")
        print("  A backup will be created before overwriting.")
        return {}


def write_config_no_bom(config_path: Path, data: dict) -> None:
    """
    Write JSON config WITHOUT UTF-8 BOM.
    This is critical on Windows -- Claude Desktop may reject BOM-prefixed configs.
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)

    json_str = json.dumps(data, indent=2, ensure_ascii=False)

    # Write raw bytes to guarantee no BOM
    with open(config_path, "wb") as f:
        f.write(json_str.encode("utf-8"))

    print(f"  [OK] Config written (no BOM): {config_path}")


def configure_claude_desktop(
    os_name: str,
    install_veo: bool,
    install_nano: bool,
    api_key: str,
    video_output_dir: str,
) -> bool:
    """Auto-configure Claude Desktop by merging server entries into its config."""
    print()
    print("--- Claude Desktop configuration ---")

    config_path = get_claude_desktop_config_path(os_name)
    if config_path is None:
        print("  [SKIP] Could not determine Claude Desktop config path.")
        return False

    print(f"  Config path: {config_path}")

    # Check if Claude Desktop is installed (config dir exists or we can create it)
    if not config_path.parent.exists():
        print(f"  Claude Desktop config directory not found: {config_path.parent}")
        if not prompt_yes_no("  Create the directory and config anyway?", default_yes=False):
            print("  [SKIP] Claude Desktop configuration skipped.")
            return False

    # Read existing config
    existing = read_existing_config(config_path)

    # Back up existing config if it has content
    if existing and config_path.exists():
        backup_path = config_path.with_suffix(".json.bak")
        try:
            with open(config_path, "rb") as src:
                raw = src.read()
            with open(backup_path, "wb") as dst:
                dst.write(raw)
            print(f"  [OK] Backup saved: {backup_path}")
        except OSError as exc:
            print(f"  [WARNING] Could not create backup: {exc}")

    # Merge MCP servers
    mcp_servers = existing.get("mcpServers", {})

    if install_veo:
        if "veo" in mcp_servers:
            print("  'veo' entry already exists -- it will be updated.")
        mcp_servers["veo"] = build_veo_config(api_key, video_output_dir)

    if install_nano:
        if "nanobanana" in mcp_servers:
            print("  'nanobanana' entry already exists -- it will be updated.")
        mcp_servers["nanobanana"] = build_nanobanana_config(api_key)

    # Build final config preserving all other keys
    final_config = dict(existing)
    final_config["mcpServers"] = mcp_servers

    write_config_no_bom(config_path, final_config)
    return True


def show_claude_code_commands(
    install_veo: bool,
    install_nano: bool,
    api_key: str,
    video_output_dir: str,
) -> None:
    """Print the `claude mcp add` commands for Claude Code users."""
    print()
    print("--- Claude Code configuration ---")
    print()
    print("  If you use Claude Code (CLI), add the servers with these commands:")
    print()

    display_key = api_key if api_key else "YOUR_GEMINI_API_KEY"

    if install_veo:
        veo_path = str(VEO_SERVER_PATH)
        print("  # VEO 3.1 server:")
        print(f"  claude mcp add veo -e GEMINI_API_KEY={display_key} -e VIDEO_OUTPUT_DIR={video_output_dir} -- python \"{veo_path}\"")
        print()

    if install_nano:
        print("  # NanoBanana server:")
        print(f"  claude mcp add nanobanana -e GEMINI_API_KEY={display_key} -- python -m nanobanana_mcp_server.server")
        print()


def show_success(install_veo: bool, install_nano: bool) -> None:
    """Print a final success message."""
    print()
    print("=" * 60)
    print("  Setup complete!")
    print("=" * 60)
    print()

    servers_installed = []
    if install_veo:
        servers_installed.append("VEO 3.1 (video generation)")
    if install_nano:
        servers_installed.append("NanoBanana (image generation)")

    print("  Installed servers:")
    for s in servers_installed:
        print(f"    - {s}")

    print()
    print("  Next steps:")
    print("    1. Restart Claude Desktop to load the new MCP servers.")
    print("    2. Test VEO:       Ask Claude to run 'veo_api_status'")
    print("    3. Test NanoBanana: Ask Claude to run 'show_output_stats'")
    print()
    print("  If you skipped the API key, edit .env and set GEMINI_API_KEY.")
    print("  Get a free key at: https://aistudio.google.com/apikey")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    banner()

    # Detect OS
    os_name = detect_os()
    print(f"  Detected OS:     {os_name} ({platform.system()} {platform.release()})")
    print(f"  Python:          {sys.version.split()[0]} ({get_python_cmd()})")
    print(f"  Repository root: {REPO_ROOT}")
    print()

    # Interactive menu
    print("  Which servers would you like to install?")
    print()
    print("    [1] Install VEO server only        (video generation)")
    print("    [2] Install NanoBanana server only  (image generation)")
    print("    [3] Install both (recommended)")
    print()

    choice = ""
    while choice not in (CHOICE_VEO, CHOICE_NANOBANANA, CHOICE_BOTH):
        choice = input("  Enter your choice (1/2/3): ").strip()
        if choice not in (CHOICE_VEO, CHOICE_NANOBANANA, CHOICE_BOTH):
            print("  Invalid choice. Please enter 1, 2, or 3.")

    install_veo = choice in (CHOICE_VEO, CHOICE_BOTH)
    install_nano = choice in (CHOICE_NANOBANANA, CHOICE_BOTH)

    # Step 1: Install dependencies
    success = True

    if install_veo:
        if not install_veo_deps():
            success = False
            print("  [WARNING] VEO dependency installation had errors.")

    if install_nano:
        if not install_nanobanana_deps():
            success = False
            print("  [WARNING] NanoBanana dependency installation had errors.")

    if not success:
        if not prompt_yes_no("  Some dependencies failed to install. Continue anyway?"):
            print("  Setup aborted.")
            sys.exit(1)

    # Step 2: Setup .env and get API key
    api_key = setup_env_file()

    # Step 3: Determine VIDEO_OUTPUT_DIR
    video_output_dir = get_video_output_dir(os_name)
    if install_veo:
        print()
        print(f"  Default video output directory: {video_output_dir}")
        custom_dir = input("  Press Enter to accept, or type a custom path: ").strip()
        if custom_dir:
            video_output_dir = custom_dir
        # Create the directory if it does not exist
        try:
            Path(video_output_dir).mkdir(parents=True, exist_ok=True)
            print(f"  [OK] Video output directory ready: {video_output_dir}")
        except OSError as exc:
            print(f"  [WARNING] Could not create directory: {exc}")
            print("  You may need to create it manually.")

    # Step 4: Configure Claude Desktop
    if prompt_yes_no("  Configure Claude Desktop automatically?"):
        configure_claude_desktop(os_name, install_veo, install_nano, api_key, video_output_dir)
    else:
        print("  [SKIP] Claude Desktop auto-configuration skipped.")

    # Step 5: Show Claude Code commands
    show_claude_code_commands(install_veo, install_nano, api_key, video_output_dir)

    # Step 6: Success
    show_success(install_veo, install_nano)


if __name__ == "__main__":
    main()

#!/usr/bin/env bash
# cold-install-smoke.sh — release gate for omni-mcp-server and nanobanana-imagen-mcp
#
# Usage:
#   bash scripts/cold-install-smoke.sh
#
# What it does (per package):
#   1. uv build --wheel
#   2. Create a fresh virtual environment
#   3. pip install --no-cache-dir <wheel>
#   4. pip install twine && twine check dist/*
#   5. python -c "import <module>; assert <module>.__version__ matches the package version"
#   6. Run <entry-point> --version
#   7. Run <entry-point> --help
#   8. Assert no home-directory pollution (~/omni-videos, ~/nanobanana-images)
#
# Exit code 0 = all checks passed.  Non-zero = failure (check stderr).

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
unset GEMINI_API_KEY GOOGLE_API_KEY GEMINI_API_KEY_BACKUP
export PYTHON_DOTENV_DISABLED=1

# Use a temporary home to detect home-dir pollution
FAKE_HOME="$(mktemp -d)"
trap 'rm -rf "$FAKE_HOME"' EXIT

echo "=== Cold-install smoke test ==="
echo "    Repo:      $REPO_ROOT"
echo "    Fake home: $FAKE_HOME"
echo ""

# ── Helper ────────────────────────────────────────────────────────────────────

smoke_package() {
    local pkg_dir="$1"         # e.g. servers/omni
    local dist_name="$2"       # e.g. omni-mcp-server
    local module_name="$3"     # e.g. omni_mcp_server
    local entry_point="$4"     # e.g. omni-mcp-server
    local expected_version="$6"
    local home_marker="$5"     # e.g. omni-videos (checked under FAKE_HOME)

    echo "──────────────────────────────────────────────────"
    echo "  Package : $dist_name"
    echo "──────────────────────────────────────────────────"

    cd "$REPO_ROOT/$pkg_dir"

    # 1. Build wheel
    echo "[1/8] Building wheel..."
    uv build --wheel --out-dir dist/
    WHEEL="$(ls dist/*.whl | tail -1)"
    echo "      Built: $WHEEL"

    # 4a. twine check (before install, just needs the wheel file)
    echo "[4a/8] twine check..."
    pip install --quiet twine
    twine check "$WHEEL"
    echo "      twine check passed"

    # 2. Fresh venv
    VENV_DIR="$(mktemp -d)"
    echo "[2/8] Creating fresh venv at $VENV_DIR ..."
    python -m venv "$VENV_DIR"

    # 3. Install wheel
    echo "[3/8] Installing wheel (no-cache)..."
    "$VENV_DIR/bin/pip" install --no-cache-dir --quiet "$WHEEL" 2>/dev/null \
        || "$VENV_DIR/Scripts/pip" install --no-cache-dir --quiet "$WHEEL"

    # Detect pip/python path (cross-platform: bin/ on Unix, Scripts/ on Windows)
    if [ -f "$VENV_DIR/bin/python" ]; then
        VENV_PYTHON="$VENV_DIR/bin/python"
        VENV_ENTRY="$VENV_DIR/bin/$entry_point"
    else
        VENV_PYTHON="$VENV_DIR/Scripts/python"
        VENV_ENTRY="$VENV_DIR/Scripts/$entry_point"
    fi

    # 5. Version assertion
    echo "[5/8] Asserting __version__ == '$expected_version' ..."
    HOME="$FAKE_HOME" "$VENV_PYTHON" -c "
import $module_name
v = $module_name.__version__
assert v == '$expected_version', f'__version__ is {v!r}, expected $expected_version'
print('    __version__ OK:', v)
"

    # 6. Entry-point --version
    echo "[6/8] Running $entry_point --version ..."
    HOME="$FAKE_HOME" "$VENV_ENTRY" --version

    # 7. Entry-point --help
    echo "[7/8] Running $entry_point --help ..."
    HOME="$FAKE_HOME" "$VENV_ENTRY" --help

    # 8. Home pollution check
    echo "[8/8] Checking no home-dir pollution..."
    if [ -d "$FAKE_HOME/$home_marker" ]; then
        echo "FAIL: $FAKE_HOME/$home_marker was created — eager mkdir detected!"
        exit 1
    fi
    echo "      No home-dir pollution detected."

    # Cleanup venv
    rm -rf "$VENV_DIR"

    echo "  PASSED: $dist_name"
    echo ""
    cd "$REPO_ROOT"
}

# ── Run for both packages ─────────────────────────────────────────────────────

smoke_package \
    "servers/omni" \
    "omni-mcp-server" \
    "omni_mcp_server" \
    "omni-mcp-server" \
    "omni-videos" \
    "2.0.0"

smoke_package \
    "servers/nanobanana" \
    "nanobanana-imagen-mcp" \
    "nanobanana_mcp_server" \
    "nanobanana-imagen-mcp" \
    "nanobanana-images" \
    "1.2.0"

echo "=== All cold-install smoke tests passed ==="

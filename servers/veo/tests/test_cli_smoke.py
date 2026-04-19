"""
CLI smoke tests for veo-mcp-server.

These tests verify:
  (a) The package can be imported with no API keys in the environment
      without triggering sys.exit (lazy init check).
  (b) `veo-mcp-server --help` exits 0 with a dummy GEMINI_API_KEY.
  (c) `veo-mcp-server --version` exits 0 and prints the version string
      (skipped when running from source tree without the package installed).

All tests use subprocess so that any accidental sys.exit is caught without
killing the pytest process.
"""

import os
import subprocess
import sys



def _base_env(tmp_path) -> dict:
    """Minimal Windows-safe environment for subprocess calls."""
    env = {
        "GEMINI_API_KEY": "dummy-key-for-testing",
        "VIDEO_OUTPUT_DIR": str(tmp_path / "veo-videos"),
        "PATH": os.environ.get("PATH", ""),
    }
    # Windows requires these for subprocess to work correctly
    for key in (
        "SystemRoot",
        "PATHEXT",
        "APPDATA",
        "LOCALAPPDATA",
        "TEMP",
        "TMP",
        "HOME",
        "USERPROFILE",
        "HOMEDRIVE",
        "HOMEPATH",
    ):
        val = os.environ.get(key)
        if val is not None:
            env[key] = val
    return env


def test_import_no_env(tmp_path, monkeypatch):
    """
    Importing veo_mcp_server with no API keys must NOT call sys.exit().

    We run it in a subprocess with an empty GEMINI_API_KEY so that the
    lazy init path is exercised but the import itself should complete
    without error (exit code 0 means the import completed cleanly).
    """
    env = _base_env(tmp_path)
    env["GEMINI_API_KEY"] = ""  # no key — should NOT exit at import

    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "import veo_mcp_server; print('import ok')",
        ],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"Import failed with code {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "import ok" in result.stdout


def test_help_with_dummy_env(tmp_path):
    """
    `veo-mcp-server --help` must exit 0 with a dummy GEMINI_API_KEY.
    No actual API call is made; argparse exits before any client is built.
    """
    env = _base_env(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "veo_mcp_server", "--help"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--help exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    assert "veo-mcp-server" in result.stdout.lower() or "usage" in result.stdout.lower()


def test_version_with_dummy_env(tmp_path):
    """
    `veo-mcp-server --version` must exit 0 and print a version string.

    Skipped when the distribution metadata is unavailable (source-tree mode
    without `-e` install). In that case __version__ == "0.0.0+local" and
    the version flag still works.
    """
    try:
        from importlib.metadata import version
        pkg_version = version("veo-mcp-server")
    except Exception:
        pkg_version = "0.0.0+local"

    env = _base_env(tmp_path)

    result = subprocess.run(
        [sys.executable, "-m", "veo_mcp_server", "--version"],
        env=env,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, (
        f"--version exited {result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
    combined = result.stdout + result.stderr
    assert pkg_version in combined, (
        f"Expected version {pkg_version!r} in output: {combined!r}"
    )


def test_no_home_pollution(tmp_path, monkeypatch):
    """
    Importing veo_mcp_server must not create ~/veo-videos or any other
    home-directory side-effects.
    """
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    env = _base_env(tmp_path)
    env["HOME"] = str(fake_home)
    env["USERPROFILE"] = str(fake_home)
    env["GEMINI_API_KEY"] = ""

    subprocess.run(
        [sys.executable, "-c", "import veo_mcp_server"],
        env=env,
        capture_output=True,
        timeout=30,
    )

    veo_videos = fake_home / "veo-videos"
    assert not veo_videos.exists(), (
        f"Import created {veo_videos} — eager mkdir must not run at import time"
    )

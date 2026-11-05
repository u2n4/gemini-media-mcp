"""Cold uvx installation, MCP initialize and tools/list, with credentials absent."""

import argparse
import json
import os
from pathlib import Path
import queue
import shutil
import subprocess
import tempfile
import threading


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("server", choices=("omni", "nanobanana"))
    parser.add_argument("--python", default="3.14")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    for key in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "GEMINI_API_KEY_BACKUP"):
        env.pop(key, None)
    env["PYTHON_DOTENV_DISABLED"] = "1"
    entry = "omni-mcp-server" if args.server == "omni" else "nanobanana-imagen-mcp"
    expected = ({"omni_generate_video", "omni_image_to_video", "omni_extend_video",
                 "omni_interpolate_video", "omni_check_job", "omni_list_jobs",
                 "omni_show_output_stats", "omni_pricing_info", "omni_api_status"}
                if args.server == "omni" else
                {"generate_image", "upload_file", "maintenance", "show_output_stats"})
    uvx = shutil.which("uvx")
    if uvx is None:
        raise RuntimeError("uvx is required")
    with tempfile.TemporaryFile(mode="w+", encoding="utf-8") as stderr:
        process = subprocess.Popen(
            [uvx, "--no-cache", "--isolated", "--python", args.python, "--from", ".", entry],
            cwd=root / "servers" / args.server, env=env,
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=stderr,
            text=True, encoding="utf-8",
        )
        lines = queue.Queue()

        def read():
            for line in process.stdout:
                lines.put(line)
            lines.put(None)

        threading.Thread(target=read, daemon=True).start()

        def send(message):
            process.stdin.write(json.dumps(message) + "\n")
            process.stdin.flush()

        def receive(request_id):
            while True:
                line = lines.get(timeout=180)
                if line is None:
                    raise RuntimeError("Server closed stdout before responding")
                message = json.loads(line)
                if message.get("id") == request_id:
                    if "error" in message:
                        raise RuntimeError(str(message["error"]))
                    return message["result"]

        try:
            send({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {
                "protocolVersion": "2025-11-25", "capabilities": {},
                "clientInfo": {"name": "offline-release-smoke", "version": "1.0"},
            }})
            receive(1)
            send({"jsonrpc": "2.0", "method": "notifications/initialized"})
            send({"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}})
            actual = {tool["name"] for tool in receive(2)["tools"]}
            assert actual == expected, actual
            print(f"{args.server}: clean uvx Python {args.python}, keys absent, initialize OK, tools/list {len(actual)} OK")
        except Exception:
            stderr.seek(0)
            print(stderr.read()[-4000:])
            raise
        finally:
            process.stdin.close()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            process.stdout.close()


if __name__ == "__main__":
    main()

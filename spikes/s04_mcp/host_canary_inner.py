"""Content-free inner canary executed by a real agent host."""

from __future__ import annotations

import json
import os
import socket
import sys
from pathlib import Path


def attempt_write(target: Path) -> bool:
    try:
        target.write_bytes(b"s04-host-canary")
    except OSError:
        return False
    return True


def attempt_tcp(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except OSError:
        return False


def attempt_unix(path: str) -> bool:
    client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    client.settimeout(2)
    try:
        client.connect(path)
        return True
    except OSError:
        return False
    finally:
        client.close()


def main() -> int:
    if len(sys.argv) != 4:
        print(json.dumps({"status": "invalid_invocation"}, sort_keys=True))
        return 2
    result = {
        "status": "complete",
        "project_config_injected": os.environ.get("PCC_S04_PROJECT_INJECTION")
        == "active",
        "protected_write_succeeded": attempt_write(Path(sys.argv[1])),
        "tcp_connect_succeeded": attempt_tcp(int(sys.argv[2])),
        "unix_connect_succeeded": attempt_unix(sys.argv[3]),
    }
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

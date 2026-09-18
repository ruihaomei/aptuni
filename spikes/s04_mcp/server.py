#!/usr/bin/env python3
"""STDIO entry point for the S04 synthetic MCP server."""

import sys
import socket


def _deny_socket_creation(event: str, args: tuple[object, ...]) -> None:
    if event == "socket.__new__" and len(args) > 1 and args[1] != socket.AF_UNIX:
        raise PermissionError("S04 server network socket creation denied")
    if event in {"socket.connect", "socket.bind"}:
        raise PermissionError("S04 server socket destination denied")


sys.addaudithook(_deny_socket_creation)

from s04.server import create_server


if __name__ == "__main__":
    if sys.argv[1:] == ["--network-canary"]:
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        raise AssertionError("socket canary unexpectedly succeeded")
    create_server().run(transport="stdio")

"""
A simple health check for Docker.
"""

import socket
import sys

sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

try:
    sock.connect(("0.0.0.0", 3575))

    ping_msg = bytes('{"msg": "are you healthy?"}', 'utf-8')
    sock.sendall(ping_msg)

    sock.close()
    sys.exit(0)

except ConnectionRefusedError:
    print("[ \033[0;31mHEALTHCHECK FAILED\033[0m ]: Python listener no longer running!")
    sys.exit(1)

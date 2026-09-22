"""Container health probe for the HTTP transports.

Exits 0 when the server is healthy, or when the transport is stdio and there is
nothing to probe. Uses only the standard library, so the runtime image needs no
extra package.
"""

import os
import sys
import urllib.request

TRANSPORT = os.environ.get("MCP_TRANSPORT", "stdio").strip().lower()
HTTP_TRANSPORTS = {"streamable-http", "streamable_http", "streamablehttp", "http", "sse"}


def main() -> int:
    if TRANSPORT not in HTTP_TRANSPORTS:
        return 0  # stdio: no socket to probe

    port = os.environ.get("PORT", "8080")
    url = f"http://127.0.0.1:{port}/health"
    try:
        with urllib.request.urlopen(url, timeout=4) as response:  # noqa: S310 - fixed localhost URL
            return 0 if response.status == 200 else 1
    except Exception as exc:  # noqa: BLE001 - any failure means unhealthy
        print(f"health probe failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

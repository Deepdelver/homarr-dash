#!/usr/bin/env python3
"""
Apply the Buddy Hub inspired custom CSS theme to the live Homarr dashboard.

Homarr v1.32 stores board level custom CSS in board.custom_css (a single string).
The dashboard is NOT rendered from git by ArgoCD — the board lives in the Homarr
SQLite DB (PVC). We therefore push the theme into the running instance through the
same management API the board-as-code sync already uses (board.saveBoard), keeping
the CSS source-of-truth in git at theme/buddy-hub-theme.css.

This mirrors .github/workflows/sync.yml's apply job (same tRPC batch call).

Usage:
  python3 scripts/apply-theme.py \
      --url https://homarr.deeps-home.duckdns.org \
      --api-key "$HOMARR_API_KEY" \
      [--board boards/home.json] \
      [--css theme/buddy-hub-theme.css] \
      [--dry-run]

Auth: an admin API key (Settings -> API keys) in HOMARR_API_KEY, or passed via
--api-key. The script is idempotent: the exact committed CSS string is what lands
in custom_css every time, so re-running never drifts.
"""
import argparse
import json
import os
import sys
import urllib.request
import urllib.error

DEFAULT_BOARD = os.path.join(os.path.dirname(__file__), "..", "boards", "home.json")
DEFAULT_CSS = os.path.join(os.path.dirname(__file__), "..", "theme", "buddy-hub-theme.css")


def load_css(path):
    with open(path, "r", encoding="utf-8") as f:
        return f.read().strip()


def build_payload(board, css):
    """Reconstruct the board.saveBoard batch payload from the board snapshot.

    The tRPC board.saveBoard mutation expects the full board object (id, name,
    isPublic) plus sections, layouts and items — matching the export shape in
    boards/home.json. We only mutate custom_css; everything else is passed
    through verbatim so the call is effectively a no-op except for the theme.
    """
    b = board["board"]
    return {
        "0": {
            "json": {
                "id": b["id"],
                "name": b["name"],
                "isPublic": bool(b.get("is_public", 0)),
                "sections": [board["section"]],
                "layouts": [board["layout"]],
                "items": [
                    {
                        "id": it["id"],
                        "kind": it["kind"],
                        "options": it["options"],
                        "advancedOptions": it["advancedOptions"],
                        "integrationId": it.get("integrationId"),
                    }
                    for it in board["items"]
                ],
                # The only field we actually change:
                "custom_css": css,
            }
        }
    }


def apply(url, api_key, payload):
    url = url.rstrip("/")
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{url}/api/trpc/board.saveBoard?batch=1",
        data=data,
        headers={"Content-Type": "application/json", "x-api-key": api_key},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.status, r.read().decode("utf-8", "replace")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default=os.environ.get("HOMARR_URL", "https://homarr.deeps-home.duckdns.org"))
    ap.add_argument("--api-key", default=os.environ.get("HOMARR_API_KEY"))
    ap.add_argument("--board", default=DEFAULT_BOARD)
    ap.add_argument("--css", default=DEFAULT_CSS)
    ap.add_argument("--dry-run", action="store_true", help="Validate + print, do not call the API")
    a = ap.parse_args()

    if not a.api_key and not a.dry_run:
        print("ERROR: --api-key (or HOMARR_API_KEY) required unless --dry-run", file=sys.stderr)
        sys.exit(2)

    css = load_css(a.css)
    with open(a.board) as f:
        board = json.load(f)

    payload = build_payload(board, css)

    if a.dry_run:
        print(f"dry-run: would POST {len(json.dumps(payload))} bytes to {a.url}/api/trpc/board.saveBoard")
        print(f"css length: {len(css)} chars; custom_css will be set on board {board['board']['id']}")
        return

    try:
        status, body = apply(a.url, a.api_key, payload)
    except urllib.error.HTTPError as e:
        print(f"ERROR: HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        sys.exit(1)
    except urllib.error.URLError as e:
        print(f"ERROR: cannot reach Homarr at {a.url}: {e.reason}", file=sys.stderr)
        sys.exit(1)

    if status == 200:
        print(f"OK: theme applied to board {board['board']['id']} (custom_css = {len(css)} chars)")
    else:
        print(f"WARN: apply returned HTTP {status}: {body[:300]}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

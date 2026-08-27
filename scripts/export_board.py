#!/usr/bin/env python3
"""Export the live Homarr board + integrations from the Homarr SQLite DB into GitOps-ready JSON.

Usage:
  python3 scripts/export_board.py [--db /tmp/homarr-db.sqlite] [--out .]

The script expects a copy of the running Homarr DB (kubectl cp ...:/appdata/db/db.sqlite).
Secrets in the integrationSecret table are REDACTED (<REDACTED_BWS>) — never committed.
Regenerate after any UI board change and commit the result so boards/home.json stays current.
"""
import sqlite3, json, datetime, os, argparse

NOW = datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default="/tmp/homarr-db.sqlite")
    ap.add_argument("--out", default=".")
    a = ap.parse_args()

    c = sqlite3.connect(a.db)
    c.row_factory = sqlite3.Row

    def cols(t):
        return [r[1] for r in c.execute(f"PRAGMA table_info({t})")]

    board = dict(c.execute("select * from board").fetchone())
    board_id = board["id"]
    layout = dict(c.execute("select * from layout").fetchone())
    section = dict(c.execute("select * from section").fetchone())
    il = {r["item_id"]: dict(r) for r in c.execute("select * from item_layout")}
    bind = {r["item_id"]: r["integration_id"] for r in c.execute("select * from integration_item")}

    items = []
    for r in c.execute("select id, kind, options, advanced_options from item"):
        d = dict(r)
        pos = il.get(d["id"], {})
        items.append({
            "id": d["id"], "kind": d["kind"],
            "options": json.loads(d["options"]) if d["options"] else {},
            "advancedOptions": json.loads(d["advanced_options"]) if d["advanced_options"] else {},
            "layout": {"x": pos.get("x_offset"), "y": pos.get("y_offset"),
                       "width": pos.get("width"), "height": pos.get("height")},
            "integrationId": bind.get(d["id"]),
        })

    int_cols = cols("integration")
    secrets_rows = [dict(r) for r in c.execute("select * from integrationSecret")]
    sec_by_int = {}
    for s in secrets_rows:
        sec_by_int.setdefault(s["integration_id"], []).append(s)

    integrations = []
    for r in c.execute("select * from integration"):
        d = dict(r)
        secs = [{"kind": s["kind"], "value": "<REDACTED_BWS>", "updated_at": s["updated_at"]}
                for s in sec_by_int.get(d["id"], [])]
        integrations.append({"id": d["id"], "name": d["name"], "url": d["url"],
                              "kind": d["kind"], "secrets": secs})

    board_export = {
        "schemaVersion": "homarr-board-export-v1", "generatedAt": NOW,
        "source": "live Homarr DB (k3s ns=homarr, PVC=homarr-database) /appdata/db/db.sqlite",
        "notes": "Board content lives in the Homarr SQLite DB (PVC), not in git. This file is the "
                 "source-of-truth snapshot. Re-apply via the Homarr management API (board.saveBoard). "
                 "Secrets are never included here.",
        "board": board, "layout": layout, "section": section,
        "items": items, "integrations": integrations,
    }
    os.makedirs(f"{a.out}/boards", exist_ok=True)
    with open(f"{a.out}/boards/home.json", "w") as f:
        json.dump(board_export, f, indent=2)

    os.makedirs(f"{a.out}/integrations", exist_ok=True)
    name_map = {"avd0frupn72xwf4plopo176h": "home-assistant.json",
                "prox01w3j5k7m9n1p3r5t7v9x1z": "proxmox.json"}
    for integ in integrations:
        fname = name_map.get(integ["id"])
        if not fname:
            continue
        payload = {"schemaVersion": "homarr-integration-v1", "generatedAt": NOW,
                   "id": integ["id"], "name": integ["name"], "kind": integ["kind"],
                   "url": integ["url"], "secrets": integ["secrets"],
                   "secretSource": "BWS project 'Ai'; injected into k8s secret 'homarr'",
                   "note": "Secret VALUES redacted. Do NOT commit real values."}
        with open(f"{a.out}/integrations/{fname}", "w") as f:
            json.dump(payload, f, indent=2)
    defaults = [i for i in integrations if i["id"] not in name_map]
    with open(f"{a.out}/integrations/defaults.json", "w") as f:
        json.dump({"schemaVersion": "homarr-integration-defaults-v1", "generatedAt": NOW,
                   "note": "Built-in registry integrations (no credentials).", "integrations": defaults}, f, indent=2)
    print(f"exported {len(items)} items, {len(integrations)} integrations -> {a.out}/boards/home.json")

if __name__ == "__main__":
    main()

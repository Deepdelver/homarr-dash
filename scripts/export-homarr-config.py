#!/usr/bin/env python3
"""
Export the Homarr dashboard *configuration* (boards, sections, items, layouts,
integrations, server settings) from its SQLite DB into version-controllable
JSON files, WITHOUT leaking any secrets.

Design guarantees (fail-closed):
  - Tables holding credentials are NEVER written as-is:
      * integrationSecret -> redacted mapping (value = "[REDACTED]")
      * user, session, account, apiKey, verificationToken, invite -> excluded
      * icon (2801-row icon cache) -> excluded (re-fetched on restore)
  - After export, we assert NONE of the real secret values appear anywhere in
    the emitted JSON. If a real secret slips through, the script exits non-zero
    and writes nothing to disk.

Usage:
  export-homarr-config.py <path-to-db.sqlite> <output-dir>

The companion backup-homarr-config.sh pulls the live DB from the pod and calls
this script, then commits + pushes.
"""
import json
import os
import sqlite3
import sys

# Tables that constitute the *dashboard config* and are safe to export verbatim.
SAFE_TABLES = [
    "board", "section", "section_layout", "item", "item_layout", "layout",
    "integration", "integration_item", "serverSetting", "search_engine",
    "group", "groupMember", "groupPermission",
    "boardGroupPermission", "boardUserPermission",
    "integrationGroupPermissions", "integrationUserPermission",
    "section_collapse_state", "onboarding",
]

# Columns that are stored as JSON-encoded strings ("{\"json\": {...}}").
JSON_COLUMNS = {
    "item": {"options", "advanced_options"},
    "serverSetting": {"value"},
    "section": set(),
    "item_layout": set(),
    "layout": set(),
    "section_layout": set(),
    "board": set(),
    "integration": set(),
    "integration_item": set(),
}

# Tables containing credentials / per-instance runtime state -> never exported raw.
EXCLUDED_TABLES = [
    "integrationSecret", "user", "session", "account", "apiKey",
    "verificationToken", "invite", "icon", "media", "cron_job_configuration",
    "trusted_certificate_hostname", "app",
]


def is_json_col(table, col):
    return col in JSON_COLUMNS.get(table, set())


def coerce(value, table, col):
    if value is None:
        return None
    if is_json_col(table, col):
        # The DB stores '{"json": {...}}' wrappers; unwrap to the inner object.
        try:
            parsed = json.loads(value)
            if isinstance(parsed, dict) and "json" in parsed:
                return parsed["json"]
            return parsed
        except (json.JSONDecodeError, TypeError):
            return value
    return value


def export_table(conn, table, out_dir):
    cur = conn.execute(f'SELECT * FROM "{table}"')
    cols = [d[0] for d in cur.description]
    rows = []
    for r in cur.fetchall():
        rows.append({cols[i]: coerce(r[i], table, cols[i]) for i in range(len(cols))})
    path = os.path.join(out_dir, f"{table}.json")
    with open(path, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, sort_keys=True)
    return len(rows)


def export_redacted_secrets(conn, out_dir):
    """Export integrationSecret structure but replace every value with [REDACTED]."""
    rows = []
    try:
        cur = conn.execute('SELECT integration_id, kind, updated_at FROM "integrationSecret"')
        for integration_id, kind, updated_at in cur.fetchall():
            rows.append({
                "integration_id": integration_id,
                "kind": kind,
                "value": "[REDACTED]",
                "updated_at": updated_at,
            })
    except sqlite3.OperationalError:
        pass  # table may not exist in some schema versions
    path = os.path.join(out_dir, "redacted-secrets.json")
    with open(path, "w") as f:
        json.dump(rows, f, indent=2, ensure_ascii=False, sort_keys=True)
    return len(rows)


def collect_real_secrets(conn):
    """Return the list of real secret values that must NEVER appear in output."""
    secrets = []
    try:
        cur = conn.execute('SELECT value FROM "integrationSecret"')
        for (v,) in cur.fetchall():
            if v:
                secrets.append(v)
    except sqlite3.OperationalError:
        pass
    # Also flag any password/salt from user table.
    try:
        cur = conn.execute('SELECT password, salt FROM "user"')
        for pw, salt in cur.fetchall():
            if pw:
                secrets.append(pw)
            if salt:
                secrets.append(salt)
    except sqlite3.OperationalError:
        pass
    return [s for s in secrets if s]


def main():
    if len(sys.argv) != 3:
        print("Usage: export-homarr-config.py <db.sqlite> <output-dir>", file=sys.stderr)
        sys.exit(2)
    db_path, out_dir = sys.argv[1], sys.argv[2]
    if not os.path.isfile(db_path):
        print(f"ERROR: db not found: {db_path}", file=sys.stderr)
        sys.exit(1)
    os.makedirs(out_dir, exist_ok=True)

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    # Real secrets must be captured BEFORE we write anything.
    real_secrets = collect_real_secrets(conn)

    manifest = {}
    for t in SAFE_TABLES:
        try:
            n = export_table(conn, t, out_dir)
            if n:
                manifest[t] = n
        except sqlite3.OperationalError:
            pass  # table absent in this schema version
    nsec = export_redacted_secrets(conn, out_dir)

    conn.close()

    # FAIL-CLOSED secret scan across every file we just wrote.
    if real_secrets:
        blob = ""
        for fn in os.listdir(out_dir):
            if fn.endswith(".json"):
                with open(os.path.join(out_dir, fn)) as f:
                    blob += f.read()
        leaked = [s[:12] + "..." for s in real_secrets if s in blob]
        if leaked:
            # Wipe output so we never ship a leak.
            for fn in os.listdir(out_dir):
                if fn.endswith(".json"):
                    os.remove(os.path.join(out_dir, fn))
            print(f"FATAL: {len(leaked)} real secret(s) leaked into export. "
                  f"Output wiped. Leak heads: {leaked}", file=sys.stderr)
            sys.exit(3)

    with open(os.path.join(out_dir, "MANIFEST.json"), "w") as f:
        json.dump({
            "generated_by": "scripts/export-homarr-config.py",
            "tables_exported": manifest,
            "redacted_secret_entries": nsec,
            "note": "integrationSecret values are [REDACTED]; re-enter in UI after restore.",
        }, f, indent=2, sort_keys=True)

    print(f"OK: exported {len(manifest)} tables, {nsec} redacted secret entries -> {out_dir}")


if __name__ == "__main__":
    main()

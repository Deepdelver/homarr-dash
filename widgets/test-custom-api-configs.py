#!/usr/bin/env python3
"""
Test & validate Homarr custom-api widget configs.

For every *.json file in the sibling `custom-api-configs/` directory:
  1. validates the required schema keys
  2. performs the configured HTTP request (GET by default)
  3. parses the JSON response
  4. evaluates each JSONPath in `jsonPath` against the response
  5. substitutes the extracted values into the `display` string
  6. reports PASS/FAIL per config

Pure stdlib — no third-party dependencies (works on a bare Python 3.8+).

Usage:
    python3 test-custom-api-configs.py
    python3 test-custom-api-configs.py --dir /path/to/configs
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from typing import Any, Dict, List, Tuple

REQUIRED_KEYS = ("name", "url", "method", "headers", "jsonPath", "display")


# --------------------------------------------------------------------------- #
# Minimal JSONPath evaluator
# Supports:  $.a.b.c            dotted object traversal
#            $.a[*].b           wildcard over array elements
#            $.a[0].b           numeric index
# Returns a list of all matched values (may be empty if no match).
# --------------------------------------------------------------------------- #
def parse_path(expr: str) -> List[Any]:
    expr = expr.strip()
    if expr.startswith("$"):
        expr = expr[1:]
    expr = expr.lstrip(".")
    steps: List[Any] = []
    i = 0
    n = len(expr)
    while i < n:
        c = expr[i]
        if c == ".":
            i += 1
            j = i
            while j < n and expr[j] not in ".[":
                j += 1
            key = expr[i:j]
            if key:
                steps.append(key)
            i = j
        elif c == "[":
            j = expr.index("]", i)
            inner = expr[i + 1:j].strip()
            steps.append("*" if inner == "*" else int(inner))
            i = j + 1
        else:
            j = i
            while j < n and expr[j] not in ".[":
                j += 1
            key = expr[i:j]
            if key:
                steps.append(key)
            i = j
    return steps


def _walk(obj: Any, steps: List[Any]) -> List[Any]:
    if not steps:
        return [obj]
    step = steps[0]
    rest = steps[1:]
    out: List[Any] = []
    if step == "*":
        if isinstance(obj, list):
            for item in obj:
                out.extend(_walk(item, rest))
        elif isinstance(obj, dict):
            for item in obj.values():
                out.extend(_walk(item, rest))
    elif isinstance(step, int):
        if isinstance(obj, list) and -len(obj) <= step < len(obj):
            out.extend(_walk(obj[step], rest))
    else:  # string key
        if isinstance(obj, dict) and step in obj:
            out.extend(_walk(obj[step], rest))
    return out


def jsonpath(obj: Any, expr: str) -> List[Any]:
    return _walk(obj, parse_path(expr))


# --------------------------------------------------------------------------- #
# HTTP fetch
# --------------------------------------------------------------------------- #
def fetch(url: str, method: str, headers: Dict[str, str], timeout: int = 20) -> Tuple[int, str]:
    req = urllib.request.Request(url, method=method.upper())
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.getcode(), resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 - surface as a clear error
        return -1, f"ERROR: {type(e).__name__}: {e}"


# --------------------------------------------------------------------------- #
# Display substitution
# --------------------------------------------------------------------------- #
def format_value(values: List[Any]) -> str:
    if not values:
        return "MISSING"
    flat = [v for v in values if v is not None]
    if not flat:
        return "null"
    if len(flat) == 1:
        return str(flat[0])
    return ", ".join(str(v) for v in flat)


def render(display: str, fields: Dict[str, List[Any]]) -> str:
    out = display
    for name, vals in fields.items():
        out = out.replace("{" + name + "}", format_value(vals))
    return out


# --------------------------------------------------------------------------- #
# Per-config test
# --------------------------------------------------------------------------- #
def test_config(path: str) -> bool:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except Exception as e:  # noqa: BLE001
        print(f"  [FAIL] {os.path.basename(path)}: invalid JSON ({e})")
        return False

    missing = [k for k in REQUIRED_KEYS if k not in cfg]
    if missing:
        print(f"  [FAIL] {cfg.get('name', os.path.basename(path))}: missing keys {missing}")
        return False

    name = cfg["name"]
    code, body = fetch(cfg["url"], cfg["method"], cfg.get("headers", {}))
    if code < 0:
        print(f"  [FAIL] {name}: request failed ({body})")
        return False
    if code >= 400:
        print(f"  [FAIL] {name}: HTTP {code}")
        return False

    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        print(f"  [FAIL] {name}: response is not JSON ({e})")
        return False

    fields: Dict[str, List[Any]] = {}
    all_ok = True
    for field, expr in cfg["jsonPath"].items():
        vals = jsonpath(data, expr)
        fields[field] = vals
        if not vals:
            all_ok = False
            print(f"        - jsonPath '{expr}' -> NO MATCH")

    rendered = render(cfg["display"], fields)
    status = "PASS" if all_ok else "FAIL"
    print(f"  [{status}] {name}: HTTP {code}")
    print(f"          {rendered}")
    return all_ok


# --------------------------------------------------------------------------- #
def main() -> int:
    here = os.path.dirname(os.path.abspath(__file__))
    default_dir = os.path.join(here, "custom-api-configs")
    ap = argparse.ArgumentParser(description="Validate Homarr custom-api widget configs")
    ap.add_argument("--dir", default=default_dir, help="directory of widget JSON configs")
    args = ap.parse_args()

    if not os.path.isdir(args.dir):
        print(f"Config directory not found: {args.dir}")
        return 2

    configs = sorted(
        os.path.join(args.dir, f)
        for f in os.listdir(args.dir)
        if f.endswith(".json")
    )
    if not configs:
        print(f"No JSON configs found in {args.dir}")
        return 2

    print(f"Testing {len(configs)} custom-api widget config(s) from {args.dir}\n")
    results = [test_config(p) for p in configs]
    passed = sum(results)
    total = len(results)
    print(f"\nSummary: {passed}/{total} config(s) passed")
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

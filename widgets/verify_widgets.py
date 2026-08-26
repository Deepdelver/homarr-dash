#!/usr/bin/env python3
"""Ad-hoc verification for homarr custom-api widget configs + layout."""
import json, sys, urllib.request, ssl

CFG = "/home/frank/homarr-dash/widgets/custom-api-configs.json"
LAY = "/home/frank/homarr-dash/widgets/dashboard-layout.json"

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

fail = []
warn = []

try:
    a = json.load(open(CFG))
    b = json.load(open(LAY))
except Exception as e:
    print("FATAL: json parse:", e); sys.exit(1)

widgets = a.get("widgets", [])
print(f"[1] configs: {len(widgets)} widgets, layout: {len(b.get('sections',[]))} sections")

req = ["name","url","authType","method","displayType","refreshSeconds","iconUrl"]
for w in widgets:
    for k in req:
        if k not in w: fail.append(f"{w.get('name','?')} missing {k}")
    if w["url"].startswith("https://") is False: fail.append(f"{w['name']} url not https")
    if not w.get("iconUrl"): fail.append(f"{w['name']} no iconUrl")
    dc = w.get("displayConfig",{})
    if dc.get("type") != w["displayType"]:
        fail.append(f"{w['name']} displayType {w['displayType']} != displayConfig.type {dc.get('type')}")

names = [w["name"] for w in widgets]
if len(names) != len(set(names)): fail.append("duplicate widget names")

cfg_names = set(names)
layout_custom = {w["name"] for s in b["sections"] for w in s["widgets"] if w.get("type")!="app"}
miss = layout_custom - cfg_names
if miss: fail.append(f"layout custom-api names missing from configs: {miss}")

for s in b["sections"]:
    for wt in s["widgets"]:
        for c in ("x","y","w","h"):
            if c not in wt: fail.append(f"tile {wt.get('name','?')} in {s['id']} missing {c}")

print("[2] live re-probe of every widget url:")
for w in widgets:
    try:
        reqt = urllib.request.Request(w["url"], method="GET", headers={"User-Agent":"homarr-verify"})
        with urllib.request.urlopen(reqt, timeout=12, context=ctx) as r:
            ct = r.headers.get("Content-Type","")
            body = r.read(200).decode("utf-8","replace")
            is_json = ct.startswith("application/json") or body.lstrip().startswith("{")
            if r.status != 200:
                fail.append(f"{w['name']} HTTP {r.status}")
            elif not is_json:
                warn.append(f"{w['name']} returned non-JSON ({ct}) - may need displayConfig tweak")
            else:
                print(f"    OK  {r.status} {ct.split(';')[0]:<16} {w['name']}")
    except Exception as e:
        fail.append(f"{w['name']} probe error: {e}")

print()
if warn:
    print("WARNINGS (non-blocking):")
    for x in warn: print("  -", x)
if fail:
    print("FAILURES:")
    for x in fail: print("  -", x)
    sys.exit(1)
print("VERIFY OK: structure + live endpoints all green (ad-hoc).")

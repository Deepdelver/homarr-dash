# Homarr Dashboard — deeps-home.duckdns.org

Homarr dashboard deployed via ArgoCD to k3s. Accessible at https://homarr.deeps-home.duckdns.org/

## Native Homarr Integrations (available out-of-the-box)

These services have built-in Homarr widgets — just add them in the Homarr UI:

| Service | Integration | Widgets | URL |
|---------|------------|---------|-----|
| **Plex** | `plex` | Now playing, streams, library stats | `https://movies.deepdelver.duckdns.org` |
| **Home Assistant** | `homeassistant` | Entity state, execute automation | `https://deepdelver.duckdns.org:8123` |
| **Proxmox** | `proxmox` | Node status, VM/CT list, CPU/RAM | `https://<proxmox-ip>:8006` |
| **Uptime Kuma** | `uptime-kuma` | Uptime %, incident history | (deploy separately) |
| **Traefik** | `traefik` | Route status, middleware, services | (internal k3s) |
| **Pi-hole** | `pi-hole` | DNS queries, blocking stats | (if deployed) |
| **AdGuard Home** | `adguard-home` | DNS filtering stats | (if deployed) |
| **Jellyfin** | `jellyfin` | Now playing, library | (alternative to Plex) |
| **Overseerr** | `overseerr` | Media requests | (if deployed) |
| **Bazarr** | `bazarr` | Subtitle management | (if deployed) |
| **Prowlarr** | `prowlarr` | Indexer management | (if deployed) |
| **Immich** | `immich` | Photo library | (if deployed) |
| **Nextcloud** | `nextcloud` | File sync status | (if deployed) |
| **ntfy** | `ntfy` | Push notifications | (if deployed) |
| **Gotify** | `gotify` | Push notifications | (if deployed) |
| **iCal** | `ical` | Calendar aggregation | any .ics URL |
| **Clock** | `clock` | Time/date widget | built-in |
| **Bookmarks** | `bookmarks` | Custom link tiles | built-in |
| **Speedtest Tracker** | `speedtest-tracker` | Bandwidth history | (if deployed) |

## Custom API Widgets (no native integration)

For services without native Homarr support, use the `custom-api` widget. The
definitive, verified list lives in `widgets/custom-api-configs.json` (Homarr v2
schema) + the per-service legacy files in `widgets/custom-api-configs/`. Every
endpoint below was probed live (HTTP 200 + JSON) on 2026-08-27 and is covered by
`python3 widgets/test-custom-api-configs.py` (9/9 PASS).

| Service | Widget | Endpoint (public, no auth unless noted) |
|---------|--------|----------------------------------------|
| **9router** (LiteLLM router) | statusIndicator | `https://9router.deeps-home.duckdns.org/api/health` |
| **OpenClaw** | statusIndicator | `https://openclaw.deeps-home.duckdns.org/health` |
| **n8n** | statusIndicator | `https://n8n.deeps-home.duckdns.org/healthz` |
| **Buddy Hub** | keyValue + progressBars | `https://buddy.deeps-home.duckdns.org/api/health` & `/api/ataglance` |
| **SearXNG** | keyValue | `https://searxng.deeps-home.duckdns.org/config` |
| **Grafana** | keyValue + singleValue | `https://grafana.deeps-home.duckdns.org/api/health` & `/api/search` |
| **Prometheus** | singleValue + keyValue | `https://prometheus.deeps-home.duckdns.org/api/v1/alerts` & `/api/v1/targets` |
| **Qdrant** | keyValue + table | `https://qdrant.deeps-home.duckdns.org/collections` & `/collections/memories` |
| **Hermes** (buddy manager) | keyValue + progressBars | `https://buddy.deeps-home.duckdns.org/api/acp/overview` & `/api/ataglance` |
| **LiteLLM** | statusIndicator | `https://litellm.deeps-home.duckdns.org/health/readiness` (public; `/health` & `/v1/models` need the master key) |
| **Cinephile** | keyValue | `https://cinephile.deeps-home.duckdns.org/health` |
| **DJ Portaal** | keyValue | `https://dj-portaal.deeps-home.duckdns.org/api/health` |

### Native integrations (NOT custom widgets — use the built-in ones)

**Plex** (`https://movies.deepdelver.duckdns.org`, token in BWS `PLEX_TOKEN`) and
**Home Assistant** (`https://deepdelver.duckdns.org:8123`, token in BWS
`HA_LONG_LIVED_TOKEN`) both have first-class Homarr integrations — add them via
Settings → Integrations, then use the native Plex "Media server streams" and HA
"Entity State" widgets. They are intentionally **excluded** from the custom-api
configs above (the brief listed them as "if not using native integration" — here
we DO use the native integration, which is the better fit).

## Docker Container Widget

Homarr can show Docker containers via the Docker integration. In k3s, this requires either:
1. **Docker socket mount** (not recommended for k3s — use containerd)
2. **DOCKER_HOSTNAMES** env var pointing to a Docker-compatible API endpoint

For k3s/containerd: the Docker widget is **not applicable**. Use the `app` widget instead to link to individual services.

## Deployment

### Prerequisites
1. Generate encryption key:
   ```bash
   openssl rand -hex 32
   ```
2. Create the secret:
   ```bash
   kubectl create secret generic homarr -n homarr \
     --from-literal=ENCRYPTION_KEY=<generated-key>
   ```

### ArgoCD Sync
```bash
kubectl -n argocd annotate application homarr argocd.argoproj.io/refresh=hard --overwrite
```

### First-Time Setup
1. Navigate to https://homarr.deeps-home.duckdns.org/
2. Create admin account (first user = admin)
3. Add integrations via UI: Settings → Integrations → Add
4. Add widgets to board: Edit → Add Widget → Choose type

## Widget Layout (actual, built 2026-08-27)

The live board `Home` (id `og15c9dzzqhkfppy2ne9mhoc`) has **17 widgets** on a 6-column
grid. Coordinates below are `(x, y, w, h)` in Homarr grid units (row `y`, col `x`).

```
Row 0  (0,0) Clock        (1,0) Weather       (2,0,2,2) Quick Links   (4,0) TV Light      (5,0) Kitchen Temp
Row 1                                      (4,1) HA Automation   (5,1) Hall Light
Row 2  (0,2,3,1) Proxmox Cluster  (3,2) OpenClaw  (4,2) 9router  (5,2) Hermes
Row 3  (0,3) Qdrant  (1,3) Buddy Hub  (2,3) Cluster Metrics  (4,3) Release feed  (5,3) Calendar
Row 4  (0,4,3,1) Notes
```

| # | Widget | Type | Bound integration | Notes |
|---|--------|------|-------------------|-------|
| 1 | Clock | `clock` | — | |
| 2 | Weather (Utrecht) | `weather` | — | °C, 3-day forecast |
| 3 | Quick Links | `notebook` | — | markdown links to fleet services |
| 4 | TV Light | `smartHome-entityState` | Home Assistant | `light.light_tv` |
| 5 | Kitchen Temp | `smartHome-entityState` | Home Assistant | `sensor.air_keuken_temperature` |
| 6 | HA Automation | `smartHome-executeAutomation` | Home Assistant | `automation.dim_lights_based_on_sun_elevation` |
| 7 | Hall Light | `smartHome-entityState` | Home Assistant | `light.light_gang` |
| 8 | Proxmox Cluster | `healthMonitoring` | Proxmox | cpu/mem/uptime/fs |
| 9 | OpenClaw | `iframe` | — | `https://openclaw.deeps-home.duckdns.org/health` (HTTPS) |
| 10 | 9router | `iframe` | — | `https://9router.deeps-home.duckdns.org/api/health` (HTTPS) |
| 11 | Hermes | `iframe` | — | `https://manager.deeps-home.duckdns.org/api/ataglance` (HTTPS) |
| 12 | Qdrant | `iframe` | — | `https://qdrant.deeps-home.duckdns.org/dashboard` (HTTPS) |
| 13 | Buddy Hub | `iframe` | — | `https://buddy.deeps-home.duckdns.org/api/health` (HTTPS) |
| 14 | Cluster Metrics | `iframe` | — | `https://manager.deeps-home.duckdns.org/api/ataglance` (HTTPS) |
| 15 | Release feed | `releases` | — | empty by design (no download-client integration) |
| 16 | Calendar | `calendar` | — | |
| 17 | Notes | `notebook` | — | build manifest |

The authoritative machine-readable copy of this layout lives in `boards/home.json`
(exported from the live Homarr SQLite DB). All 6 iframe widgets use HTTPS — no
mixed-content. The Proxmox `healthMonitoring` widget shows "Failed to fetch" only
when the upstream Proxmox node is down (known, accepted).

## Board-as-Code (GitOps for board content)

Homarr v1.32 stores board config in its SQLite DB on the `homarr-database` PVC — it is
**NOT** rendered from git by ArgoCD. To make the board reproducible and reviewable:

- `boards/home.json` — source-of-truth snapshot of the live board (items, layouts,
  integrations, bindings). Regenerate with `python3 scripts/export_board.py`.
- `integrations/*.json` — integration definitions with **secrets redacted**
  (`<REDACTED_BWS>`). Real values live in BWS project `Ai`; they are injected into the
  k8s `homarr` secret at deploy time, never committed.
- `.github/workflows/sync.yml` — on push to `boards/home.json`, optionally re-applies
  the board to the live Homarr instance via the management API
  (`board.saveBoard`, the same call the ops build used). Disabled by default
  (`ENABLE_BOARD_APPLY=false`) to avoid clobbering in-cluster edits; flip it on in the
  repo/Environment secret to enforce GitOps on the board itself.

> Regenerate after any UI change: `python3 scripts/export_board.py` then commit.


## Storage
- PVC `homarr-database` (1Gi, local-path): SQLite database, encryption key, board config
- `emptyDir` logs: Application logs (ephemeral)

## Security
- TLS via cert-manager (Let's Encrypt)
- Traefik ingress with existing `deeps-home-tls` cert
- Homarr built-in auth (first user = admin, subsequent users by invite)
- No `hostPath` mounts, no privileged containers

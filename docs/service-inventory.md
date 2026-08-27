# Service Inventory — Homarr integration

Researched 2026-08-27 by the Researcher agent. URLs, reachability, API auth and
BWS key presence were verified live via curl probes against Traefik/k3s ingress
(current node 192.168.1.198/210) and the `deepdelver.duckdns.org` HA/Plex host.
LAN = private `192.168.x.x` address; WAN = public `*.deeps-home.duckdns.org`
(Traefik ingress) or `deepdelver.duckdns.org` (separate NPM host for HA/Plex).

> NOTE: two corrections vs prior `README.md` — (1) `movies.deepdelver.duckdns.org`
> serves **Cinephile**, NOT Plex; (2) Plex has **no** public WAN URL in this
> environment (it is only reachable on its LAN host 192.168.1.250:32400, which is
> firewalled from the dashboard node). Plan Plex integration as LAN-only.

## Legend
- **Homarr Native?** = first-class Homarr v1 integration exists (`✓`) vs must be
  done with a `custom-api` widget or an `app`/bookmark tile (`~` / `✗`).
- **Key Source** = BWS secret name already stored in project `fb098e5c-…` (Ai),
  or "—" if no credential is needed / none found.
- Probing done from this k3s node. `HTTP 200` = reachable + responding;
  `404` on a subdomain = that subdomain is not a configured proxy host.

## Inventory

| Service | LAN URL | WAN URL | API Type | Auth Method | Key Source (BWS) | Homarr Native? |
|---|---|---|---|---|---|---|
| **Plex** | `http://192.168.1.250:32400` (LAN-firewalled from dash node) | *none* (no `plex.deeps-home` proxy) | REST (XML/JSON) | Plex Token (header `X-Plex-Token`) | `PLEX_TOKEN` | ✓ (native `plex`) — LAN-only |
| **Home Assistant** | `https://192.168.1.251:8123` | `https://deepdelver.duckdns.org:8123` (HTTP 200) | REST + WebSocket | Long-Lived Access Token (`Authorization: Bearer`) | `HA_LONG_LIVED_TOKEN`, `HASS_TOKEN`, `HA_PROFILE_HA_PASS` | ✓ (native `homeassistant`) |
| **Proxmox** | `https://192.168.1.253:8006` (HTTP 301) | *none* | REST (Proxmox VE API) | Ticket + CSRF token (`PVEAuthCookie`) | `SUDO_PASSWORD` (host), no PVE API token in BWS | ✓ (native `proxmox`) — LAN-only |
| **Immich** | LAN host not enumerated (docker-stack node) | *none* (`immich.deeps-home` 404) | REST + OpenAPI | API Key (user-scoped, `x-api-key`) | *no Immich key in BWS* | ✓ (native `immich`) — no WAN |
| **Nextcloud** | LAN host not enumerated (docker-stack node) | *none* (`nextcloud.deeps-home` 404) | REST (OCS/WebDAV) | App password / Bearer token | *no Nextcloud key in BWS* | ✓ (native `nextcloud`) — no WAN |
| **Pi-hole** | LAN host not enumerated (docker-stack node) | *none* (`pihole.deeps-home` 404) | REST (FTL API) | App password (`PIHOLE_TOKEN`) / web password | *no Pi-hole key in BWS* | ✓ (native `pi-hole`) — no WAN |
| **ntfy** | LAN host not enumerated (docker-stack node) | *none* (`ntfy.deeps-home` 404) | REST (pub/sub) | Optional token / Bearer | *no ntfy key in BWS* | ✓ (native `ntfy`) — no WAN |
| **Uptime Kuma** | LAN host not enumerated (docker-stack node) | *none* (`uptimekuma.deeps-home` 404) | REST (socket.io) | Username + password (no API key) | *no Uptime Kuma key in BWS* | ✓ (native `uptime-kuma`) — no WAN |
| **Grafana** | LAN host not enumerated (docker-stack node) | `https://grafana.deeps-home.duckdns.org` (HTTP 200 `/api/health`) | REST | Service Account Token (Bearer) | `ADMIN_API_KEY`, `WEBUI_SECRET_KEY` (related) | ~ (use `custom-api` widget — see README) |
| **SearXNG** | — | `https://searxng.deeps-home.duckdns.org` (HTTP 200 `/config`) | REST (OpenSearch + JSON) | None (public) | `SEARXNG_SECRET` | ~ (use `custom-api` widget) |
| **OpenClaw** | — | `https://openclaw.deeps-home.duckdns.org` (HTTP 200 `/health`) | REST | Bearer token (`OPENCLAW_GATEWAY_PASSWORD` / bot token) | `OPENCLAW_GATEWAY_PASSWORD`, `OPENCLAW_TELEGRAM_BOT_TOKEN`, `OPENCLAW_BWS_TOKEN` | ~ (use `custom-api` widget) |
| **9router** (LiteLLM router) | — | `https://9router.deeps-home.duckdns.org` (HTTP 307 → `/`) | REST (OpenAI-compatible) | API key (`Authorization: Bearer sk-…`) | `9ROUTER_*_APIKEY`, `NINE_ROUTER_API_KEY`, `9ROUTER_ADMIN_PASSWORD` | ~ (use `custom-api` widget) |
| **Hermes** (manager/buddy) | — | `https://manager.deeps-home.duckdns.org` (HTTP 200 `/api/ataglance`) | REST | n/a (public health) | `HOMARR_ADMIN_PASSWORD` (unrelated), `GATEWAY_PASSWORD` | ~ (use `custom-api` widget) |
| **Qdrant** | `http://192.168.1.198:30633` (NodePort) | `https://qdrant.deeps-home.duckdns.org` (HTTP 200 `/collections`) | REST | API key (`x-api-key` / `Authorization`) | *no Qdrant key in BWS* (unauthenticated) | ~ (use `custom-api` widget) |
| **n8n** | — | `https://n8n.deeps-home.duckdns.org` (HTTP 200 `/healthz`) | REST | API key (Bearer) / session cookie | *no n8n key in BWS* | ~ (use `custom-api` widget) |
| **Docmost** | — | `https://docmost.deeps-home.duckdns.org` (HTTP 200) | REST/GraphQL | Bearer token (workspace API key) | *no Docmost key in BWS* | ✗ (bookmark tile) |
| **Firecrawl** | — | `https://firecrawl.deeps-home.duckdns.org` (HTTP 200; `/v1/scrape` 400, `/v0/scrape` 400 = API present, bad payload) | REST | API key (`Authorization: Bearer fc-…`) | *no Firecrawl key in BWS* | ✗ (bookmark tile) |
| **Buddy Hub** | — | `https://buddy.deeps-home.duckdns.org` (HTTP 200 `/api/health`, `/api/ataglance`) | REST | n/a (public) | `GITHUB_PAT_BUDDY_STACK` | ~ (use `custom-api` widget) |
| **Cinephile** | LAN host not enumerated | `https://cinephile.deeps-home.duckdns.org` (HTTP 200 `/health`) + `https://movies.deepdelver.duckdns.org` (HTTP 200, Cinephile UI) | REST | n/a (public health) | `TMDB_API_KEY`, `TRAKT_*` | ~ (use `custom-api` widget) |
| **Homarr** (self) | k3s pod | `https://homarr.deeps-home.duckdns.org` (HTTP 200) | REST | Built-in admin auth | `HOMARR_ADMIN_PASSWORD` (BWS) | self |

## Key findings / gaps
- **Public (WAN) reachable via Traefik:** homarr, grafana, searxng, openclaw,
  9router, hermes/manager, qdrant, n8n, docmost, firecrawl, buddy, cinephile,
  litellm (hidden), dj-portaal (hidden). All return HTTP 200 on health.
- **Public via deepdelver NPM host:** Home Assistant (`deepdelver.duckdns.org:8123`)
  and Cinephile (`movies.deepdelver.duckdns.org`). Plex is listed there but the
  subdomain returns 404 — Plex is LAN-only (192.168.1.250:32400).
- **No public URL (LAN-only, behind docker-stack node not reached from dash node):**
  Immich, Nextcloud, Pi-hole, ntfy, Uptime Kuma, Proxmox. These have native Homarr
  integrations but Homarr (running in k3s) cannot reach their LAN IPs unless the
  docker-stack host is on a routable subnet — verify cross-host routing before
  adding them.
- **BWS credentials present** for: Plex (`PLEX_TOKEN`), HA (`HA_LONG_LIVED_TOKEN`,
  `HASS_TOKEN`, `HA_PROFILE_HA_PASS`), Proxmox host (`SUDO_PASSWORD`, not a PVE API
  token), OpenClaw (`OPENCLAW_GATEWAY_PASSWORD` etc.), 9router (`9ROUTER_*_APIKEY`),
  SearXNG (`SEARXNG_SECRET`), Cinephile (`TMDB_API_KEY`, `TRAKT_*`), plus LLM keys
  (OpenAI/Anthropic/Groq/Gemini/DeepSeek/XAI/Ollama/Nous) under their own names.
- **BWS credentials MISSING** for: Immich, Nextcloud, Pi-hole, ntfy, Uptime Kuma,
  Grafana SA token, Qdrant API key, n8n API key, Docmost API key, Firecrawl API
  key. These must be generated in each service's UI and stored in BWS before
  Homarr can authenticate (except where the endpoint is public/unauthenticated).
- **Verified custom-api endpoints** (HTTP 200 + JSON) are catalogued in
  `../README.md` and `widgets/custom-api-configs/` (9/9 tested). Reuse those
  rather than re-deriving.

## Recommended Homarr wiring
1. **Native integrations** (add in UI → Settings → Integrations): Plex (LAN),
   Home Assistant, Proxmox (LAN), Immich, Nextcloud, Pi-hole, ntfy, Uptime Kuma —
   once the docker-stack host is routable from k3s.
2. **custom-api widgets**: 9router, OpenClaw, n8n, Buddy Hub, SearXNG, Grafana,
   Qdrant, Cinephile, Hermes — configs already exist in `widgets/`.
3. **Bookmark tiles**: Docmost, Firecrawl (no meaningful status API for a widget).

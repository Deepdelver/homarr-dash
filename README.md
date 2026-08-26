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

For services without native Homarr support, use the `custom-api` widget:

| Service | Approach | Endpoint |
|---------|----------|----------|
| **Grafana** | `iframe` widget or `custom-api` | `https://grafana.deeps-home.duckdns.org` |
| **9router** | `custom-api` widget | `http://9router.9router.svc:20128/api/health` |
| **OpenClaw** | `custom-api` widget | `http://openclaw.openclaw.svc:18789/health` |
| **Qdrant** | `custom-api` widget | `http://qdrant.qdrant.svc:6333/healthz` |
| **Hermes** | `app` widget (link) | `https://manager.deeps-home.duckdns.org` |
| **Buddy Hub** | `app` widget (link) | `https://buddy.deeps-home.duckdns.org` |
| **SearXNG** | `custom-api` widget | `http://searxng.searxng.svc:8080/healthz` |
| **Prometheus** | `custom-api` widget | `http://prometheus.prometheus.svc:9090/-/healthy` |
| **Cinephile** | `app` widget (link) | `https://movies.deepdelver.duckdns.org` |

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

## Widget Layout (planned)

```
┌─────────────────────────────────────────────────────────────┐
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Clock       │  │ Weather     │  │ System Stats        │  │
│  │             │  │ (ical)      │  │ (Proxmox via custom) │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────┐│
│  │ Service Status (app widgets)                             ││
│  │  Plex | HA | Grafana | Buddy Hub | OpenClaw | 9router   ││
│  └──────────────────────────────────────────────────────────┘│
│  ┌──────────────────┐  ┌──────────────────┐  ┌────────────┐ │
│  │ Plex Now Playing │  │ HA Entity State  │  │ Bookmarks  │ │
│  └──────────────────┘  └──────────────────┘  └────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

## Storage
- PVC `homarr-database` (1Gi, local-path): SQLite database, encryption key, board config
- `emptyDir` logs: Application logs (ephemeral)

## Security
- TLS via cert-manager (Let's Encrypt)
- Traefik ingress with existing `deeps-home-tls` cert
- Homarr built-in auth (first user = admin, subsequent users by invite)
- No `hostPath` mounts, no privileged containers

# Homarr Integration & Layout Guide

Researched and compiled for the Homarr dashboard at `https://homarr.deeps-home.duckdns.org`
(Homarr v1, deployed on k3s via ArgoCD — repo `Deepdelver/homarr-dash`).

> All integration steps are performed inside the Homarr UI (no YAML). Homarr v1 is
> configured 100% through the web interface (Integrations → Management, then add
> widgets to a board). The deprecated YAML/config-file approach does not apply here.

---

## 1. Credential sources (Bitwarden Secrets Manager)

The tokens below are stored in the `Ai` BWS project on this host. Never paste
them into git, chat, or logs. In a session with `BWS_ACCESS_TOKEN` set, resolve
them by ID and pass the value into the Homarr UI only:

| Secret (BWS) | ID | Used for |
| --- | --- | --- |
| `HA_LONG_LIVED_TOKEN` | `807e1701-9f6d-40b1-81d1-b499009ea054` | Home Assistant API key |
| `PLEX_TOKEN` | `2b20a769-2522-4649-a484-b4980124808f` | Plex API key |

Resolve example (no value printed):
```bash
BWS_ID=807e1701-9f6d-40b1-81d1-b499009ea054
bws secret get "$BWS_ID" | python3 -c "import sys,json;print(json.load(sys.stdin)['value'])"
```
Proxmox has **no** stored secret yet — you create a dedicated API token during setup (§3).

---

## 2. Home Assistant integration

**Widgets available:** Entity State (show + optionally toggle an entity), Execute Automation (one-click trigger).

**Setup (in Home Assistant, then in Homarr):**
1. Open HA → click your **profile** (bottom-left) → **Security** tab.
2. Scroll to **Long-lived access tokens** → **Create Token**.
3. Name it (e.g. `Homarr Integration`), click Create, **copy the token once**.
   (Long-lived tokens are valid ~10 years.)
4. In Homarr: **Integrations → Add → Home Assistant**.
   - URL: `https://deepdelver.duckdns.org:8123` (or `http://192.168.1.251:8123` for LAN)
   - API Key: the long-lived token from step 3.
5. Add widgets:
   - **Entity State** widget — pick entities to surface. Recommended to expose:
     a few key lights/switches, a climate entity, `sensor`/`binary_sensor`
     summaries, and any sensor you already watch in HA (e.g. power, temperature).
     You do NOT need to expose everything — only the entities you want on the
     dashboard. Use the widget's entity picker to add them one by one.
   - **Execute Automation** widget — bind to a useful one-tap automation
     (e.g. "Goodnight", "Movie mode").

**Caveats:** HA must be reachable from the Homarr pod. The LAN URL
`192.168.1.251:8123` works if the k3s cluster can route to that host (it can on
this LAN). Use the public HTTPS URL if you prefer egress via the ingress.

---

## 3. Proxmox VE integration (at `192.168.1.253:8006`)

**Widget available:** System Health Monitoring (node health/status).

**IMPORTANT — PAM vs PVE auth:** Homarr's docs explicitly warn the Proxmox API
may **not** work with the Linux PAM standard authentication (`root@pam`). Use the
**Proxmox VE authentication server** realm (`realm = pve`) for the API user.

**Step A — create a dedicated Proxmox user + group (least privilege):**
1. Proxmox web UI → **Datacenter → Permissions → Groups → Add**.
   - Name: `api-users` (or similar).
2. **Permissions (folder) → Add → Group Permission**:
   - Path: `/`
   - Group: `api-users`
   - Role: **PVEAuditor**
   - Propagate: ✔ checked
3. **Permissions → Users → Add**:
   - User: `homarr` (or similar)
   - Realm: **Proxmox VE authentication server** (i.e. `pve`, NOT Linux PAM)
   - Password: secure random
   - Group: `api-users`

**Step B — create the API token:**
1. **Permissions → API Tokens → Add**:
   - User: `homarr@pve`
   - Token ID: `homarr` (so the full token ID is `homarr@pve!homarr`)
   - Privilege Separation: **unchecked** (so the token inherits the user's
     `PVEAuditor` permissions)
   - **Copy the Secret shown — it is displayed only once.**
2. **Permissions → Add → API Token Permission**:
   - Path: `/`
   - API Token: select `homarr@pve!homarr`
   - Role: **PVE Auditor**
   - Propagate: ✔ checked

**Step C — enter credentials in Homarr:**
Homarr expects the token split into four fields (the `api@pve!homarr=secret`
format must be broken apart):
- **Username:** `homarr`
- **Realm:** `pve`
- **Token ID:** `homarr`
- **API Key:** `<the secret from Step B1>`

**Verify the token works (from a host that can reach Proxmox):**
```bash
curl -k -H "Authorization=PVEAPIToken=homarr@pve!homarr=<SECRET>" \
  https://192.168.1.253:8006/api2/json/access/ticket
```
A `200` with a ticket JSON = token valid. (A bare call without a token returns
`401`, which only confirms the endpoint is up — that was verified during research:
`GET /api2/json/version` → `HTTP 401`.)

**Required permissions summary:** the Homarr Proxmox user needs **read-only**
access to the whole tree → `PVEAuditor` with `Propagate` at path `/`. No write
rights are needed or should be granted.

---

## 4. Plex integration

**Widgets available:** Media server streams (currently playing sessions only —
not all active sessions), Media releases (newly added / upcoming).

**Setup:**
1. Obtain your Plex token. Easiest method (per Plex support):
   - Sign in to Plex Web, open a library item, view its XML.
   - The URL contains `X-Plex-Token=<token>` — copy that value.
   (Alternatively the value is already stored in BWS as `PLEX_TOKEN`,
   ID `2b20a769-2522-4649-a484-b4980124808f`.)
2. In Homarr: **Integrations → Add → Plex**.
   - URL: your Plex server URL (e.g. `http://<plex-host>:32400` or the LAN IP).
   - API Key: the Plex token.
3. Add the **Media server streams** and/or **Media releases** widgets and bind
   them to the Plex integration.

**Caveats:** the media-server widget shows **only currently playing streams**,
not the full session list — this is by design in Homarr, not a misconfiguration.
If the integration fails with `fetch failed`, check the Plex URL is reachable
from the Homarr pod and that the token is current (Plex tokens can expire/rotate
if you sign out everywhere).

---

## 5. Docker widget on k3s — known limitation & alternatives

**The Docker integration will NOT work here.** Homarr's Docker widget talks to a
Docker daemon socket (`/var/run/docker.sock`) or Podman socket. This cluster runs
**containerd** under k3s — there is no Docker socket to mount, and the pod is
network-isolated from host sockets. The deployment manifest still carries a
`DOCKER_HOSTNAMES` env var (a v0-era leftover); it is harmless but ignored by v1.

**Recommended alternatives (all first-class Homarr v1 integrations):**

### 5a. Kubernetes integration (BEST FIT for this cluster)
Homarr has a native **Kubernetes** integration — purpose-built for exactly this
situation. It is **read-only** and shows Pods, Services, Ingresses, Nodes,
ConfigMaps, Secrets, Namespaces, and Volumes, plus basic metrics when the
**Metrics Server** is installed.

- Prerequisites: cluster ≥ 1.24, **Metrics Server** enabled, RBAC enabled.
- For Homarr running inside the cluster (our case), grant it a ServiceAccount +
  Role/RoleBinding (or ClusterRole for cluster-wide). The Helm chart does this
  via `rbac.enabled: true`; in our kustomize/ArgoCD setup you would add an
  equivalent `ServiceAccount` + `Role`/`ClusterRole` + bindings and set
  `serviceAccountName` on the Homarr pod.
- This replaces the Docker "container stats" view with real k3s object visibility.

### 5b. Beszel (lightweight host + container monitoring)
Beszel monitors servers (CPU, mem, disk, net, GPU, temp) **and** Docker/container
metrics via lightweight agents, with history and alerts. Homarr widgets:
**Beszel System Stats** (time-series CPU/mem/disk/net/container charts),
**Beszel Systems (Grid)**, **Beszel Systems (Table)**, **Beszel Alerts**.
- Credentials: Beszel **username + password** (PocketBase; default admin set at
  Beszel install). No special token.
- Trade-off: you must deploy a Beszel hub + agents. Good if you want historical
  graphs and per-host views beyond what the Kubernetes integration gives.

### 5c. Glances (no auth, host stats only)
Glances is cross-platform host monitoring. Homarr widgets: **System Resources**
(CPU/RAM/net) and **System Health Monitoring**. The integration needs **no
credentials** — it just points at a Glances instance. Note: Glances reports
**host** stats, not k3s container stats, so it is less useful than Kubernetes/
Beszel for container visibility here.

**Recommendation:** Use the **Kubernetes integration** as the primary cluster
view (zero extra infra, read-only, native). Add **Beszel** only if you want
historical graphs/alerts. Skip Glances unless you already run it.

---

## 6. Recommended dashboard layout

Homarr is board-based with responsive layouts (you can tune the grid per screen
width — desktop, tablet, mobile independently). Suggested structure using
**multiple boards** (set one as Home board):

**Board 1 — "Home" (daily driver, dark theme):**
- Top strip: **System Health Monitoring** (Proxmox node) + **Kubernetes** (pod
  status overview) side by side.
- Media column: **Plex Media server streams** + **Media releases**.
- Smart home column: **HA Entity State** widgets (a few key lights/climate) +
  one **Execute Automation** ("Movie mode" / "Goodnight").
- Bookmarks row: pinned app links (Arr stack, HA, Plex, Proxmox, Grafana, etc.).

**Board 2 — "Infra / k3s":**
- **Kubernetes** widgets (Nodes, Pods, Ingresses, Namespaces) for deep cluster view.
- If Beszel deployed: **Beszel Systems (Grid)** + **Beszel System Stats**.

**Design tips (from community best practices):**
- Use the **dark** color scheme (Homarr default; set `DEFAULT_COLOR_SCHEME: dark`
  if ever container-bootstrapping). Pick a single accent color for cohesion.
- Group by function into sections rather than one long strip — Homarr's grid
  lets you size tiles independently.
- Keep the home board uncluttered; push detail views (full pod list, Beszel
  history) to the secondary board.
- Add a **Weather** and **Date/time** widget for ambient polish.
- Build the desktop layout first, then open on mobile/tablet and adjust that
  breakpoint's grid separately.

---

## 7. Known limitations & open items

- **Docker widget:** non-functional on k3s (containerd, no docker.sock). Use
  Kubernetes integration instead. See §5.
- **Proxmox auth realm:** must be `pve` (PVE auth server), not Linux PAM, or the
  API token may fail. See §3.
- **Plex widget:** shows only currently-playing streams by design.
- **HA reachability:** confirm the Homarr pod can reach `192.168.1.251:8123`
  (LAN) or the public URL; pick whichever the cluster network allows.
- **Metrics Server:** the Kubernetes integration's metrics require the cluster
  Metrics Server to be installed — verify before relying on the charts.
- **Secret deployment:** `SECRET_ENCRYPTION_KEY` + `REDIS_URL` are created
  manually as a `homarr` k8s secret (not in git). The manifest's
  `secret-homarr.yaml` is documentation only; ArgoCD skips it (deployment uses
  `optional: true` on the secretRef). Integration API keys themselves are stored
  inside Homarr's encrypted DB (encrypted with `SECRET_ENCRYPTION_KEY`), entered
  through the UI — they are NOT k8s secrets.

---

## Sources

- Homarr docs — Proxmox: https://homarr.dev/docs/integrations/proxmox/
- Homarr docs — Home Assistant: https://homarr.dev/docs/integrations/home-assistant/
- Homarr docs — Plex: https://homarr.dev/docs/integrations/plex/
- Homarr docs — Kubernetes: https://homarr.dev/docs/integrations/kubernetes/
- Homarr docs — Docker: https://homarr.dev/docs/integrations/docker/
- Homarr docs — Beszel: https://homarr.dev/docs/integrations/beszel/
- Homarr docs — Glances: https://homarr.dev/docs/integrations/glances/
- Homarr docs — Media server widget: https://homarr.dev/docs/widgets/media-server/
- Homarr docs — Boards (layout): https://homarr.dev/docs/management/boards/
- Plex — finding an auth token: https://support.plex.tv/articles/204059436-finding-an-authentication-token-x-plex-token/
- HA long-lived tokens (dev docs): https://developers.home-assistant.io/docs/auth_api/
- Deployed manifests (ground truth): `/home/frank/homarr-dash/clusters/production/apps/homarr/manifests/`

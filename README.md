# infra-monitor

Terminal dashboard for monitoring host availability (ping + TCP ports).
Logs events in JSON Lines format — compatible with Loki / Prometheus / Grafana.

## Quickstart

**With Docker (recommended):**
```bash
git clone <repo-url>
cd infra-monitor
docker compose up --build
```

**Without Docker:**
```bash
pip install rich
python monitor.py
```

## Setup

On first launch you will see the **Setup screen**.

1. Delete example hosts with `D 1`, `D 2`, `D 3`
2. Add your hosts with `A`
3. Adjust interval and location with `C`
4. Press `S` to start monitoring

Your configuration is saved to `config.json` automatically.

## Commands (Setup screen)

| Key | Action |
|-----|--------|
| `S` | Start monitoring |
| `A` | Add host |
| `E <#>` | Edit host by number |
| `D <#>` | Delete host by number |
| `C` | Settings (interval, location, node name) |
| `Q` | Quit |

Press `Q` + Enter in the monitor view to return to Setup.

## Config reference (`config.json`)

| Field | Description |
|-------|-------------|
| `interval` | Poll interval in seconds (1–30) |
| `location` | `internal` = all hosts, `external` = only hosts with `"external": true` |
| `node` | Label for this monitoring instance (appears in logs). Auto-detected if empty. |
| `log_file` | Path to JSON Lines log file |

Each host:

| Field | Description |
|-------|-------------|
| `name` | Display label |
| `host` | IP address or hostname |
| `ping` | `true` / `false` |
| `tcp` | List of TCP ports to check, e.g. `[22, 443]` |
| `external` | `true` if reachable from internet (used with `location: external`) |

## Log format (JSON Lines)

```json
{"ts": "2026-04-04T10:00:00", "event": "START", "node": "myhost", "location": "internal", "hosts": 5, "checks": 12}
{"ts": "2026-04-04T10:05:00", "event": "DOWN",  "node": "myhost", "name": "example-server", "host": "192.168.1.10", "check": "ping"}
{"ts": "2026-04-04T10:07:00", "event": "UP",    "node": "myhost", "name": "example-server", "host": "192.168.1.10", "check": "ping", "downtime_sec": 120}
```

## Deploy on another machine

```bash
git clone <repo-url> /opt/infra-monitor
cd /opt/infra-monitor
# edit config.json
docker compose up --build -d

# update later:
git pull && docker compose up --build -d
```

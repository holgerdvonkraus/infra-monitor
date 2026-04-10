![Python 3.8+](https://img.shields.io/badge/python-3.8%2B-blue?logo=python&logoColor=white)
![Docker](https://img.shields.io/badge/docker-supported-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-Non--Commercial-red)
![Platform](https://img.shields.io/badge/platform-linux%20%7C%20macOS-lightgrey)

# infra-monitor

Terminal dashboard for monitoring host availability via **ping** and **TCP port checks**.
Events are logged in JSON Lines format — ready for ingestion by Loki, Prometheus, or Grafana.

---

## Screenshots

**Setup screen** — manage hosts and settings before starting:

```
╭─────────────────── Infrastructure Monitor — Setup ───────────────────╮
│  Interval   30s          Location   internal                          │
│  Node       prod-mon-01  Log        ./logs/monitor.log                │
╰───────────────────────────────────────────────────────────────────────╯

 #   Name               Host               Ping   Ports
 ─   ────────────────   ────────────────   ────   ────────────────
 1   gateway            10.0.0.1           ✓      22, 80
 2   app-server         10.0.0.10          ✓      22, 443, 8080
 3   public-endpoint    example.com        ✓      80, 443

[S] Start   [A] Add   [E #] Edit   [D #] Delete   [C] Settings   [Q] Quit
```

**Monitor screen** — live dashboard, refreshes every second:

```
╭──────────────────────────────────────────────────────────────────────╮
│ Infrastructure Monitor  •  internal  •  node: prod-mon-01            │
│ Ports watched: 22, 80, 443, 8080                                     │
╰──────────────────────────────────────────────────────────────────────╯
╭──────────────────────────────────────────────────────────────────────╮
│ Node: prod-mon-01    Session: 1h 22m    Events: 2    Avail: 99.8%    │
│ Hosts:  3 total   ✓ 2 up    ✗ 1 down                                 │
│ Checks: 8 total   ✓ 6 ok    ✗ 2 failing                              │
╰──────────────────────────────────────────────────────────────────────╯

 Name               Host             Ping         TCP                  Since
 ────────────────   ──────────────   ──────────   ─────────────────   ──────
 gateway            10.0.0.1         ✓            :22 ✓  :80 ✓        4m 12s
 app-server         10.0.0.10        ✗ 3m 07s     :22 ✗  :443 ✗       3m 07s   ← red bg
 public-endpoint    example.com      ✓            :80 ✓  :443 ✓       1h 22m

╭──────────────────────────────────────────────────────────────────────╮
│ Last check: 14:35:02   Next in: 23s        [Q] Back to setup         │
╰──────────────────────────────────────────────────────────────────────╯
```

---

## Features

- **Ping + TCP checks** — independently configurable per host
- **Live terminal UI** — built with [Rich](https://github.com/Textualize/rich), refreshes every second
- **State tracking** — detects UP/DOWN transitions, measures downtime duration
- **Availability metric** — per-session percentage across all checks
- **JSON Lines logging** — `event`, `node`, `host`, `check`, `downtime_sec` — compatible with Loki/Grafana
- **Internal / external mode** — skip internal-only hosts when running from an external node
- **Interactive setup** — add, edit, delete hosts without touching JSON manually
- **Docker-ready** — single `docker compose up` command, config and logs are volume-mounted
- **Zero external dependencies** — only `rich` required beyond the standard library

---

## Quickstart

### Docker (recommended)

```bash
git clone https://github.com/holgerdvonkraus/infra-monitor.git
cd infra-monitor
docker compose up --build
```

Config is mounted from `./config.json`; logs go to `./logs/monitor.log`.

> **Note:** `docker compose up` does not attach stdin, so the interactive Setup screen keys (`A`, `E`, `D`, `C`, `Q`) will not respond. To use the interactive UI, run:
> ```bash
> docker compose run --rm monitor
> ```
> Once configured, use `docker compose up -d` to run in the background with the saved `config.json`.

### Bare Python

```bash
pip install rich
python monitor.py
```

Requires Python 3.8+. On first launch the Setup screen opens automatically.

---

## Configuration

### `config.json` — top-level fields

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `interval` | int | `30` | Poll interval in seconds (1–300) |
| `location` | string | `"internal"` | `"internal"` = check all hosts; `"external"` = only hosts with `"external": true` |
| `node` | string | `""` | Label for this monitoring instance (falls back to `hostname` if empty) |
| `log_file` | string | `"./logs/monitor.log"` | Path to JSON Lines log file |
| `hosts` | array | `[]` | List of host objects (see below) |

### Host object fields

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Display label |
| `host` | string | yes | IP address or hostname |
| `ping` | bool | no | Enable ICMP ping check |
| `tcp` | array[int] | no | TCP ports to check, e.g. `[22, 443]` |
| `external` | bool | no | Mark host as internet-reachable (used with `location: "external"`) |

The `host` field accepts both IP addresses and DNS hostnames. Hostnames are resolved using the system resolver at check time, so short names (e.g. `my-server`) work if your `/etc/resolv.conf` has a matching `search` domain configured.

**Example:**

```json
{
  "interval": 30,
  "location": "internal",
  "node": "prod-mon-01",
  "log_file": "./logs/monitor.log",
  "hosts": [
    {"name": "gateway",    "host": "10.0.0.1",         "ping": true, "tcp": [22, 80],  "external": false},
    {"name": "app-server", "host": "app-server",        "ping": true, "tcp": [22, 443], "external": false},
    {"name": "public",     "host": "example.com",       "ping": true, "tcp": [80, 443], "external": true}
  ]
}
```

> **DNS tip:** to use short hostnames, the monitoring node needs:
> 1. A DNS server that resolves your internal names — set via `nameserver` in `/etc/resolv.conf` or via your DHCP/netplan config
> 2. A search domain matching your internal zone — set via `search` in `/etc/resolv.conf`
>
> On Ubuntu with systemd-resolved, check with `resolvectl status`. You can set DNS servers and search domain in netplan:
> ```yaml
> network:
>   version: 2
>   ethernets:
>     eth0:
>       dhcp4: true
>       nameservers:
>         addresses: [192.168.1.53]
>         search: [corp.local]
> ```
> After that, `app-server` resolves as `app-server.corp.local`.

### Setup screen keyboard commands

| Key | Action |
|-----|--------|
| `S` | Start monitoring |
| `A` | Add host |
| `E <#>` | Edit host by number |
| `D <#>` | Delete host by number |
| `C` | Edit settings (interval, location, node name) |
| `Q` | Quit |

Press `Q` + Enter in the monitor view to return to Setup.

---

## Log format

Events are written as JSON Lines to `log_file`. Three event types:

```jsonl
{"ts": "2026-04-03T14:00:00", "event": "START", "node": "prod-mon-01", "location": "internal", "hosts": 3, "checks": 8}
{"ts": "2026-04-03T14:32:11", "event": "DOWN",  "node": "prod-mon-01", "name": "app-server", "host": "10.0.0.10", "check": "ping"}
{"ts": "2026-04-03T14:35:18", "event": "UP",    "node": "prod-mon-01", "name": "app-server", "host": "10.0.0.10", "check": "ping", "downtime_sec": 187}
```

| Field | Description |
|-------|-------------|
| `ts` | ISO 8601 timestamp (local time) |
| `event` | `START`, `DOWN`, or `UP` |
| `node` | Monitoring node label |
| `name` | Host display name |
| `host` | IP or hostname |
| `check` | `"ping"` or `"tcp:<port>"` |
| `downtime_sec` | Seconds the check was down (present on `UP` events only) |

Ingest example with `jq`:

```bash
jq 'select(.event == "DOWN")' logs/monitor.log
```

---

## Deploy

### Remote machine via git

```bash
# First deploy
ssh user@server "git clone https://github.com/holgerdvonkraus/infra-monitor.git /opt/infra-monitor"
ssh user@server "cd /opt/infra-monitor && docker compose up --build -d"

# Push your config
scp config.json user@server:/opt/infra-monitor/config.json

# Update to latest version
ssh user@server "cd /opt/infra-monitor && git pull && docker compose up --build -d"
```

### Check logs on remote

```bash
ssh user@server "tail -f /opt/infra-monitor/logs/monitor.log | jq ."
```

---

## Contributing

1. Fork the repository and create a feature branch: `git checkout -b feat/your-feature`
2. Make your changes and ensure the monitor runs cleanly with `python monitor.py`
3. Open a Pull Request with a clear description of what was changed and why

---

## License

Non-Commercial License — Copyright (c) 2026 [Holgerd von Kraus](https://github.com/holgerdvonkraus)

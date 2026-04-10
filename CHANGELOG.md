# Changelog

## [Unreleased]

### Known issues

- **Sequential checks** — checks run one by one; with many unreachable hosts (ping timeout 5s, TCP timeout 2s) the actual poll cycle can far exceed the configured interval. To be fixed with parallel/threaded checks.
- **Q key requires Enter** — pressing Q in monitor view does not exit immediately; requires Q + Enter due to stdin readline behaviour.
- **No log rotation** — `monitor.log` grows indefinitely. Use external logrotate or set up log rotation manually.
- **Session-only availability** — uptime/availability stats reset on container restart; only the log file persists across restarts.
- **DNS-only hosts** — hosts not registered in DNS (e.g. Linux servers not joined to AD) must be added by IP manually.

---

## [0.1.0] — 2026-04-03

### Added

- Initial release: ping + TCP checks, Rich live UI, JSON Lines logging
- Interactive setup screen (add/edit/delete hosts, settings)
- `internal` / `external` location modes
- Docker support with `docker-compose.yml`
- `cap_add: NET_RAW` required for ping inside Docker
- Use `docker compose run --rm monitor` for interactive mode (not `docker compose up`)

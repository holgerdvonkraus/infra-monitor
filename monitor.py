#!/usr/bin/env python3
"""Infrastructure Monitor v0.1"""

import json
import os
import socket
import subprocess
import sys
import threading
import time
from datetime import datetime, timedelta

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")
console = Console()


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r") as f:
            return json.load(f)
    return {
        "interval": 30,
        "location": "internal",
        "node": "",
        "log_file": "./logs/monitor.log",
        "hosts": []
    }


def save_config(cfg: dict) -> None:
    with open(CONFIG_PATH, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def get_node(cfg: dict) -> str:
    return cfg.get("node") or socket.gethostname()


# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

def write_log(cfg: dict, record: dict) -> None:
    log_file = cfg.get("log_file", "./logs/monitor.log")
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
    with open(log_file, "a") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# ---------------------------------------------------------------------------
# Checks
# ---------------------------------------------------------------------------

def check_ping(host: str) -> bool:
    try:
        result = subprocess.run(
            ["ping", "-c1", "-W2", host],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=5
        )
        return result.returncode == 0
    except Exception:
        return False


def check_tcp(host: str, port: int) -> bool:
    try:
        with socket.create_connection((host, port), timeout=2):
            return True
    except Exception:
        return False


# ---------------------------------------------------------------------------
# Duration formatting
# ---------------------------------------------------------------------------

def fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m, s = divmod(seconds, 60)
        return f"{m}m {s:02d}s"
    else:
        h, rem = divmod(seconds, 3600)
        m = rem // 60
        return f"{h}h {m:02d}m"


# ---------------------------------------------------------------------------
# Setup Screen
# ---------------------------------------------------------------------------

def show_setup(cfg: dict) -> None:
    console.clear()
    node = get_node(cfg)

    # Settings panel
    settings_table = Table.grid(padding=(0, 2))
    settings_table.add_column()
    settings_table.add_column()
    settings_table.add_column()
    settings_table.add_column()
    settings_table.add_row(
        "[bold]Interval[/bold]",
        f"{cfg['interval']}s",
        "[bold]Location[/bold]",
        cfg.get("location", "internal")
    )
    settings_table.add_row(
        "[bold]Node[/bold]",
        node,
        "[bold]Log[/bold]",
        cfg.get("log_file", "./logs/monitor.log")
    )
    console.print(Panel(settings_table, title="[bold cyan]Infrastructure Monitor — Setup[/bold cyan]", border_style="cyan"))

    # Hosts table
    hosts = cfg.get("hosts", [])
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta")
    table.add_column("#", style="dim", width=3)
    table.add_column("Name", min_width=16)
    table.add_column("Host", min_width=20)
    table.add_column("Ping", width=6)
    table.add_column("Ports")

    for i, h in enumerate(hosts, 1):
        ping_str = "[green]✓[/green]" if h.get("ping") else "[dim]—[/dim]"
        ports = h.get("tcp", [])
        ports_str = ", ".join(str(p) for p in ports) if ports else "[dim]—[/dim]"
        table.add_row(str(i), h["name"], h["host"], ping_str, ports_str)

    console.print(table)
    console.print("\n[bold][[green]S[/green]] Start   [[yellow]A[/yellow]] Add   [[yellow]E #[/yellow]] Edit   [[yellow]D #[/yellow]] Delete   [[yellow]C[/yellow]] Settings   [[red]Q[/red]] Quit[/bold]\n")


def prompt_host(existing: dict = None) -> dict:
    """Prompts for host fields. If existing provided, shows defaults."""
    def ask(prompt, default=None):
        hint = f" [{default}]" if default is not None else ""
        val = input(f"  {prompt}{hint}: ").strip()
        return val if val else (str(default) if default is not None else "")

    name = ask("Name", existing.get("name") if existing else None)
    host = ask("Host/IP", existing.get("host") if existing else None)

    ping_default = "y" if (existing.get("ping", True) if existing else True) else "n"
    ping_ans = ask("Ping? (y/n)", ping_default).lower()
    ping = ping_ans in ("y", "yes", "")

    tcp_default = ",".join(str(p) for p in existing.get("tcp", [])) if existing else ""
    tcp_str = ask("TCP ports (comma-separated, empty=none)", tcp_default)
    tcp = []
    if tcp_str.strip():
        for p in tcp_str.split(","):
            p = p.strip()
            if p.isdigit():
                tcp.append(int(p))

    ext_default = "y" if (existing.get("external", False) if existing else False) else "n"
    ext_ans = ask("External? (y/n)", ext_default).lower()
    external = ext_ans in ("y", "yes")

    return {"name": name, "host": host, "ping": ping, "tcp": tcp, "external": external}


def run_setup(cfg: dict) -> str:
    """Returns 'monitor' or 'quit'."""
    while True:
        show_setup(cfg)
        try:
            cmd = input("Command: ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return "quit"

        if cmd == "q":
            return "quit"

        elif cmd == "s":
            return "monitor"

        elif cmd == "a":
            console.print("\n[bold cyan]Add Host[/bold cyan]")
            try:
                h = prompt_host()
                if h["name"] and h["host"]:
                    cfg["hosts"].append(h)
                    save_config(cfg)
                else:
                    console.print("[red]Name and Host are required.[/red]")
                    input("Press Enter...")
            except (EOFError, KeyboardInterrupt):
                pass

        elif cmd.startswith("e "):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                hosts = cfg.get("hosts", [])
                if 0 <= idx < len(hosts):
                    console.print(f"\n[bold cyan]Edit Host #{idx+1}[/bold cyan]")
                    try:
                        updated = prompt_host(hosts[idx])
                        if updated["name"] and updated["host"]:
                            hosts[idx] = updated
                            save_config(cfg)
                        else:
                            console.print("[red]Name and Host are required.[/red]")
                            input("Press Enter...")
                    except (EOFError, KeyboardInterrupt):
                        pass
                else:
                    console.print(f"[red]No host #{idx+1}[/red]")
                    input("Press Enter...")

        elif cmd.startswith("d "):
            parts = cmd.split()
            if len(parts) == 2 and parts[1].isdigit():
                idx = int(parts[1]) - 1
                hosts = cfg.get("hosts", [])
                if 0 <= idx < len(hosts):
                    h = hosts[idx]
                    try:
                        confirm = input(f"  Delete '{h['name']}' ({h['host']})? (y/n): ").strip().lower()
                        if confirm in ("y", "yes"):
                            hosts.pop(idx)
                            save_config(cfg)
                    except (EOFError, KeyboardInterrupt):
                        pass
                else:
                    console.print(f"[red]No host #{idx+1}[/red]")
                    input("Press Enter...")

        elif cmd == "c":
            console.print("\n[bold cyan]Settings[/bold cyan]")
            try:
                interval_str = input(f"  Interval (1-300) [{cfg['interval']}]: ").strip()
                if interval_str.isdigit():
                    cfg["interval"] = max(1, min(300, int(interval_str)))

                location_str = input(f"  Location (internal/external) [{cfg.get('location','internal')}]: ").strip().lower()
                if location_str in ("internal", "external"):
                    cfg["location"] = location_str

                node_str = input(f"  Node name [{cfg.get('node','')}]: ").strip()
                if node_str:
                    cfg["node"] = node_str

                save_config(cfg)
            except (EOFError, KeyboardInterrupt):
                pass

        else:
            console.print("[red]Unknown command.[/red]")
            time.sleep(0.8)


# ---------------------------------------------------------------------------
# Monitor state
# ---------------------------------------------------------------------------

class CheckState:
    """Tracks up/down state and downtime for a single (host, check) pair."""
    def __init__(self):
        self.up: bool = True
        self.since: datetime = datetime.now()
        self.total_downtime_sec: float = 0.0

    def update(self, is_up: bool) -> str | None:
        """Returns 'UP', 'DOWN', or None if no change."""
        now = datetime.now()
        if is_up == self.up:
            return None
        elapsed = (now - self.since).total_seconds()
        if not is_up:
            # Was up, now down
            self.up = False
            self.since = now
            return "DOWN"
        else:
            # Was down, now up
            self.total_downtime_sec += elapsed
            self.up = True
            self.since = now
            return "UP"

    def current_downtime(self) -> float:
        """Total downtime including current down period if applicable."""
        dt = self.total_downtime_sec
        if not self.up:
            dt += (datetime.now() - self.since).total_seconds()
        return dt

    def time_in_state(self) -> float:
        return (datetime.now() - self.since).total_seconds()


class MonitorSession:
    def __init__(self, cfg: dict):
        self.cfg = cfg
        self.node = get_node(cfg)
        self.start_time = datetime.now()
        self.event_count = 0
        # key: (host_name, check_name) -> CheckState
        self.states: dict[tuple, CheckState] = {}
        self._init_states()

    def _init_states(self):
        for h in self.cfg.get("hosts", []):
            name = h["name"]
            if h.get("ping"):
                self.states[(name, "ping")] = CheckState()
            for port in h.get("tcp", []):
                self.states[(name, f"tcp:{port}")] = CheckState()

    def run_checks(self):
        """Run all checks sequentially, update states, write logs on transitions."""
        for h in self.cfg.get("hosts", []):
            name = h["name"]
            host = h["host"]

            if h.get("ping"):
                result = check_ping(host)
                state = self.states[(name, "ping")]
                event = state.update(result)
                if event:
                    self.event_count += 1
                    record = {
                        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "event": event,
                        "name": name,
                        "host": host,
                        "check": "ping",
                        "node": self.node
                    }
                    if event == "UP":
                        record["downtime_sec"] = int(state.total_downtime_sec)
                    write_log(self.cfg, record)

            for port in h.get("tcp", []):
                result = check_tcp(host, port)
                key = (name, f"tcp:{port}")
                state = self.states[key]
                event = state.update(result)
                if event:
                    self.event_count += 1
                    record = {
                        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
                        "event": event,
                        "name": name,
                        "host": host,
                        "check": f"tcp:{port}",
                        "node": self.node
                    }
                    if event == "UP":
                        record["downtime_sec"] = int(state.total_downtime_sec)
                    write_log(self.cfg, record)

    def session_seconds(self) -> float:
        return (datetime.now() - self.start_time).total_seconds()

    def total_downtime(self) -> float:
        return sum(s.current_downtime() for s in self.states.values())

    def availability(self) -> float:
        sess = self.session_seconds()
        if sess <= 0:
            return 100.0
        checks = len(self.states)
        if checks == 0:
            return 100.0
        # availability = (total possible check-seconds - total downtime) / total possible check-seconds
        total_possible = sess * checks
        total_down = self.total_downtime()
        return max(0.0, (total_possible - total_down) / total_possible * 100)

    def counts(self):
        hosts = self.cfg.get("hosts", [])
        total_hosts = len(hosts)
        total_checks = len(self.states)

        up_checks = sum(1 for s in self.states.values() if s.up)
        down_checks = total_checks - up_checks

        # A host is "up" if ALL its checks are up
        up_hosts = 0
        for h in hosts:
            name = h["name"]
            host_states = []
            if h.get("ping"):
                host_states.append(self.states.get((name, "ping")))
            for port in h.get("tcp", []):
                host_states.append(self.states.get((name, f"tcp:{port}")))
            if not host_states or all(s.up for s in host_states if s):
                up_hosts += 1

        down_hosts = total_hosts - up_hosts
        return total_hosts, up_hosts, down_hosts, total_checks, up_checks, down_checks


# ---------------------------------------------------------------------------
# Monitor screen rendering
# ---------------------------------------------------------------------------

def build_monitor_layout(session: MonitorSession, next_check_in: int, last_check: str) -> Layout:
    cfg = session.cfg
    node = session.node
    hosts = cfg.get("hosts", [])

    # ---- Header ----
    all_ports = sorted(set(
        port for h in hosts for port in h.get("tcp", [])
    ))
    ports_str = ", ".join(str(p) for p in all_ports) if all_ports else "none"
    header_text = Text()
    header_text.append("Infrastructure Monitor", style="bold cyan")
    header_text.append("  •  ")
    header_text.append(cfg.get("location", "internal"), style="yellow")
    header_text.append("  •  node: ")
    header_text.append(node, style="green")
    header_text.append(f"  •  interval: {cfg['interval']}s")
    header_text.append(f"\nPorts watched: {ports_str}", style="dim")
    header_panel = Panel(header_text, border_style="bright_blue", padding=(0, 1))

    # ---- Summary ----
    sess_sec = session.session_seconds()
    sess_str = fmt_duration(sess_sec)
    avail = session.availability()
    total_h, up_h, down_h, total_c, up_c, down_c = session.counts()

    summary_grid = Table.grid(padding=(0, 2))
    summary_grid.add_column()
    summary_grid.add_column()
    summary_grid.add_row(
        Text.assemble(
            ("Node: ", "bold"),
            (node, "green"),
            "    ",
            ("Session: ", "bold"),
            (sess_str, "cyan"),
            "    ",
            ("Events: ", "bold"),
            (str(session.event_count), "yellow"),
            "    ",
            ("Availability: ", "bold"),
            (f"{avail:.1f}%", "green" if avail >= 95 else "yellow" if avail >= 80 else "red"),
        ),
        ""
    )
    summary_grid.add_row(
        Text.assemble(
            ("Hosts:  ", "bold"),
            (str(total_h), ""), (" total   ", ""),
            ("✓ ", "green"), (f"{up_h} up", "green"),
            ("   ✗ ", "red"), (f"{down_h} down", "red"),
        ),
        Text.assemble(
            ("Checks: ", "bold"),
            (str(total_c), ""), (" total   ", ""),
            ("✓ ", "green"), (f"{up_c} ok", "green"),
            ("   ✗ ", "red"), (f"{down_c} failing", "red"),
        )
    )
    summary_panel = Panel(summary_grid, border_style="blue", padding=(0, 1))

    # ---- Hosts table ----
    table = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold magenta", expand=True)
    table.add_column("Name", min_width=14)
    table.add_column("Host", min_width=18)
    table.add_column("Ping", width=12)
    table.add_column("TCP", min_width=24)
    table.add_column("Since", width=10)

    for h in hosts:
        name = h["name"]
        host = h["host"]

        # Ping column
        ping_cell = Text()
        ping_state = session.states.get((name, "ping"))
        if not h.get("ping"):
            ping_cell.append("—", style="dim")
        elif ping_state:
            if ping_state.up:
                ping_cell.append("✓", style="bold green")
            else:
                dur = fmt_duration(ping_state.time_in_state())
                ping_cell.append(f"✗ {dur}", style="bold red")

        # TCP column
        tcp_cell = Text()
        for i, port in enumerate(h.get("tcp", [])):
            if i > 0:
                tcp_cell.append("  ")
            state = session.states.get((name, f"tcp:{port}"))
            if state:
                if state.up:
                    tcp_cell.append(f":{port} ", style="")
                    tcp_cell.append("✓", style="green")
                else:
                    tcp_cell.append(f":{port} ", style="")
                    tcp_cell.append("✗", style="red")
        if not h.get("tcp"):
            tcp_cell.append("—", style="dim")

        # Since column
        # Use the minimum since time among all checks for this host
        host_states = []
        if h.get("ping") and ping_state:
            host_states.append(ping_state)
        for port in h.get("tcp", []):
            s = session.states.get((name, f"tcp:{port}"))
            if s:
                host_states.append(s)

        since_str = ""
        if host_states:
            # Use the most recently changed state
            most_recent = max(host_states, key=lambda s: s.since)
            since_str = fmt_duration(most_recent.time_in_state())

        # Row style: dark_red if any check is down
        any_down = any(
            not s.up for s in host_states
        )
        row_style = "on dark_red" if any_down else ""

        table.add_row(name, host, ping_cell, tcp_cell, since_str, style=row_style)

    # ---- Footer ----
    footer_text = Text.assemble(
        ("Last check: ", "bold"), (last_check, "cyan"),
        ("   Next in: ", "bold"), (f"{max(0, next_check_in)}s", "yellow"),
        ("        "), ("[Q] Back to setup", "dim")
    )
    footer_panel = Panel(footer_text, border_style="bright_blue", padding=(0, 1))

    # ---- Compose layout ----
    layout = Layout()
    layout.split_column(
        Layout(header_panel, name="header", size=4),
        Layout(summary_panel, name="summary", size=6),
        Layout(table, name="hosts"),
        Layout(footer_panel, name="footer", size=3),
    )
    return layout


# ---------------------------------------------------------------------------
# Monitor loop
# ---------------------------------------------------------------------------

def run_monitor(cfg: dict) -> None:
    session = MonitorSession(cfg)
    node = session.node

    # Log START event
    write_log(cfg, {
        "ts": datetime.now().strftime("%Y-%m-%dT%H:%M:%S"),
        "event": "START",
        "node": node,
        "location": cfg.get("location", "internal"),
        "hosts": len(cfg.get("hosts", [])),
        "checks": len(session.states)
    })

    # Input thread for Q key
    stop_flag = threading.Event()

    def input_reader():
        while not stop_flag.is_set():
            try:
                line = sys.stdin.readline()
                if line.strip().lower() == "q":
                    stop_flag.set()
                    break
            except Exception:
                break

    input_thread = threading.Thread(target=input_reader, daemon=True)
    input_thread.start()

    interval = cfg.get("interval", 30)
    last_check_time = datetime.now()
    last_check_str = last_check_time.strftime("%H:%M:%S")
    next_check_in = 0  # Run immediately on start

    # Initial check
    session.run_checks()
    last_check_time = datetime.now()
    last_check_str = last_check_time.strftime("%H:%M:%S")
    next_check_in = interval

    with Live(console=console, refresh_per_second=1, screen=True) as live:
        while not stop_flag.is_set():
            now = datetime.now()
            elapsed = (now - last_check_time).total_seconds()
            next_check_in = max(0, int(interval - elapsed))

            layout = build_monitor_layout(session, next_check_in, last_check_str)
            live.update(layout)

            if elapsed >= interval:
                session.run_checks()
                last_check_time = datetime.now()
                last_check_str = last_check_time.strftime("%H:%M:%S")
                next_check_in = interval

            time.sleep(1)

    stop_flag.set()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    cfg = load_config()

    while True:
        action = run_setup(cfg)
        if action == "quit":
            console.print("[dim]Goodbye.[/dim]")
            sys.exit(0)
        elif action == "monitor":
            # Reload config before starting monitor (in case edited externally)
            cfg = load_config()
            run_monitor(cfg)
            # After returning from monitor, reload config and go back to setup
            cfg = load_config()


if __name__ == "__main__":
    main()

"""
tools.py
--------
Simulated IT-support tools the agent can invoke ("tool calling").

In a production deployment these would call real systems (a monitoring
API, an IT service-management platform like ServiceNow/Jira, Active
Directory, etc). Here they are deterministic-but-safe simulations so the
project runs fully offline with no external accounts or credentials,
while still demonstrating the agent's ability to decide *when* to call a
tool, execute it, and use the structured result in its response.
"""

import json
import os
import random
import string
import time
from datetime import datetime, timezone

_DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data"
)
_TICKETS_PATH = os.path.join(_DATA_DIR, "tickets.json")

# A small static "history" so search_ticket_history has something to find
_SAMPLE_PAST_TICKETS = [
    {"id": "TCK-1042", "issue": "VPN connection failing after Windows update", "resolution": "Reinstalled VPN client, updated TAP adapter driver."},
    {"id": "TCK-1077", "issue": "Printer offline on shared network", "resolution": "Reassigned static IP to printer, cleared print spooler."},
    {"id": "TCK-1103", "issue": "Outlook not syncing new mail", "resolution": "Repaired Outlook profile, mailbox cache rebuilt."},
    {"id": "TCK-1129", "issue": "Laptop battery draining within 2 hours", "resolution": "Disabled background sync apps, updated power driver."},
    {"id": "TCK-1155", "issue": "Account locked after failed MFA attempts", "resolution": "Manually unlocked account after identity verification."},
]


def _ensure_data_dir():
    os.makedirs(_DATA_DIR, exist_ok=True)
    if not os.path.exists(_TICKETS_PATH):
        with open(_TICKETS_PATH, "w", encoding="utf-8") as f:
            json.dump([], f)


def run_network_diagnostic() -> dict:
    """Simulate a ping/connectivity diagnostic tool."""
    time.sleep(0)  # placeholder for real async I/O
    packet_loss = random.choice([0, 0, 0, 5, 12])
    latency_ms = random.randint(8, 120)
    status = "healthy" if packet_loss == 0 and latency_ms < 80 else "degraded"
    return {
        "tool": "run_network_diagnostic",
        "packet_loss_percent": packet_loss,
        "avg_latency_ms": latency_ms,
        "status": status,
    }


def check_service_status(service_name: str) -> dict:
    """Simulate checking whether a background service/process is running."""
    is_running = random.random() > 0.3
    return {
        "tool": "check_service_status",
        "service": service_name,
        "running": is_running,
        "status": "running" if is_running else "stopped",
    }


def restart_service(service_name: str) -> dict:
    """Simulate restarting a stuck local service (e.g. print spooler)."""
    return {
        "tool": "restart_service",
        "service": service_name,
        "result": "success",
        "message": f"'{service_name}' service was restarted successfully.",
    }


def search_ticket_history(query: str, top_n: int = 2) -> dict:
    """Simulate a keyword search over past resolved helpdesk tickets."""
    query_terms = set(query.lower().split())
    scored = []
    for ticket in _SAMPLE_PAST_TICKETS:
        overlap = len(query_terms & set(ticket["issue"].lower().split()))
        if overlap > 0:
            scored.append((overlap, ticket))
    scored.sort(key=lambda x: x[0], reverse=True)
    matches = [t for _, t in scored[:top_n]]
    return {"tool": "search_ticket_history", "query": query, "matches": matches}


def get_system_diagnostics() -> dict:
    """Simulate a system resource snapshot (CPU / RAM / Disk)."""
    return {
        "tool": "get_system_diagnostics",
        "cpu_usage_percent": random.randint(10, 95),
        "ram_usage_percent": random.randint(20, 90),
        "disk_free_gb": round(random.uniform(2, 250), 1),
    }


def create_ticket(summary: str, category: str = "General") -> dict:
    """Create (persist) an escalation ticket for a human technician."""
    _ensure_data_dir()
    with open(_TICKETS_PATH, "r", encoding="utf-8") as f:
        tickets = json.load(f)

    ticket_id = "TCK-" + "".join(random.choices(string.digits, k=4))
    ticket = {
        "id": ticket_id,
        "summary": summary,
        "category": category,
        "status": "open",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    tickets.append(ticket)
    with open(_TICKETS_PATH, "w", encoding="utf-8") as f:
        json.dump(tickets, f, indent=2)

    return {"tool": "create_ticket", "ticket": ticket}


# Registry so the agent can dispatch tool calls by name
TOOL_REGISTRY = {
    "run_network_diagnostic": run_network_diagnostic,
    "check_service_status": check_service_status,
    "restart_service": restart_service,
    "search_ticket_history": search_ticket_history,
    "get_system_diagnostics": get_system_diagnostics,
    "create_ticket": create_ticket,
}

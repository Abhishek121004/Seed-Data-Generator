from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


LOAD_SEQUENCE = [
    "roles.json",
    "countries.json",
    "states.json",
    "districts.json",
    "cities.json",
    "users.json",
    "vendor_companies.json",
    "field_engineers.json",
    "clients.json",
    "client_contacts.json",
    "billing_addresses.json",
    "service_types.json",
    "projects.json",
    "cost_centers.json",
    "tickets.json",
    "site_addresses.json",
    "allocations.json",
    "schedules.json",
    "visits.json",
    "work_orders.json",
    "tasks.json",
    "history_events.json",
]


@dataclass
class GeneratedDataset:
    tables: dict[str, list[dict]] = field(default_factory=dict)
    manifest: dict | None = None
    generated_at: datetime | None = None


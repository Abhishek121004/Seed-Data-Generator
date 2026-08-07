from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import json
import os
import random
import re
import stat
from pathlib import Path
from typing import Any

from faker import Faker

from .models import LOAD_SEQUENCE, GeneratedDataset
from .validator import validate_output


IST = timezone(timedelta(hours=5, minutes=30))
BASE_TIME = datetime(2026, 8, 1, 9, 0, tzinfo=IST)


@dataclass
class GenerationConfig:
    clients: int = 10
    projects: int = 30
    tickets: int = 200
    seed: int = 42
    output_dir: Path = Path("output")


def _slugify(value: str) -> str:
    value = re.sub(r"[^A-Za-z0-9]+", "-", value).strip("-")
    return value.upper() or "X"


def _iso(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _date(dt: datetime) -> str:
    return dt.date().isoformat()


def _rand_phone(faker: Faker) -> str:
    return "+91" + "".join(str(random_digit) for random_digit in [random.randint(6, 9)] + [random.randint(0, 9) for _ in range(9)])


class SyntheticGenerator:
    def __init__(self, config: GenerationConfig):
        self.config = config
        self.random = random.Random(config.seed)
        self.faker = Faker("en_IN")
        self.faker.seed_instance(config.seed)
        random.seed(config.seed)
        self.tables: dict[str, list[dict[str, Any]]] = {name: [] for name in LOAD_SEQUENCE}
        self.next_id: dict[str, int] = {name: 1 for name in LOAD_SEQUENCE}
        self.users: list[dict[str, Any]] = []
        self.clients: list[dict[str, Any]] = []
        self.projects: list[dict[str, Any]] = []
        self.cost_centers_by_project: dict[int, list[dict[str, Any]]] = {}
        self.ticket_primary_vendor: dict[int, int] = {}
        self.ticket_primary_schedule: dict[int, int] = {}
        self.ticket_visits: dict[int, list[dict[str, Any]]] = {}

    def _id(self, table: str) -> int:
        value = self.next_id[table]
        self.next_id[table] += 1
        return value

    def _add(self, table: str, record: dict[str, Any]) -> dict[str, Any]:
        record = {"id": self._id(table), **record}
        self.tables[table].append(record)
        return record

    def generate(self) -> GeneratedDataset:
        self._roles()
        self._geography()
        self._users()
        self._vendors()
        self._clients()
        self._reference_data()
        self._projects_and_cost_centers()
        self._tickets()
        self._manifest()
        return GeneratedDataset(tables=self.tables, manifest=self.tables.get("manifest.json", [{}])[0], generated_at=BASE_TIME)

    def _roles(self) -> None:
        for role in ["admin", "coordinator", "finance", "operations"]:
            self._add("roles.json", {"name": role})

    def _geography(self) -> None:
        country = self._add("countries.json", {"name": "India"})
        state_names = ["Karnataka", "Maharashtra", "Tamil Nadu", "Telangana", "Delhi", "Haryana"]
        states = [self._add("states.json", {"country_id": country["id"], "name": name}) for name in state_names[: max(3, min(6, self.config.clients // 2 + 2))]]
        districts = []
        for state in states:
            for _ in range(2):
                districts.append(self._add("districts.json", {"state_id": state["id"], "name": self.faker.city() + " District"}))
        for district in districts:
            for _ in range(2):
                city_name = self.faker.city()
                pincode = f"{self.random.randint(100000, 999999)}"
                self._add("cities.json", {"district_id": district["id"], "name": city_name, "pincode": pincode})

    def _users(self) -> None:
        role_ids = [record["id"] for record in self.tables["roles.json"]]
        count = max(10, self.config.projects // 2 + 6)
        for i in range(count):
            self.users.append(self._add("users.json", {
                "full_name": self.faker.name(),
                "email": self._unique_email(f"user{i}"),
                "phone": self._indian_mobile(),
                "role_id": self.random.choice(role_ids),
                "status": self.random.choices(["active", "pending", "inactive"], weights=[0.75, 0.15, 0.10])[0],
            }))

    def _vendors(self) -> None:
        cities = self.tables["cities.json"]
        vendor_count = max(3, self.config.tickets // 50 + 2)
        self.vendor_companies: list[dict[str, Any]] = []
        for i in range(vendor_count):
            city = self.random.choice(cities)
            vendor = self._add("vendor_companies.json", {
                "name": f"{self.faker.company()} Services",
                "email": self._unique_email(f"vendor{i}"),
                "phone": self._indian_mobile(),
                "pan": self._pan(),
                "gst": self._gst(),
                "city_id": city["id"],
                "status": self.random.choices(["approved", "pending", "rejected"], weights=[0.7, 0.2, 0.1])[0],
            })
            self.vendor_companies.append(vendor)
            for _ in range(self.random.randint(2, 4)):
                self._add("field_engineers.json", {
                    "vendor_company_id": vendor["id"],
                    "full_name": self.faker.name(),
                    "phone": self._indian_mobile(),
                    "is_active": self.random.random() > 0.15,
                })

    def _clients(self) -> None:
        self.client_contacts_by_client: dict[int, list[dict[str, Any]]] = {}
        for i in range(self.config.clients):
            client = self._add("clients.json", {
                "name": f"{self.faker.company()} Pvt Ltd",
                "account_manager_id": self.random.choice(self.users)["id"],
            })
            self.clients.append(client)
            contacts = []
            for _ in range(self.random.randint(1, 3)):
                contacts.append(self._add("client_contacts.json", {
                    "client_id": client["id"],
                    "full_name": self.faker.name(),
                    "phone": self._indian_mobile(),
                    "email": self._unique_email(f"contact{client['id']}"),
                }))
            self.client_contacts_by_client[client["id"]] = contacts

    def _reference_data(self) -> None:
        service_types = [
            ("Installation", "deployment"),
            ("Repair", "reactive"),
            ("Preventive Maintenance", "maintenance"),
            ("Inspection", "audit"),
            ("Emergency Callout", "urgent"),
        ]
        for name, category in service_types:
            self._add("service_types.json", {"name": name, "category": category})

    def _projects_and_cost_centers(self) -> None:
        for i in range(self.config.projects):
            project = self._add("projects.json", {
                "name": f"{self.faker.bs().title()} Project {i + 1}",
                "owner_id": self.random.choice(self.users)["id"],
                "is_completed": self.random.random() < 0.35,
            })
            self.projects.append(project)
            client = self.random.choice(self.clients)
            billing = self._add("billing_addresses.json", {
                "address_text": self.faker.address().replace("\n", ", "),
                "city_id": self.random.choice(self.tables["cities.json"])["id"],
            })
            cc = self._add("cost_centers.json", {
                "code": f"CC-{project['id']:04d}",
                "project_id": project["id"],
                "client_id": client["id"],
                "billing_address_id": billing["id"],
                "primary_contact_id": self.random.choice(self.users)["id"] if self.random.random() < 0.5 else None,
            })
            self.cost_centers_by_project[project["id"]] = [cc]

    def _tickets(self) -> None:
        projects = self.projects
        service_type_ids = [record["id"] for record in self.tables["service_types.json"]]
        creator_ids = [user["id"] for user in self.users]
        status_choices = ["open", "in_progress", "closed", "cancelled"]
        status_weights = [0.25, 0.30, 0.35, 0.10]

        for i in range(self.config.tickets):
            project = self.random.choice(projects)
            cost_center = self.cost_centers_by_project[project["id"]][0]
            client_contacts = self.client_contacts_by_client[cost_center["client_id"]]
            ticket_status = self.random.choices(status_choices, weights=status_weights)[0]
            created_at = BASE_TIME - timedelta(days=self.random.randint(1, 90), hours=self.random.randint(0, 8))
            closed_at = None
            if ticket_status in {"closed", "cancelled"}:
                closed_at = created_at + timedelta(days=self.random.randint(1, 14), hours=self.random.randint(1, 8))
            ticket = self._add("tickets.json", {
                "number": f"TKT-{i + 1:06d}",
                "project_id": project["id"],
                "service_type_id": self.random.choice(service_type_ids),
                "customer_contact_id": self.random.choice(client_contacts)["id"],
                "subject": self.faker.sentence(nb_words=6).rstrip("."),
                "status": ticket_status,
                "created_by_id": self.random.choice(creator_ids),
                "created_at": _iso(created_at),
                "closed_at": _iso(closed_at) if closed_at else None,
            })

            site_city = self.random.choice(self.tables["cities.json"])
            self._add("site_addresses.json", {
                "ticket_id": ticket["id"],
                "address_text": self.faker.address().replace("\n", ", "),
                "city_id": site_city["id"],
            })

            vendor = self.random.choice(self.vendor_companies)
            primary = self._add("allocations.json", {
                "ticket_id": ticket["id"],
                "vendor_company_id": vendor["id"],
                "nature": "primary",
                "allocated_by_id": self.random.choice(self.users)["id"],
                "allocated_at": _iso(created_at + timedelta(hours=self.random.randint(1, 24))),
            })
            self.ticket_primary_vendor[ticket["id"]] = vendor["id"]

            schedule_at = _parse_datetime(primary["allocated_at"]) + timedelta(hours=self.random.randint(2, 48))
            schedule = self._add("schedules.json", {
                "ticket_id": ticket["id"],
                "scheduled_at": _iso(schedule_at),
                "is_active": True,
                "created_by_id": self.random.choice(self.users)["id"],
            })
            self.ticket_primary_schedule[ticket["id"]] = schedule["id"]

            visits = []
            visit_count = self.random.randint(1, 3)
            start = schedule_at + timedelta(hours=1)
            engineer_ids = [engineer["id"] for engineer in self.tables["field_engineers.json"] if engineer["vendor_company_id"] == vendor["id"]]
            for visit_number in range(1, visit_count + 1):
                visit_start = start + timedelta(days=visit_number - 1, hours=self.random.randint(0, 2))
                visit_end = visit_start + timedelta(hours=self.random.randint(1, 4))
                visits.append(self._add("visits.json", {
                    "ticket_id": ticket["id"],
                    "schedule_id": schedule["id"],
                    "vendor_company_id": vendor["id"],
                    "engineer_id": self.random.choice(engineer_ids) if engineer_ids else self.random.choice([engineer["id"] for engineer in self.tables["field_engineers.json"]]),
                    "visit_number": visit_number,
                    "start_time": _iso(visit_start),
                    "end_time": _iso(visit_end),
                    "outcome": self.random.choices(["completed", "failed", "cancelled"], weights=[0.75, 0.15, 0.10])[0],
                }))
            self.ticket_visits[ticket["id"]] = visits

            work_order_created = max(_parse_datetime(v["end_time"]) for v in visits) + timedelta(hours=self.random.randint(1, 12))
            wo_status = {
                "open": "issued",
                "in_progress": self.random.choices(["issued", "invoiced"], weights=[0.6, 0.4])[0],
                "closed": self.random.choices(["invoiced", "closed"], weights=[0.5, 0.5])[0],
                "cancelled": "cancelled",
            }[ticket_status]
            work_order = self._add("work_orders.json", {
                "number": f"WO-{ticket['id']:06d}",
                "ticket_id": ticket["id"],
                "vendor_company_id": vendor["id"],
                "visit_ids": [visit["id"] for visit in visits],
                "amount": round(self.random.uniform(5000, 50000), 2),
                "currency": "INR",
                "status": wo_status,
                "created_at": _iso(work_order_created),
            })

            self._add("tasks.json", {
                "ticket_id": ticket["id"],
                "name": "Upload service report",
                "status": "closed" if ticket_status in {"closed", "cancelled"} else "open",
                "assignee_id": self.random.choice(self.users)["id"],
                "work_order_id": work_order["id"],
                "visit_id": self.random.choice(visits)["id"],
                "created_at": _iso(created_at + timedelta(hours=2)),
                "closed_at": _iso(created_at + timedelta(days=1)) if ticket_status in {"closed", "cancelled"} else None,
            })
            if self.random.random() < 0.5:
                self._add("tasks.json", {
                    "ticket_id": ticket["id"],
                    "name": "Confirm customer feedback",
                    "status": "open",
                    "assignee_id": self.random.choice(self.users)["id"],
                    "work_order_id": None,
                    "visit_id": None,
                    "created_at": _iso(created_at + timedelta(hours=3)),
                    "closed_at": None,
                })

            events = [
                ("Ticket created", created_at, self.random.choice(self.users)["id"]),
                ("Vendor allocated", _parse_datetime(primary["allocated_at"]), primary["allocated_by_id"]),
                ("Schedule confirmed", schedule_at, schedule["created_by_id"]),
            ]
            for visit in visits:
                events.append(("Visit completed", _parse_datetime(visit["end_time"]), self.random.choice(self.users)["id"]))
            events.append(("Work order issued", work_order_created, self.random.choice(self.users)["id"]))
            if ticket_status in {"closed", "cancelled"} and closed_at:
                events.append((f"Ticket {ticket_status}", closed_at, self.random.choice(self.users)["id"]))
            for action, when, actor_id in sorted(events, key=lambda item: item[1]):
                self._add("history_events.json", {
                    "ticket_id": ticket["id"],
                    "action": action,
                    "actor_id": actor_id,
                    "created_at": _iso(when),
                })

    def _manifest(self) -> None:
        record_counts = {filename: len(records) for filename, records in self.tables.items() if filename != "manifest.json"}
        self.tables["manifest.json"] = [{
            "schema_version": "Field-Service Domain Schema v1",
            "seed": self.config.seed,
            "record_counts": record_counts,
            "load_sequence": LOAD_SEQUENCE,
        }]

    def _indian_mobile(self) -> str:
        first = str(self.random.randint(6, 9))
        return "+91" + first + "".join(str(self.random.randint(0, 9)) for _ in range(9))

    def _unique_email(self, prefix: str) -> str:
        return f"{prefix}.{self.random.randint(1000, 9999)}@example.test"

    def _pan(self) -> str:
        letters = "".join(self.random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ") for _ in range(5))
        digits = "".join(str(self.random.randint(0, 9)) for _ in range(4))
        return f"{letters}{digits}{self.random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"

    def _gst(self) -> str:
        state_code = f"{self.random.randint(1, 37):02d}"
        entity_code = str(self.random.randint(1, 9))
        checksum = str(self.random.randint(0, 9))
        return f"{state_code}{self._pan()}{entity_code}Z{checksum}"


def _parse_datetime(value: str) -> datetime:
    return datetime.fromisoformat(value)


def write_dataset(dataset: GeneratedDataset, output_dir: Path) -> None:
    output_dir = output_dir.resolve()
    if output_dir.exists():
        _clear_directory(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for filename in LOAD_SEQUENCE + ["manifest.json"]:
        records = dataset.tables.get(filename, [])
        path = output_dir / filename
        if filename == "manifest.json":
            payload = records[0] if records else dataset.manifest
        else:
            payload = records
        path.write_text(json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _clear_directory(path: Path) -> None:
    if not path.exists():
        return
    for child in sorted(path.rglob("*"), key=lambda p: len(p.parts), reverse=True):
        try:
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                child.rmdir()
        except PermissionError:
            os.chmod(child, stat.S_IWRITE | stat.S_IREAD)
            if child.is_file() or child.is_symlink():
                child.unlink()
            else:
                child.rmdir()
    try:
        path.rmdir()
    except PermissionError:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        path.rmdir()


def generate_dataset(config: GenerationConfig) -> GeneratedDataset:
    generator = SyntheticGenerator(config)
    return generator.generate()


def generate_and_write(config: GenerationConfig) -> tuple[GeneratedDataset, list[str]]:
    dataset = generate_dataset(config)
    write_dataset(dataset, config.output_dir)
    issues = validate_output(config.output_dir)
    return dataset, [issue.format() for issue in issues]

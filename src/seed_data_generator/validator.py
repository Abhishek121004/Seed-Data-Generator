from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any


class ValidationError(Exception):
    pass


@dataclass
class Issue:
    file: str
    record_id: Any
    rule: str
    detail: str

    def format(self) -> str:
        return f"{self.file} id={self.record_id}: {self.rule} - {self.detail}"


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _parse_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


def _index_by_id(records: list[dict[str, Any]]) -> dict[Any, dict[str, Any]]:
    return {record["id"]: record for record in records}


def validate_output(output_dir: Path) -> list[Issue]:
    issues: list[Issue] = []

    manifest_path = output_dir / "manifest.json"
    if not manifest_path.exists():
        return [Issue("manifest.json", "-", "missing-file", "manifest.json was not found")]

    manifest = _load_json(manifest_path)
    tables: dict[str, list[dict[str, Any]]] = {}
    for filename in manifest.get("load_sequence", []):
        path = output_dir / filename
        if not path.exists():
            issues.append(Issue(filename, "-", "missing-file", "file was not found"))
            continue
        tables[filename] = _load_json(path)

    issues.extend(_validate_manifest(manifest))
    issues.extend(_validate_tables(tables, manifest))
    return issues


def _validate_manifest(manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    if manifest.get("schema_version") != "Field-Service Domain Schema v1":
        issues.append(Issue("manifest.json", "manifest", "schema-version", "schema_version must target Field-Service Domain Schema v1"))
    if not isinstance(manifest.get("seed"), int):
        issues.append(Issue("manifest.json", "manifest", "seed", "seed must be an integer"))
    if not isinstance(manifest.get("record_counts"), dict):
        issues.append(Issue("manifest.json", "manifest", "record-counts", "record_counts must be an object"))
    if not isinstance(manifest.get("load_sequence"), list):
        issues.append(Issue("manifest.json", "manifest", "load-sequence", "load_sequence must be a list"))
    elif manifest["load_sequence"] != [
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
    ]:
        issues.append(Issue("manifest.json", "manifest", "load-sequence", "load_sequence must match the dependency order in the schema"))
    return issues


def _validate_tables(tables: dict[str, list[dict[str, Any]]], manifest: dict[str, Any]) -> list[Issue]:
    issues: list[Issue] = []
    ids: dict[str, dict[Any, dict[str, Any]]] = {name: _index_by_id(records) for name, records in tables.items()}
    record_counts = manifest.get("record_counts", {})
    for filename, records in tables.items():
        if record_counts.get(filename) != len(records):
            issues.append(Issue("manifest.json", filename, "record-counts", f"{filename} count in manifest does not match the file contents"))

    def exists(table: str, record_id: Any) -> bool:
        return record_id is None or record_id in ids.get(table, {})

    def require_fk(file: str, record: dict[str, Any], field: str, table: str, rule: str) -> None:
        value = record.get(field)
        if value is None or not exists(table, value):
            issues.append(Issue(file, record.get("id"), rule, f"{field} must reference an existing {table[:-5] if table.endswith('.json') else table}"))

    def ensure_enum(file: str, record: dict[str, Any], field: str, allowed: set[str], rule: str) -> None:
        value = record.get(field)
        if value not in allowed:
            issues.append(Issue(file, record.get("id"), rule, f"{field} must be one of {sorted(allowed)}"))

    # roles
    for record in tables.get("roles.json", []):
        if not record.get("name"):
            issues.append(Issue("roles.json", record.get("id"), "required-field", "name is required"))

    # geography
    for record in tables.get("states.json", []):
        require_fk("states.json", record, "country_id", "countries.json", "fk-country")
    for record in tables.get("districts.json", []):
        require_fk("districts.json", record, "state_id", "states.json", "fk-state")
    for record in tables.get("cities.json", []):
        require_fk("cities.json", record, "district_id", "districts.json", "fk-district")
        pincode = str(record.get("pincode", ""))
        if len(pincode) != 6 or not pincode.isdigit():
            issues.append(Issue("cities.json", record.get("id"), "pincode-format", "pincode must be a 6-digit Indian PIN"))

    # users and vendors
    for record in tables.get("users.json", []):
        if not record.get("full_name"):
            issues.append(Issue("users.json", record.get("id"), "required-field", "full_name is required"))
        if not record.get("email"):
            issues.append(Issue("users.json", record.get("id"), "required-field", "email is required"))
        require_fk("users.json", record, "role_id", "roles.json", "fk-role")
        ensure_enum("users.json", record, "status", {"active", "pending", "inactive"}, "enum-status")
    for record in tables.get("vendor_companies.json", []):
        require_fk("vendor_companies.json", record, "city_id", "cities.json", "fk-city")
        ensure_enum("vendor_companies.json", record, "status", {"approved", "pending", "rejected"}, "enum-status")
    for record in tables.get("field_engineers.json", []):
        require_fk("field_engineers.json", record, "vendor_company_id", "vendor_companies.json", "fk-vendor")

    # clients
    for record in tables.get("client_contacts.json", []):
        require_fk("client_contacts.json", record, "client_id", "clients.json", "fk-client")
    for record in tables.get("billing_addresses.json", []):
        require_fk("billing_addresses.json", record, "city_id", "cities.json", "fk-city")
    for record in tables.get("service_types.json", []):
        if not record.get("name"):
            issues.append(Issue("service_types.json", record.get("id"), "required-field", "name is required"))

    # projects/cost centers
    for record in tables.get("projects.json", []):
        require_fk("projects.json", record, "owner_id", "users.json", "fk-owner")
    for record in tables.get("cost_centers.json", []):
        require_fk("cost_centers.json", record, "project_id", "projects.json", "fk-project")
        require_fk("cost_centers.json", record, "client_id", "clients.json", "fk-client")
        require_fk("cost_centers.json", record, "billing_address_id", "billing_addresses.json", "fk-billing-address")

    # tickets and dependents
    project_to_cost_center = defaultdict(list)
    for cc in tables.get("cost_centers.json", []):
        project_to_cost_center[cc["project_id"]].append(cc)
        if cc.get("primary_contact_id") is not None:
            require_fk("cost_centers.json", cc, "primary_contact_id", "users.json", "fk-primary-contact")

    client_contacts = ids.get("client_contacts.json", {})
    tickets = tables.get("tickets.json", [])
    for record in tickets:
        require_fk("tickets.json", record, "project_id", "projects.json", "fk-project")
        require_fk("tickets.json", record, "service_type_id", "service_types.json", "fk-service-type")
        require_fk("tickets.json", record, "customer_contact_id", "client_contacts.json", "fk-client-contact")
        require_fk("tickets.json", record, "created_by_id", "users.json", "fk-created-by")
        ensure_enum("tickets.json", record, "status", {"open", "in_progress", "closed", "cancelled"}, "enum-status")
        created_at = record.get("created_at")
        closed_at = record.get("closed_at")
        if not created_at:
            issues.append(Issue("tickets.json", record.get("id"), "required-field", "created_at is required"))
        else:
            try:
                created_dt = _parse_dt(created_at)
            except Exception:
                issues.append(Issue("tickets.json", record.get("id"), "datetime-format", "created_at must be ISO 8601"))
                created_dt = None
            if closed_at and created_dt:
                try:
                    closed_dt = _parse_dt(closed_at)
                    if closed_dt <= created_dt:
                        issues.append(Issue("tickets.json", record.get("id"), "date-order", "closed_at must be after created_at"))
                except Exception:
                    issues.append(Issue("tickets.json", record.get("id"), "datetime-format", "closed_at must be ISO 8601"))

        cc_list = project_to_cost_center.get(record.get("project_id"), [])
        if len(cc_list) != 1:
            issues.append(Issue("tickets.json", record.get("id"), "project-bridge", "ticket project must resolve through exactly one cost center"))

        contact = client_contacts.get(record.get("customer_contact_id"))
        project = ids.get("projects.json", {}).get(record.get("project_id"))
        if contact and project:
            cc_list = project_to_cost_center.get(project["id"], [])
            derived_client_ids = {cc["client_id"] for cc in cc_list}
            if contact.get("client_id") not in derived_client_ids:
                issues.append(Issue("tickets.json", record.get("id"), "client-mismatch", "customer_contact_id must belong to the ticket's derived client"))

    for record in tables.get("site_addresses.json", []):
        require_fk("site_addresses.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("site_addresses.json", record, "city_id", "cities.json", "fk-city")
    ticket_ids = {ticket["id"] for ticket in tickets}
    site_addresses_by_ticket: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in tables.get("site_addresses.json", []):
        site_addresses_by_ticket[record.get("ticket_id")].append(record)
    for ticket_id in ticket_ids:
        if len(site_addresses_by_ticket.get(ticket_id, [])) != 1:
            issues.append(Issue("site_addresses.json", ticket_id, "cardinality", "each ticket must have exactly one site address"))

    allocations_by_ticket: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in tables.get("allocations.json", []):
        require_fk("allocations.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("allocations.json", record, "vendor_company_id", "vendor_companies.json", "fk-vendor")
        require_fk("allocations.json", record, "allocated_by_id", "users.json", "fk-allocated-by")
        ensure_enum("allocations.json", record, "nature", {"primary", "backup"}, "enum-nature")
        allocations_by_ticket[record.get("ticket_id")].append(record)
    for ticket_id in ticket_ids:
        allocs = allocations_by_ticket.get(ticket_id, [])
        if len([alloc for alloc in allocs if alloc.get("nature") == "primary"]) != 1:
            issues.append(Issue("allocations.json", ticket_id, "cardinality", "each ticket must have exactly one primary allocation"))

    schedules_by_ticket: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in tables.get("schedules.json", []):
        require_fk("schedules.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("schedules.json", record, "created_by_id", "users.json", "fk-created-by")
        schedules_by_ticket[record.get("ticket_id")].append(record)
    for ticket_id in ticket_ids:
        schedules = schedules_by_ticket.get(ticket_id, [])
        if len(schedules) != 1:
            issues.append(Issue("schedules.json", ticket_id, "cardinality", "each ticket must have exactly one schedule"))
        elif sum(1 for schedule in schedules if schedule.get("is_active")) != 1:
            issues.append(Issue("schedules.json", ticket_id, "active-schedule", "each ticket must have exactly one active schedule"))

    visits_by_ticket: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in tables.get("visits.json", []):
        require_fk("visits.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("visits.json", record, "schedule_id", "schedules.json", "fk-schedule")
        require_fk("visits.json", record, "vendor_company_id", "vendor_companies.json", "fk-vendor")
        require_fk("visits.json", record, "engineer_id", "field_engineers.json", "fk-engineer")
        ensure_enum("visits.json", record, "outcome", {"completed", "failed", "cancelled"}, "enum-outcome")
        visits_by_ticket[record.get("ticket_id")].append(record)

    for ticket_id, visits in visits_by_ticket.items():
        visits_sorted = sorted(visits, key=lambda rec: rec.get("visit_number", 0))
        for index, visit in enumerate(visits_sorted, start=1):
            if visit.get("visit_number") != index:
                issues.append(Issue("visits.json", visit.get("id"), "visit-sequence", "visit_number must start at 1 and have no gaps per ticket"))
        for visit in visits:
            try:
                start_dt = _parse_dt(visit["start_time"])
                end_dt = _parse_dt(visit["end_time"])
                schedule = ids.get("schedules.json", {}).get(visit["schedule_id"])
                if schedule:
                    scheduled_dt = _parse_dt(schedule["scheduled_at"])
                    if start_dt < scheduled_dt:
                        issues.append(Issue("visits.json", visit.get("id"), "date-order", "start_time must be on or after scheduled_at"))
                if end_dt <= start_dt:
                    issues.append(Issue("visits.json", visit.get("id"), "date-order", "end_time must be after start_time"))
            except Exception:
                issues.append(Issue("visits.json", visit.get("id"), "datetime-format", "visit datetimes must be ISO 8601"))
        if visits_sorted:
            ticket = ids.get("tickets.json", {}).get(ticket_id)
            allocs = allocations_by_ticket.get(ticket_id, [])
            primary = next((a for a in allocs if a.get("nature") == "primary"), None)
            if primary:
                allowed_vendor = primary["vendor_company_id"]
                for visit in visits_sorted:
                    if visit.get("vendor_company_id") != allowed_vendor:
                        issues.append(Issue("visits.json", visit.get("id"), "vendor-mismatch", "visit vendor must match the ticket's primary allocation"))
                    engineer = ids.get("field_engineers.json", {}).get(visit.get("engineer_id"))
                    if engineer and engineer.get("vendor_company_id") != visit.get("vendor_company_id"):
                        issues.append(Issue("visits.json", visit.get("id"), "engineer-vendor-mismatch", "engineer must belong to the visit vendor"))

    for record in tables.get("work_orders.json", []):
        require_fk("work_orders.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("work_orders.json", record, "vendor_company_id", "vendor_companies.json", "fk-vendor")
        ticket_allocs = allocations_by_ticket.get(record.get("ticket_id"), [])
        primary = next((alloc for alloc in ticket_allocs if alloc.get("nature") == "primary"), None)
        if primary and primary.get("vendor_company_id") != record.get("vendor_company_id"):
            issues.append(Issue("work_orders.json", record.get("id"), "vendor-mismatch", "work order vendor must match the ticket's primary allocation"))
        if not isinstance(record.get("visit_ids"), list) or not record["visit_ids"]:
            issues.append(Issue("work_orders.json", record.get("id"), "required-field", "visit_ids must be a non-empty array"))
        else:
            for visit_id in record["visit_ids"]:
                visit = ids.get("visits.json", {}).get(visit_id)
                if visit is None:
                    issues.append(Issue("work_orders.json", record.get("id"), "fk-visit", f"visit_id {visit_id} must exist"))
                elif visit.get("ticket_id") != record.get("ticket_id"):
                    issues.append(Issue("work_orders.json", record.get("id"), "ticket-mismatch", "all linked visits must belong to the same ticket"))
        ensure_enum("work_orders.json", record, "status", {"issued", "invoiced", "closed", "cancelled"}, "enum-status")
        if record.get("currency") != "INR":
            issues.append(Issue("work_orders.json", record.get("id"), "currency", "currency must be INR"))
        if not isinstance(record.get("amount"), (int, float)) or record.get("amount", 0) <= 0:
            issues.append(Issue("work_orders.json", record.get("id"), "amount", "amount must be > 0"))
        if record.get("created_at"):
            try:
                created_dt = _parse_dt(record["created_at"])
            except Exception:
                issues.append(Issue("work_orders.json", record.get("id"), "datetime-format", "created_at must be ISO 8601"))
                created_dt = None
            if created_dt and isinstance(record.get("visit_ids"), list):
                linked_ends = []
                for visit_id in record["visit_ids"]:
                    visit = ids.get("visits.json", {}).get(visit_id)
                    if visit and visit.get("end_time"):
                        try:
                            linked_ends.append(_parse_dt(visit["end_time"]))
                        except Exception:
                            issues.append(Issue("work_orders.json", record.get("id"), "datetime-format", "linked visit end_time must be ISO 8601"))
                if linked_ends and created_dt < max(linked_ends):
                    issues.append(Issue("work_orders.json", record.get("id"), "date-order", "created_at must be on or after the latest linked visit end_time"))

    for record in tables.get("tasks.json", []):
        require_fk("tasks.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("tasks.json", record, "assignee_id", "users.json", "fk-assignee")
        if record.get("work_order_id") is not None:
            require_fk("tasks.json", record, "work_order_id", "work_orders.json", "fk-work-order")
        if record.get("visit_id") is not None:
            require_fk("tasks.json", record, "visit_id", "visits.json", "fk-visit")
        ensure_enum("tasks.json", record, "status", {"open", "closed"}, "enum-status")
        ticket = ids.get("tickets.json", {}).get(record.get("ticket_id"))
        if ticket and record.get("created_at") and ticket.get("created_at"):
            try:
                if _parse_dt(record["created_at"]) < _parse_dt(ticket["created_at"]):
                    issues.append(Issue("tasks.json", record.get("id"), "date-order", "task created_at must be on or after the ticket created_at"))
            except Exception:
                issues.append(Issue("tasks.json", record.get("id"), "datetime-format", "task datetimes must be ISO 8601"))
        if record.get("visit_id") is not None:
            visit = ids.get("visits.json", {}).get(record["visit_id"])
            if visit and visit.get("ticket_id") != record.get("ticket_id"):
                issues.append(Issue("tasks.json", record.get("id"), "ticket-mismatch", "task visit_id must belong to the same ticket"))
        if record.get("work_order_id") is not None:
            work_order = ids.get("work_orders.json", {}).get(record["work_order_id"])
            if work_order and work_order.get("ticket_id") != record.get("ticket_id"):
                issues.append(Issue("tasks.json", record.get("id"), "ticket-mismatch", "task work_order_id must belong to the same ticket"))
        if record.get("closed_at"):
            try:
                closed_dt = _parse_dt(record["closed_at"])
                created_dt = _parse_dt(record["created_at"])
                if closed_dt <= created_dt:
                    issues.append(Issue("tasks.json", record.get("id"), "date-order", "closed_at must be after created_at"))
            except Exception:
                issues.append(Issue("tasks.json", record.get("id"), "datetime-format", "task datetimes must be ISO 8601"))

    events_by_ticket: dict[Any, list[dict[str, Any]]] = defaultdict(list)
    for record in tables.get("history_events.json", []):
        require_fk("history_events.json", record, "ticket_id", "tickets.json", "fk-ticket")
        require_fk("history_events.json", record, "actor_id", "users.json", "fk-actor")
        events_by_ticket[record.get("ticket_id")].append(record)

    for ticket_id, events in events_by_ticket.items():
        timestamps = []
        for event in events:
            try:
                timestamps.append(_parse_dt(event["created_at"]))
            except Exception:
                issues.append(Issue("history_events.json", event.get("id"), "datetime-format", "created_at must be ISO 8601"))
        if timestamps != sorted(timestamps):
            issues.append(Issue("history_events.json", ticket_id, "chronology", "history_events must be chronological per ticket"))

    return issues

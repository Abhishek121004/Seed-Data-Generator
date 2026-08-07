# Field-Service Domain Schema v1

Target schema for the synthetic seed data generator. Conventions:

- Every entity has an `id` (your stable synthetic ID) — not repeated in the field tables below.
- All timestamps are ISO 8601 strings (`2026-08-06T14:30:00+05:30`); dates are `YYYY-MM-DD`.
- `FK` means the field holds the `id` of another record. Required FKs must resolve; optional FKs may be `null`.
- Enum values are lowercase strings and must match exactly.

## Reference / people entities

**Role** — a user's job function.

| field | type | req | notes |
|---|---|---|---|
| name | string | ✓ | e.g. `admin`, `coordinator`, `finance` |

**Country / State / District / City** — geography hierarchy.

| entity | fields |
|---|---|
| Country | `name` (req) |
| State | `country_id` FK (req), `name` (req) |
| District | `state_id` FK (req), `name` (req) |
| City | `district_id` FK (req), `name` (req), `pincode` (req, 6-digit Indian PIN) |

**User** — internal staff who create and coordinate work.

| field | type | req | notes |
|---|---|---|---|
| full_name | string | ✓ | |
| email | string | ✓ | unique across users |
| phone | string | ✓ | Indian mobile format |
| role_id | FK Role | ✓ | |
| status | enum | ✓ | `active` \| `pending` \| `inactive` |

**VendorCompany** — a service vendor that executes field work.

| field | type | req | notes |
|---|---|---|---|
| name | string | ✓ | |
| email / phone | string | ✓ | |
| pan | string | ✓ | synthetic, PAN format `AAAAA9999A` |
| gst | string | ✓ | synthetic, 15-char GSTIN format |
| city_id | FK City | ✓ | |
| status | enum | ✓ | `approved` \| `pending` \| `rejected` |

**FieldEngineer** — a technician employed by a vendor.

| field | type | req | notes |
|---|---|---|---|
| vendor_company_id | FK VendorCompany | ✓ | |
| full_name / phone | string | ✓ | |
| is_active | bool | ✓ | |

## Client-side entities

**Client** — a customer organization.

| field | type | req | notes |
|---|---|---|---|
| name | string | ✓ | company name |
| account_manager_id | FK User | – | |

**ClientContact** — a person at a customer site tickets are raised for.

| field | type | req | notes |
|---|---|---|---|
| client_id | FK Client | ✓ | |
| full_name / phone | string | ✓ | |
| email | string | – | |

**BillingAddress** — where a cost center is billed.

| field | type | req | notes |
|---|---|---|---|
| address_text | string | ✓ | street-level address |
| city_id | FK City | ✓ | |

## Work-definition entities

**ServiceType** — catalog of the kinds of work performed (e.g. Installation, Repair, Preventive Maintenance).

| field | type | req | notes |
|---|---|---|---|
| name | string | ✓ | |
| category | string | – | free-form grouping |

**Project** — a body of work. *Note: a project has no direct client link — the CostCenter is the bridge.*

| field | type | req | notes |
|---|---|---|---|
| name | string | ✓ | |
| owner_id | FK User | ✓ | |
| is_completed | bool | ✓ | |

**CostCenter** — billing unit linking a Project to its Client. Every project must have at least one.

| field | type | req | notes |
|---|---|---|---|
| code | string | ✓ | short identifier, e.g. `CC-0042` |
| project_id | FK Project | ✓ | |
| client_id | FK Client | ✓ | |
| billing_address_id | FK BillingAddress | ✓ | |
| primary_contact_id | FK User | – | |

## Ticket and dependents

**Ticket** — one unit of field work. Its client is derived: ticket → project → cost center → client.

| field | type | req | notes |
|---|---|---|---|
| number | string | ✓ | human-readable, unique, e.g. `TKT-000123` |
| project_id | FK Project | ✓ | |
| service_type_id | FK ServiceType | ✓ | |
| customer_contact_id | FK ClientContact | ✓ | contact's client must match the ticket's derived client |
| subject | string | ✓ | |
| status | enum | ✓ | `open` \| `in_progress` \| `closed` \| `cancelled` |
| created_by_id | FK User | ✓ | |
| created_at | datetime | ✓ | |
| closed_at | datetime | if closed/cancelled | must be > created_at |

**SiteAddress** — where the ticket's work happens.

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | one per ticket |
| address_text | string | ✓ | |
| city_id | FK City | ✓ | |

**Allocation** — assignment of a vendor to a ticket.

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | |
| vendor_company_id | FK VendorCompany | ✓ | |
| nature | enum | ✓ | `primary` \| `backup` |
| allocated_by_id | FK User | ✓ | |
| allocated_at | datetime | ✓ | ≥ ticket created_at |

**Schedule** — the agreed visit slot.

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | |
| scheduled_at | datetime | ✓ | ≥ allocation time |
| is_active | bool | ✓ | one active schedule per ticket |
| created_by_id | FK User | ✓ | |

**Visit** — an engineer going to site.

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | |
| schedule_id | FK Schedule | ✓ | |
| vendor_company_id | FK VendorCompany | ✓ | must match the ticket's primary allocation |
| engineer_id | FK FieldEngineer | ✓ | engineer must belong to that vendor |
| visit_number | int | ✓ | 1, 2, 3… per ticket, no gaps |
| start_time / end_time | datetime | ✓ | scheduled_at ≤ start < end |
| outcome | enum | ✓ | `completed` \| `failed` \| `cancelled` |

**WorkOrder** — the payable commitment to the vendor for visits.

| field | type | req | notes |
|---|---|---|---|
| number | string | ✓ | unique, e.g. `WO-000456` |
| ticket_id | FK Ticket | ✓ | |
| vendor_company_id | FK VendorCompany | ✓ | matches the ticket's allocation |
| visit_ids | array of FK Visit | ✓ | each visit belongs to the same ticket |
| amount | number | ✓ | > 0 |
| currency | string | ✓ | `INR` |
| status | enum | ✓ | `issued` \| `invoiced` \| `closed` \| `cancelled` |
| created_at | datetime | ✓ | ≥ latest linked visit end_time |

**Task** — an open item on a ticket (document upload, price approval, follow-up…).

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | |
| name | string | ✓ | |
| status | enum | ✓ | `open` \| `closed` |
| assignee_id | FK User | – | |
| work_order_id | FK WorkOrder | – | |
| visit_id | FK Visit | – | |
| created_at | datetime | ✓ | closed tasks also need `closed_at` > created_at |

**HistoryEvent** — the ticket's audit trail.

| field | type | req | notes |
|---|---|---|---|
| ticket_id | FK Ticket | ✓ | |
| action | string | ✓ | e.g. "Ticket created", "Vendor allocated" |
| actor_id | FK User | ✓ | |
| created_at | datetime | ✓ | events for a ticket must be chronological |

## Dependency-ordered creation sequence

```
1. Role
2. Country → State → District → City
3. User
4. VendorCompany → FieldEngineer
5. Client → ClientContact
6. BillingAddress, ServiceType
7. Project
8. CostCenter          (links Project ↔ Client)
9. Ticket → SiteAddress
10. Allocation → Schedule → Visit
11. WorkOrder
12. Task, HistoryEvent
```

`manifest.json` must declare this same order as its load sequence.

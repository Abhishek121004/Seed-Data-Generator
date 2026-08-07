# Project Brief — Synthetic Field-Service Seed Data Generator

## Goal

Build a standalone Python CLI tool (its own new repo) that generates a realistic, fully synthetic dataset for a field-service business — clients, cost centers, projects, and service tickets with their vendors, visits, work orders, and tasks — conforming exactly to the **Field-Service Domain Schema v1** (see `generic-schema.md`, handed out with this brief). The tool writes neutral JSON output files; an internal adapter will map that output into our systems later. **Loading into any real system is out of your scope.** Two interns build this independently — the better version gets adopted.

## Hard requirements

1. **Output format:** one JSON file per entity (`roles.json`, `users.json`, `clients.json`, `projects.json`, `tickets.json`, ...) plus a `manifest.json` declaring the schema version, the seed used, record counts, and the dependency-ordered load sequence. Every record has a stable synthetic ID (UUIDs or sequential ints — pick one, be consistent); all foreign keys reference those IDs.
2. **Generate in the dependency order** defined at the end of `generic-schema.md` — an entity is never written before everything it references.
3. **Zero real PII:** all names, phones, emails, addresses, and tax/bank identifiers come from Faker with the `en_IN` locale. Never copy real-world data into the repo or the output.
4. **Configurable volume + reproducible:** e.g. `generate --clients 10 --projects 30 --tickets 200 --seed 42`. Same flags + same seed → byte-identical output. Re-running overwrites the output directory cleanly.
5. **Coherent data:** every ticket belongs to a project whose cost center links it to exactly one client; allocations, visits, and work orders on a ticket all reference the same vendor; dates are ordered (ticket created < scheduled < visit start < visit end < ticket closed); statuses realistically mixed (open / in-progress / closed tickets, issued / invoiced / cancelled work orders).
6. **`validate` command:** the tool must be able to check its own output — every foreign key resolves, required fields are present, dates obey the ordering rules, and every enum value is legal per the schema. Validation failures must name the file, record ID, and rule broken.

## Suggested milestones

- **M1:** Study `generic-schema.md`. Generate core entities: roles, users, geography, vendor companies, field engineers, clients.
- **M2:** Projects, service types, billing addresses, cost centers — correctly linked.
- **M3:** Tickets and everything a ticket needs: site address, allocation, schedule, visits, work orders, tasks, history events.
- **M4:** The `validate` command, CLI polish, README, live demo.

## Definition of done

One command generates the full dataset; `validate` passes with zero errors; the README documents the schema version targeted, all CLI flags, and how an adapter would consume the output files (read `manifest.json`, load files in the declared order); no real data anywhere in the repo.

## Evaluation criteria (two versions compete)

Correctness of relationships · code readability · ease of running (clone → generate in <5 commands) · realism of generated data · quality and strictness of the `validate` command · how easy it is to add a new entity to the generator.

## Constraints

- Python. Your own new repo. `generic-schema.md` is your **only** specification — if something is ambiguous, ask your mentor rather than inventing behavior.
- No real customer, vendor, or employee data — ever, anywhere.
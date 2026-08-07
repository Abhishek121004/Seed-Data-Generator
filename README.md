<div align="center">

# 🚀 Synthetic Field-Service Seed Data Generator

**A standalone Python CLI for generating realistic, deterministic, and schema-compliant synthetic field-service datasets.**

Generate interconnected business entities such as **Clients, Projects, Vendors, Engineers, Tickets, Visits, Work Orders, and Tasks** while preserving complete referential integrity.

![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Typer](https://img.shields.io/badge/CLI-Typer-009688?style=for-the-badge)
![Faker](https://img.shields.io/badge/Faker-en__IN-blue?style=for-the-badge)
![Rich](https://img.shields.io/badge/Rich-Terminal-green?style=for-the-badge)

</div>

---

# 📖 Overview

Developing and testing enterprise applications often requires **large, realistic datasets** with complex relationships.

This project generates **fully synthetic field-service business data** while maintaining:

- ✅ Referential Integrity
- ✅ Business Relationships
- ✅ Dependency-aware Generation
- ✅ Chronological Events
- ✅ Deterministic Output
- ✅ Schema Validation

The generator follows the **Field-Service Domain Schema v1** and produces **one JSON file per entity**, along with a `manifest.json` describing the dataset.

---

# ✨ Features

- 🚀 Standalone CLI built with **Typer**
- 📦 One JSON file per entity
- 🎲 Reproducible datasets using configurable random seeds
- 🔒 Completely synthetic data generated using **Faker (`en_IN`)**
- 🔗 Automatic foreign-key relationship management
- 📅 Chronological ticket lifecycle generation
- 📄 Manifest generation with dependency-aware load sequence
- ✅ Built-in validation command
- 🎨 Rich terminal output
- ⚡ Modular and extensible architecture

---

# 🏗 Domain Model

```text
Role
│
├── User
│
├── Geography
│   ├── Country
│   ├── State
│   ├── District
│   └── City
│
├── Vendor Company
│   └── Field Engineer
│
├── Client
│   └── Client Contact
│
├── Billing Address
│
├── Service Type
│
├── Project
│
├── Cost Center
│
└── Ticket
    ├── Site Address
    ├── Allocation
    ├── Schedule
    ├── Visit
    ├── Work Order
    ├── Task
    └── History Event
```

---

# 📂 Project Structure

```text
Seed-Data-Generator/

├── src/
│   └── seed_data_generator/
│       ├── cli.py
│       ├── generator.py
│       ├── validator.py
│       ├── models.py
│       ├── __main__.py
│       └── ...
│
├── demo_output/
├── tests/
├── pyproject.toml
├── generic-schema.md
└── README.md
```

---

# ⚙ Installation

Clone the repository

```bash
git clone https://github.com/Abhishek121004/Seed-Data-Generator.git

cd Seed-Data-Generator
```

Install the package

```bash
pip install -e .
```

---

# 🚀 Usage

## Generate Dataset

```bash
seed-data-generator generate \
    --clients 10 \
    --projects 30 \
    --tickets 200 \
    --seed 42 \
    --output-dir output
```

### Available Options

| Option | Description |
|---------|-------------|
| `--clients` | Number of client organizations |
| `--projects` | Number of projects |
| `--tickets` | Number of service tickets |
| `--seed` | Random seed for deterministic generation |
| `--output-dir` | Output directory |

---

## Validate Dataset

```bash
seed-data-generator validate --output-dir output
```

The validator checks:

- Foreign Key Integrity
- Required Fields
- Enum Values
- Date Ordering
- Ticket Relationships
- Manifest Structure
- Business Rules

---

# 📁 Generated Files

```text
output/

roles.json
users.json

countries.json
states.json
districts.json
cities.json

vendor_companies.json
field_engineers.json

clients.json
client_contacts.json
billing_addresses.json

service_types.json

projects.json
cost_centers.json

tickets.json
site_addresses.json
allocations.json
schedules.json
visits.json
work_orders.json
tasks.json
history_events.json

manifest.json
```

---

# 🔄 Dependency-Aware Generation

The generator follows the schema-defined dependency order to ensure every foreign key references an existing record.

```text
Role
 ↓
Country
 ↓
State
 ↓
District
 ↓
City
 ↓
User
 ↓
Vendor Company
 ↓
Field Engineer
 ↓
Client
 ↓
Client Contact
 ↓
Billing Address
 ↓
Service Type
 ↓
Project
 ↓
Cost Center
 ↓
Ticket
 ↓
Site Address
 ↓
Allocation
 ↓
Schedule
 ↓
Visit
 ↓
Work Order
 ↓
Task
 ↓
History Event
```

---

# 🔒 Referential Integrity

Every generated dataset guarantees:

- Every Project belongs to a Cost Center
- Every Cost Center belongs to a Client
- Every Ticket belongs to a Project
- Every Engineer belongs to a Vendor Company
- Every Visit uses the allocated Vendor
- Every Work Order references valid Visits
- Every Task references existing entities
- Every foreign key is valid

---

# 🎯 Deterministic Generation

The generator produces identical datasets when using the same random seed.

```bash
seed-data-generator generate --seed 42
```

This makes the project ideal for:

- Integration Testing
- Automated Testing
- QA Environments
- CI/CD Pipelines
- Benchmarking

---

# 🛠 Tech Stack

| Technology | Purpose |
|------------|---------|
| Python 3.12+ | Core Language |
| Typer | Command Line Interface |
| Rich | Terminal Output |
| Faker (`en_IN`) | Synthetic Data Generation |
| JSON | Dataset Output |

---

# 📌 Example Use Cases

- API Development
- Backend Testing
- Integration Testing
- Database Seeding
- QA Automation
- Product Demonstrations
- Performance Testing

---

# 🔮 Future Enhancements

- Docker Support
- CSV Export
- SQLite Export
- PostgreSQL Export
- YAML Configuration
- GitHub Actions CI
- Unit Test Coverage Reports

---

# 👨‍💻 Author

**Abhishek Kumar**

B.Tech Computer Science & Engineering, BIT Mesra

GitHub: **https://github.com/Abhishek121004**

---

<div align="center">

</div>

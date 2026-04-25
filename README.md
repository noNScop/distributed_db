# Library Reservation System - Distributed Database Project

A distributed library reservation system built on a 3-node Apache Cassandra cluster.
The system handles concurrent book reservations with strong consistency guarantees
using Lightweight Transactions (LWT/CAS) to prevent over-reservation under heavy load.

## Features
- Book catalogue management (add, list, update copies)
- Member reservations with status tracking (ACTIVE, RETURNED, CANCELLED)
- Concurrent-safe reservations via Compare-And-Swap with automatic retry
- Bulk data seeding and 3 stress tests to validate correctness under load

## Setup & Running

### 1. Reserve loopback addresses for nodes 2 and 3
```bash
sudo ip addr add 127.0.0.2 dev lo
sudo ip addr add 127.0.0.3 dev lo
```

### 2. Start the 3-node Cassandra cluster
```bash
docker compose up -d
```

### 3. Wait and verify all nodes are UP (UN = Up/Normal)
```bash
docker exec cassandra1 nodetool status
```

### 4. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 5. Run the application
```bash
python app/main.py
```

The CLI will initialize the schema automatically on first run.

## Project Structure
```
distributed_db/
├── docker-compose.yml
├── app/
│   ├── main.py           # CLI entry point
│   ├── db.py             # Cassandra connection & session
│   ├── schema.py         # Keyspace & table creation
│   ├── reservations.py   # Reservation CRUD operations
│   ├── books.py          # Books CRUD operations
│   ├── seed_data.py      # Bulk test data generation
│   └── stress_tests.py   # Stress tests (single client, concurrent, race condition)
├── README.md
└── requirements.txt
```

## Stress Tests
- **ST1** — Single client hammers the same book as fast as possible
- **ST2** — 10 concurrent workers make random reservations and returns
- **ST3** — Two clients race to exhaust all copies of a single book simultaneously - verifies that both clients succeed and no over-reservation occurs
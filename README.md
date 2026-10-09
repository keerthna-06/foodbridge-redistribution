# FoodBridge — Smart Food Waste Redistribution

A working development application for matching surplus food with recipient demand. Frontend, backend, and database code are separate. No third-party dependencies are required.

## Folder structure

- `frontend/index.html`: responsive interface and styles.
- `frontend/app.js`: UI, matching, baseline comparison, API synchronization, and CSV export.
- `backend/server.py`: Python HTTP API, validation, static file serving, and transactional SQLite persistence.
- `database/schema.sql`: relational schema for food, recipients, deliveries, settings, and workspace revision.
- `database/seed.json`: sample data with expiry times relative to startup.
- `tests/test_backend.py`: persistence and allocation constraint tests.

## Run locally

Install Python 3.10 or newer. From the FoodBridge folder:

```bash
python backend/server.py
```

Open **http://localhost:8000**. On Windows, use `py` instead of `python` if necessary. Do not open the HTML file directly: it requires the API.

SQLite is initialized automatically at `database/foodbridge.sqlite3`. No database installation is needed. To change the location, set `FOODBRIDGE_DB`; use `PORT` to change port 8000. The server listens on localhost for development.

```bash
python -m unittest discover -s tests -v
```

## Features

- Add or edit surplus food and recipient requests.
- Food category, quantities in a common portion unit, expiry, and chilled storage.
- Configurable vehicle capacity, distance radius, speed, trip budget, and recipient priority weight.
- Partial allocations and splitting supply across recipients.
- Reserve, pick up, deliver, or cancel allocations; cancelled reservations release quantities.
- Confirmed delivered portions, remaining demand, active deliveries, and CSV outcome export.
- Simulate smart matching and a nearest-first baseline on the same snapshot.
- Shared database records with optimistic revision checks to prevent concurrent overwrites. A conflicting or rejected save reloads server state and shows an error; rejected local edits are discarded.

## Matching method

Coordinates represent kilometres from a shared origin. Distance is Euclidean, not live road distance. Estimated arrival time is 15 minutes handling plus distance / speed. A candidate must arrive before expiry, satisfy category and cold-chain constraints, fit remaining supply/demand, and stay inside the configured radius.

Smart matching greedily selects the highest-scoring feasible candidate:

```
score = 40 / (remaining_hours + 0.5)
      + 0.25 * allocated_portions
      + recipient_priority * priority_weight / 10
      - 2 * distance_km
```

Each allocation is bounded by vehicle capacity. Repeat until no feasible candidate remains or the concurrent trip budget is exhausted. The nearest-first baseline instead selects the shortest feasible route, using the same constraints. This is a heuristic, not a globally optimal solver. Neither strategy is guaranteed to win on every objective.

Comparison metrics include allocated portions, urgent portions allocated (under three hours), one-way route distance, trips, demand fulfilment, and unallocated food. Unallocated food is not automatically counted as waste. Simulated metrics are separate from delivered outcomes.

Matching runs in the frontend for transparency; the backend independently validates newly reserved allocations and quantity conservation in a database transaction. Recorded late deliveries are flagged. No food-safety approval is inferred from expiry matching.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/state` | Workspace records and current revision |
| PUT | `/api/state` | Atomically save `{ "revision": 0, "state": {...} }`; rejects invalid allocations and stale revisions |
| POST | `/api/reset` | Replace records with fresh demonstration data |

This simple workspace API sends a full snapshot. SQL tables remain separate and normalized for key fields. Delivery payload stores supplementary outcome metadata.

## Upload to GitHub

Create an empty repository, extract this ZIP, then run inside the FoodBridge folder:

```bash
git init
git add .
git commit -m "Add FoodBridge frontend backend and database"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/foodbridge-redistribution.git
git push -u origin main
```

Replace the URL with your repository URL. The included `.gitignore` excludes SQLite runtime data and Python cache files. No credentials are included.

## Development limits

This is a runnable educational/development project, not a production service. It has no authentication, user roles, organization isolation, messaging, live map integration, or safety verification. The local API includes a demo reset endpoint. Add authentication/authorization, controlled reset access, deployment-grade request handling, road-route estimates, transport scheduling, and food-safety workflows before real-world deployment. The earlier hosted static demo remains unchanged; this package is the separate full-stack version.

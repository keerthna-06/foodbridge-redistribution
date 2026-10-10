FoodBridge: Smart Food Waste Redistribution

**Live demo:** https://foodbridge-redistribution.onrender.com
*(Free hosting sleeps when idle, so the first load can take up to a minute.)*

FoodBridge matches surplus food from hotels, kitchens and bakeries with the shelters and community kitchens that need it, and decides who gets what before the food expires.

## The problem
Good food is thrown away every day while people nearby go hungry. Matching donors with recipients is mostly manual (calls, WhatsApp groups), so food often expires before it reaches anyone.

## What it does
- Add or edit surplus food and recipient requests (category, portions, expiry, chilled storage)
- Configurable vehicle capacity, distance radius, speed, trip budget and priority weight
- Smart matching with partial allocations, splitting supply across recipients
- Reserve, pick up, deliver or cancel allocations (cancelling releases the quantity)
- Compare smart matching against a nearest-first baseline on the same data
- Track delivered portions, remaining demand and active deliveries, with CSV export
- Shared records with revision checks, so two people can't overwrite each other

## How matching works
Coordinates are kilometres from a shared origin. A candidate must arrive before expiry, satisfy category and cold-chain rules, fit remaining supply and demand, and be inside the radius. The highest-scoring feasible candidate is picked greedily:

```
score = 40 / (remaining_hours + 0.5)
      + 0.25 * allocated_portions
      + recipient_priority * priority_weight / 10
      - 2 * distance_km
```

Each allocation is limited by vehicle capacity, and the process repeats until nothing feasible remains or the trip budget runs out. The baseline instead picks the shortest feasible route. This is a heuristic, not a globally optimal solver, and neither strategy wins on every metric.

## Project structure
```
frontend/   index.html (UI and styles), app.js (UI, matching, API sync, CSV export)
backend/    server.py (HTTP API, validation, SQLite persistence), test_backend.py
database/   schema.sql, seed.json (demo data with expiry times relative to startup)
```

## Tech stack
HTML, CSS and JavaScript (no framework) · Python standard library · SQLite · hosted on Render. No third-party dependencies.

## Run locally
Requires Python 3.10+.

```bash
git clone https://github.com/keerthna-06/foodbridge-redistribution.git
cd foodbridge-redistribution
python3 backend/server.py
```

Open http://localhost:8000. Don't open the HTML file directly, because it needs the API. Set `PORT` to change the port and `FOODBRIDGE_DB` to change the database location.

## API
| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/api/health` | Health check |
| GET | `/api/state` | Workspace records and current revision |
| PUT | `/api/state` | Save a snapshot; rejects invalid allocations and stale revisions |
| POST | `/api/reset` | Replace records with fresh demo data |

## Demo walkthrough
1. Settings → **Reset demo** (loads fresh expiry times)
2. **Overview**: available food and recipient demand
3. **Surplus food**: add a donation that expires soon
4. **Smart matching**: run it and see who receives what
5. **Redistributions**: reserve and track the allocation
6. **Impact & baseline**: compare against the nearest-first baseline

## Limitations
This is a development prototype, not a production service. There is no authentication, user roles, messaging or live map integration, distances are straight-line and not road routes, and no food-safety approval is inferred from expiry matching. The reset endpoint is open for demo purposes. On free hosting the database may reset when the server restarts.

**Next steps:** login for donors and NGOs, real road distances, SMS or WhatsApp alerts, and PostgreSQL for scale.

## Team Plain Maggie
- Geethika R
- Keerthna M
- Darshan S

Built for Commitcon, 2026.

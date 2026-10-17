# QuickCart

Tiny storefront: product catalog, cart, checkout, order history, admin panel.

- `backend/`: FastAPI + Postgres (SQLAlchemy)
- `frontend/`: React + Vite, served by nginx

## Run locally

```
docker compose up --build
```

Frontend on http://localhost:3000, API on http://localhost:8000, Adminer on http://localhost:8080.

Seed an admin user with `docker compose exec api python -m app.seed`.

Not deployed yet. Planning a DigitalOcean droplet with this same compose file.

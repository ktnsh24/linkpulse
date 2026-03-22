# LinkPulse — URL Shortener with Click Analytics

A production-grade **event-driven microservice** built with FastAPI on Azure, demonstrating the **API Gateway + Queue + Worker + Data Lake** architecture pattern.

[![Deploy LinkPulse](https://github.com/ktnsh24/linkpulse/actions/workflows/deploy.yml/badge.svg)](https://github.com/ktnsh24/linkpulse/actions/workflows/deploy.yml)

## What It Does

| Endpoint | Method | Purpose |
|---|---|---|
| `/api/v1/links` | POST | Create a short link |
| `/api/v1/links` | GET | List all links |
| `/{short_code}` | GET | Redirect → original URL (logs click event) |
| `/api/v1/analytics/{short_code}` | GET | Click stats (total, device type) |
| `/health` | GET | Health check |
| `/docs` | GET | Swagger UI |

## Architecture

```
POST /api/v1/links  →  Table Storage (link mapping)
GET /{code}         →  307 Redirect + Queue (click event)
                              │
                    Worker polls every 5s
                              │
                        ┌─────┴──────┐
                        │            │
                   Table Storage  Blob Storage
                   (click count)  (event lake)
```

**Pattern:** Event-Driven Microservice with CQRS-lite  
**Cost:** ~€0.05-0.50/month on Azure (scale-to-zero)  

## Quick Start

```bash
poetry install
docker-compose up -d azurite
poetry run uvicorn app.main:app --reload --port 8000
# Open http://localhost:8000/docs
```

## Documentation

| Document | Description |
|---|---|
| [Architecture](docs/architecture.md) | System design, patterns, alternatives, cost analysis |
| [Getting Started](docs/getting_started.md) | Local dev, Azure deployment, CI/CD setup |

## Tech Stack

Python 3.12 · FastAPI · Pydantic v2 · asyncio · Azure Storage (Table + Queue + Blob) · Application Insights · Terraform · GitHub Actions · Poetry · Docker · Azurite

## License

MIT


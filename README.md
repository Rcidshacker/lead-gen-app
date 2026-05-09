# LeadForge — AI-Powered Lead Generation Engine

![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)
![FastAPI](https://img.shields.io/badge/FastAPI-0.104+-green.svg)
![Next.js](https://img.shields.io/badge/Next.js-14+-black.svg)
![ScrapeGraphAI](https://img.shields.io/badge/ScrapeGraphAI-1.x-orange.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

**LeadForge** is an intelligent lead generation application that uses ScrapeGraphAI to scrape job postings from platforms like LinkedIn, Naukri, UpWork, Indeed, and more. It extracts structured data, scores leads using AI, and provides a rich dashboard for managing your pipeline.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌──────────────┐
│   Next.js    │────▶│   FastAPI    │────▶│  PostgreSQL   │
│  Frontend    │◀────│   Backend    │◀────│  + pgvector   │
└─────────────┘     └──────┬───────┘     └──────────────┘
                           │
                    ┌──────▼───────┐     ┌──────────────┐
                    │    Redis     │     │   Celery      │
                    │   (Broker)   │────▶│   Workers     │
                    └──────────────┘     └──────┬───────┘
                                                │
                                         ┌──────▼───────┐
                                         │ ScrapeGraphAI │
                                         │  Scraper Eng  │
                                         └──────────────┘
```

## Features

- **Multi-Platform Scraping** — LinkedIn, Naukri, UpWork, Indeed, and custom URLs
- **AI-Powered Extraction** — ScrapeGraphAI with LLMs for intelligent data extraction
- **Lead Scoring** — Automatic relevance scoring based on user profile and preferences
- **Async Job Queue** — Celery + Redis for non-blocking scraping operations
- **Semantic Search** — pgvector for finding similar leads
- **Export Options** — CSV, JSON, and webhook integrations
- **Rich Dashboard** — Real-time stats, lead management, and scraping activity

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Frontend | Next.js 14, TypeScript, Tailwind CSS, Recharts |
| Backend | FastAPI, Python 3.11+, SQLAlchemy |
| Scraper | ScrapeGraphAI, Playwright, BeautifulSoup |
| Queue | Celery, Redis |
| Database | PostgreSQL + pgvector |
| AI/LLM | OpenAI GPT-4, Anthropic Claude |
| Auth | JWT (JSON Web Tokens) |
| Deployment | Docker, Docker Compose |

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Python 3.11+
- Node.js 18+

### 1. Clone & Configure

```bash
git clone https://github.com/Rcidshacker/lead-gen-app.git
cd lead-gen-app

# Copy environment files
cp .env.example .env
cp frontend/.env.local.example frontend/.env.local

# Edit .env with your API keys
nano .env
```

### 2. Start with Docker Compose

```bash
docker-compose up -d
```

### 3. Access the App

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs

## Project Structure

```
lead-gen-app/
├── backend/              # FastAPI application
│   ├── app/
│   │   ├── api/         # API route handlers
│   │   ├── models/      # SQLAlchemy ORM models
│   │   ├── schemas/     # Pydantic request/response schemas
│   │   ├── services/    # Business logic services
│   │   └── workers/     # Celery async tasks
│   └── alembic/         # Database migrations
├── scraper/             # ScrapeGraphAI engine
│   ├── scrapers/        # Platform-specific scrapers
│   ├── extractors/      # LLM-powered data extractors
│   └── utils/           # Proxy, rate limiting, etc.
├── frontend/            # Next.js dashboard
│   └── src/
│       ├── app/         # App Router pages
│       ├── components/  # React UI components
│       ├── hooks/       # Custom React hooks
│       ├── lib/         # API client, utilities
│       └── types/       # TypeScript type definitions
└── docs/                # Architecture & deployment docs
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/register` | Register new user |
| POST | `/api/v1/auth/login` | Login and get JWT |
| GET | `/api/v1/dashboard/stats` | Dashboard statistics |
| GET/POST | `/api/v1/sources` | List/create job sources |
| POST | `/api/v1/sources/{id}/scrape` | Trigger scrape for source |
| GET | `/api/v1/leads` | List leads (with filters) |
| PATCH | `/api/v1/leads/{id}` | Update lead status |
| GET | `/api/v1/jobs` | List scraping jobs |
| POST | `/api/v1/exports/csv` | Export leads to CSV |

## Roadmap

- [x] MVP scaffolding and architecture
- [x] FastAPI backend with CRUD APIs
- [x] ScrapeGraphAI scraper engine
- [x] Celery async scraping workers
- [x] Next.js dashboard with lead management
- [x] Docker Compose deployment
- [ ] Semantic search with pgvector
- [ ] Email notifications for new leads
- [ ] CRM integrations (HubSpot, Salesforce)
- [ ] Multi-user support with RBAC
- [ ] Mobile-responsive PWA

## License

MIT License — see the [LICENSE](LICENSE) file for details.

## Disclaimer

This tool is for educational and personal use. Always respect the terms of service of the websites you scrape.

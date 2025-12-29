# Formbricks Data Seeder

A production-ready CLI tool for orchestrating a local Formbricks instance and seeding it with realistic LLM-generated survey data.

## Overview

This tool provides a clean interface to:
- Spin up Formbricks locally via Docker Compose
- Generate realistic fake survey data using Ollama (local LLM)
- Seed that data into Formbricks using only public APIs

The result: A believable, actively-used Formbricks dashboard with realistic survey data.

## Workflow

```
┌─────────────────────────────────────────────────────────────────┐
│                    FORMBRICKS DATA SEEDER                       │
└─────────────────────────────────────────────────────────────────┘

    Step 1: Start              Step 2: Generate           Step 3: Seed
    ─────────────              ────────────────           ────────────
    
    $ python main.py           $ python main.py           $ python main.py
      formbricks up              formbricks generate        formbricks seed
    
         │                            │                          │
         │                            │                          │
         ▼                            ▼                          ▼
    
    ┌──────────┐               ┌──────────┐               ┌──────────┐
    │  Docker  │               │  Ollama  │               │Formbricks│
    │ Compose  │               │   LLM    │               │   APIs   │
    └──────────┘               └──────────┘               └──────────┘
         │                            │                          │
         │                            │                          │
         ▼                            ▼                          ▼
    
    ┌──────────┐               ┌──────────┐               ┌──────────┐
    │Formbricks│               │   JSON   │               │ Populated│
    │  Running │───────────────│  Files   │───────────────│ Dashboard│
    │  :3000   │               │  data/   │               │  :3000   │
    └──────────┘               └──────────┘               └──────────┘
    
    PostgreSQL                 users.json                 Users
    + Formbricks              surveys.json                Surveys
    + Ollama                  responses.json              Responses
```

## Prerequisites

- **Python 3.9+**
- **Docker & Docker Compose** installed and running

**That's it!** Ollama runs in Docker - no separate installation needed.

## Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd assignment
```

2. Create a virtual environment and install dependencies:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

3. Copy environment template and configure:
```bash
cp .env.example .env
# Edit .env with your settings (defaults work for local development)
```

## Usage

### 1. Start Formbricks

```bash
python main.py formbricks up
```

This command:
- Pulls necessary Docker images (first run only)
- Starts PostgreSQL, Formbricks application, and Ollama
- Automatically pulls the llama2 model (first run only, may take 5-10 minutes)
- Makes Formbricks available at http://localhost:3000
- Makes Ollama available at http://localhost:11434

**Note:** On first startup, you'll need to:
1. Visit http://localhost:3000
2. Complete the initial setup wizard
3. Create an API key from Settings → API Keys
4. Update `.env` with your API key and environment ID

### 2. Generate Realistic Data

```bash
python main.py formbricks generate
```

This command:
- Uses Ollama (containerized LLM) to generate realistic survey data
- Creates 10 users, 5 surveys with questions, and survey responses
- Saves JSON files to `data/` directory:
  - `data/users.json`
  - `data/surveys.json`
  - `data/responses.json`

**No network calls to Formbricks** - this is pure data generation.
**No external API keys needed** - Ollama runs locally in Docker.

### 3. Seed Formbricks

```bash
python main.py formbricks seed
```

This command:
- Reads generated JSON files from `data/`
- Seeds data via Formbricks APIs:
  - Management API → users & surveys
  - Client API → survey responses
- Respects dependency order: users → surveys → responses

**Result:** Your Formbricks dashboard now shows realistic activity!

### 4. Stop Formbricks

```bash
python main.py formbricks down
```

This command:
- Cleanly stops all Formbricks containers
- Removes temporary resources
- Preserves data volumes (data persists across restarts)

## Architecture

```
formbricks-seeder/
├── main.py                 # CLI entry point (Click commands)
├── docker-compose.yml      # Formbricks orchestration
├── src/
│   ├── config.py          # Environment-based configuration
│   ├── orchestrator.py    # Docker lifecycle management
│   ├── generator.py       # LLM-based data generation
│   ├── seeder.py          # API-based data seeding
│   └── schemas.py         # Pydantic data models
└── data/                  # Generated JSON files (gitignored)
```

## Design Decisions

### Why Ollama?
- **Containerized**: No separate installation, runs in Docker
- **Local-first**: No API keys, no rate limits, no network dependency
- **Realistic data**: LLMs excel at generating human-like survey responses
- **Deterministic**: Structured prompts → consistent JSON schemas

### Why API-only seeding?
- **Clean**: No database manipulation, no SQL scripts
- **Maintainable**: Works across Formbricks versions
- **Correct**: Uses official, supported integration paths

### Why Docker Compose?
- **Everything in one**: Formbricks, PostgreSQL, and Ollama
- **Industry standard**: Best practice for local multi-service apps
- **Official support**: Formbricks provides Docker setup
- **Isolated**: Clean environment, easy cleanup

## API Usage

This tool uses two Formbricks API categories:

1. **Management API** (`/api/v1/management/*`)
   - Create teams, users, surveys
   - Requires API key authentication

2. **Client API** (`/api/v1/client/*`)
   - Submit survey responses
   - Public endpoint (environment ID auth)

All API interactions are in [src/seeder.py](src/seeder.py).

## Troubleshooting

**Formbricks won't start**
- Ensure Docker is running
- Check ports 3000, 5432, 11434 aren't in use
- Try `docker-compose down -v` then `python main.py formbricks up`

**Generate fails**
- Wait for Ollama container to be healthy: `docker ps`
- Model will auto-pull on first `formbricks up`
- Or pull manually: `docker exec formbricks-ollama ollama pull llama2`

**Seed fails**
- Ensure Formbricks is running
- Verify API key and environment ID in `.env`
- Check `data/*.json` files exist and are valid

## Development

Run with verbose output:
```bash
python main.py formbricks <command> --verbose
```

## License

MIT

# ⚡ InstantAPI

> **Turn any website into a REST API in 30 seconds.**

[![PyPI version](https://img.shields.io/pypi/v/instantapi.svg?color=cyan)](https://pypi.org/project/instantapi/)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Stars](https://img.shields.io/github/stars/riri/instantapi?style=social)](https://github.com/gacorpoll-ui/Instant_API)

```
$ instantapi scrape https://news.ycombinator.com

⚡ InstantAPI
─────────────────
Scraping page...          ✅ (2.1s)
Detecting schema with AI... ✅ (4.3s)
Saving to database...     ✅

┌─────────────────────────────────────────────────────┐
│  🎉 API Ready!                                      │
│  Site: Hacker News                                  │
│  Endpoints: 3 detected                              │
└─────────────────────────────────────────────────────┘

  Endpoint              Description         Items   Fields
  GET /api/stories      Top HN stories       30     title, url, score, author
  GET /api/jobs         Job listings          5     title, company, url
  GET /api/comments     Discussion items     150    text, author, time

🚀 Starting API server on port 3000...
  API:  http://localhost:3000/
  Docs: http://localhost:3000/docs
```

---

## ✨ Features

- 🤖 **AI-powered schema detection** — automatically finds data patterns in any webpage
- 🌐 **Multi-provider LLM** — works with Ollama (free/local), OpenAI, Claude, Gemini, Groq, DeepSeek
- ⚡ **30-second setup** — scrape → detect → serve in one command
- 📚 **Auto Swagger docs** — OpenAPI documentation generated automatically
- 🔍 **Built-in search & pagination** — every endpoint has `?q=`, `?page=`, `?limit=`, `?sort=`
- 📦 **Export to project** — generate a full deployable FastAPI project
- 🎨 **Beautiful CLI** — Rich terminal UI with progress, colors, tables
- 💾 **Persistent storage** — APIs saved to SQLite, load and re-serve anytime
- 🌍 **Web Dashboard** — manage your APIs visually

---

## 🚀 Quick Start

```bash
pip install instantapi
playwright install chromium  # one-time browser setup

# Option 1: Use with Ollama (free, no API key needed)
ollama pull llama3.1
instantapi init  # select Ollama

# Option 2: Use OpenAI
export OPENAI_API_KEY=sk-...
instantapi init  # select OpenAI

# Scrape any website!
instantapi scrape https://news.ycombinator.com
```

---

## 📖 Usage

### `instantapi scrape`

```bash
# Auto-detect all data patterns
instantapi scrape https://example.com

# Guided extraction — tell AI what you want
instantapi scrape https://amazon.com/laptops \
  --extract "all laptops with name, price, rating"

# Custom port
instantapi scrape https://example.com --port 8080

# Export as deployable project (don't start server)
instantapi scrape https://example.com --export ./my-api

# Just save schema, don't start server
instantapi scrape https://example.com --no-serve

# Override LLM provider for this run
instantapi scrape https://example.com --provider openai
```

### `instantapi list` / `serve` / `export`

```bash
# List all saved APIs
instantapi list

# Serve a previously saved API
instantapi serve 1 --port 3000

# Export saved API as project
instantapi export 1 ./my-api

# Delete an API
instantapi delete 1
```

### `instantapi dashboard`

```bash
# Open web dashboard (auto-opens browser)
instantapi dashboard

# Custom port
instantapi dashboard --port 9000
```

### `instantapi config`

```bash
# Interactive setup wizard
instantapi init

# Show current config
instantapi config --show

# Change provider
instantapi config --provider anthropic --model claude-sonnet-4-20250514

# Set API key
instantapi config --api-key sk-...

# Use custom/local LLM (LM Studio, vLLM, Ollama with custom URL)
instantapi config --provider custom \
  --model openai/my-model \
  --api-base http://localhost:1234/v1
```

---

## 📡 Auto-Generated API Endpoints

For each detected data pattern, InstantAPI creates:

| Endpoint | Description |
|----------|-------------|
| `GET /api/{name}` | List all items with pagination & filtering |
| `GET /api/{name}/{id}` | Get single item by index |
| `GET /api/{name}/search?q=` | Full-text search |
| `GET /api/{name}/schema` | Get field schema |
| `GET /` | API overview |
| `GET /docs` | Swagger UI |
| `GET /openapi.json` | OpenAPI spec |

**Query parameters on list endpoints:**

```
?page=1       - Page number
?limit=20     - Items per page (max 100)
?q=term       - Full-text search
?sort=field   - Sort by field
?order=desc   - Sort order (asc/desc)
```

---

## 🤖 LLM Providers

| Provider | Default Model | Free? | Notes |
|----------|--------------|-------|-------|
| **Ollama** | `llama3.1` | ✅ Free | Local, requires ~8GB RAM |
| **OpenAI** | `gpt-4o-mini` | ❌ Paid | Best accuracy |
| **Anthropic** | `claude-sonnet-4-20250514` | ❌ Paid | Excellent reasoning |
| **Gemini** | `gemini-2.0-flash` | ❌ Paid | Fast & cheap |
| **Groq** | `llama-3.1-70b-versatile` | ⚡ Fast | Very fast inference |
| **DeepSeek** | `deepseek-chat` | 💰 Cheap | Best price/performance |
| **Custom** | Any LiteLLM string | - | Any OpenAI-compatible API |

---

## 📦 Export & Deploy

Export any scraped API as a standalone FastAPI project:

```bash
instantapi scrape https://example.com --export ./my-api
cd my-api
pip install -r requirements.txt
uvicorn main:app --reload
```

Or with Docker:

```bash
docker build -t my-api .
docker run -p 8000:8000 my-api
```

The exported project includes:
- `main.py` — FastAPI application
- `requirements.txt` — Dependencies
- `Dockerfile` — Ready to containerize
- `README.md` — Auto-generated docs

---

## 🛠️ Installation

```bash
# Install from PyPI
pip install instantapi

# Or install from source
git clone https://github.com/gacorpoll-ui/Instant_API
cd instantapi
pip install -e ".[dev]"

# Install Playwright browsers (required for scraping)
playwright install chromium
```

**Requirements:**
- Python 3.10+
- [Playwright](https://playwright.dev/python/) (for browser scraping)
- An LLM: [Ollama](https://ollama.ai) (free) or API key for cloud providers

---

## 🙏 Tech Stack

- **[FastAPI](https://fastapi.tiangolo.com/)** — API framework
- **[Playwright](https://playwright.dev/python/)** — Headless browser scraping
- **[LiteLLM](https://github.com/BerriAI/litellm)** — Universal LLM provider
- **[Typer](https://typer.tiangolo.com/)** + **[Rich](https://github.com/Textualize/rich)** — CLI
- **[Pydantic](https://pydantic.dev/)** — Data validation
- **[aiosqlite](https://aiosqlite.omnilib.dev/)** — Async SQLite storage

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">
  Made with ❤️ by <a href="https://github.com/riri">Riri</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/gacorpoll-ui/Instant_API/issues">Report Bug</a>
  &nbsp;·&nbsp;
  <a href="https://github.com/gacorpoll-ui/Instant_API/issues">Request Feature</a>
</div>

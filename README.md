# PostgreSQL Observability AI Agent

An AI-powered PostgreSQL observability agent that uses **Prometheus** metrics and **VictoriaLogs** log data through **MCP servers**, reasons with **LangGraph**, and provides a ChatGPT-style interface for database monitoring.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        React Frontend                           │
│   ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌────────────┐  │
│   │ Database  │  │   Chat    │  │  Message   │  │ Tool Call  │  │
│   │ Selector  │  │  Window   │  │  Bubbles   │  │   Trace    │  │
│   └──────────┘  └───────────┘  └────────────┘  └────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │  REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    FastAPI Backend                               │
│   ┌──────────────┐  ┌──────────┐  ┌───────────────────────────┐ │
│   │  POST /chat  │  │ GET /dbs │  │      GET /health          │ │
│   └──────┬───────┘  └──────────┘  └───────────────────────────┘ │
│          │                                                      │
│          ▼                                                      │
│   ┌──────────────────────────────────────────────────────┐      │
│   │             LangGraph ReAct Agent                    │      │
│   │   ┌─────────┐  ┌────────┐  ┌──────────────────────┐ │      │
│   │   │ Reason  │→ │  Tool  │→ │  Observe & Repeat    │ │      │
│   │   └─────────┘  └───┬────┘  └──────────────────────┘ │      │
│   └─────────────────────┼────────────────────────────────┘      │
│                         │                                       │
│          ┌──────────────┼──────────────┐                        │
│          ▼              ▼              │                        │
│   ┌─────────────┐ ┌──────────────┐    │      ┌──────────────┐  │
│   │ Prometheus  │ │ VictoriaLogs │    └─────▶│   Langfuse   │  │
│   │ MCP Server  │ │ MCP Server   │           │  (Tracing)   │  │
│   │ (stdio)     │ │ (stdio)      │           └──────────────┘  │
│   └──────┬──────┘ └──────┬───────┘                              │
│          │               │                                      │
└──────────┼───────────────┼──────────────────────────────────────┘
           ▼               ▼
     ┌───────────┐   ┌──────────────┐
     │Prometheus │   │ VictoriaLogs │
     │  Server   │   │   Instance   │
     └───────────┘   └──────────────┘
```

---

## Prerequisites

- **Python 3.11+**
- **Node.js 20+**
- **Docker** (for MCP server containers)
- A running **Prometheus** instance
- A running **VictoriaLogs** instance
- An **OpenAI** or **Anthropic** API key

---

## Quick Start

### 1. Clone & Configure

```bash
git clone <repo-url>
cd postgres-ai-agent

# Copy and fill in your environment variables
cp .env.example .env
# Edit .env with your API keys and server URLs
```

### 2. Backend Setup

```bash
cd backend
python -m venv venv
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
python main.py
```

The backend runs at **http://localhost:8000**.

### 3. Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The frontend runs at **http://localhost:3000**.

### 4. Docker Compose (Full Stack)

```bash
docker compose up --build
```

- Frontend: **http://localhost:3000**
- Backend:  **http://localhost:8000**

---

## Configuration

### Environment Variables (`.env`)

| Variable               | Description                        | Default                      |
| ---------------------- | ---------------------------------- | ---------------------------- |
| `PROMETHEUS_URL`       | Prometheus server URL              | `http://localhost:9090`      |
| `VICTORIA_LOGS_URL`    | VictoriaLogs instance URL          | `http://localhost:9428`      |
| `LLM_PROVIDER`         | `openai` or `anthropic`            | `openai`                     |
| `LLM_MODEL`            | Model name                         | `gpt-4o`                     |
| `OPENAI_API_KEY`       | OpenAI API key                     | —                            |
| `ANTHROPIC_API_KEY`    | Anthropic API key                  | —                            |
| `LANGFUSE_PUBLIC_KEY`  | Langfuse public key                | —                            |
| `LANGFUSE_SECRET_KEY`  | Langfuse secret key                | —                            |
| `LANGFUSE_HOST`        | Langfuse host URL                  | `https://cloud.langfuse.com` |

### Database List

Edit `backend/databases.yaml` to add/remove databases:

```yaml
databases:
  - name: prod-db-01
    label: "Production DB 01"
  - name: staging-db-01
    label: "Staging DB 01"
```

---

## MCP Servers

This project uses **open-source MCP servers** — no custom MCP code is needed:

| Server            | Source                                                                   | Docker Image                                    |
| ----------------- | ------------------------------------------------------------------------ | ----------------------------------------------- |
| Prometheus MCP    | [pab1it0/prometheus-mcp-server](https://github.com/pab1it0/prometheus-mcp-server) | `ghcr.io/pab1it0/prometheus-mcp-server:latest`  |
| VictoriaLogs MCP  | [VictoriaMetrics-Community/mcp-victorialogs](https://github.com/VictoriaMetrics-Community/mcp-victorialogs) | `ghcr.io/victoriametrics-community/mcp-victorialogs` |

The agent connects to these servers via **stdio transport** at startup.

---

## Example Queries

Here are some questions you can ask the agent:

| Category        | Example Query                                                |
| --------------- | ------------------------------------------------------------ |
| **Health**      | "What's the overall health of my database?"                  |
| **Connections** | "How many active connections are there right now?"            |
| **Performance** | "What's the cache hit ratio for the last hour?"              |
| **Replication** | "Is there any replication lag?"                               |
| **Locks**       | "Are there any deadlocks or long-running lock waits?"        |
| **Diagnostics** | "Why is my database running slow?"                            |
| **Metrics**     | "Show the transaction rate over the last 24 hours"           |
| **Storage**     | "What's the current disk usage and table bloat?"             |
| **Correlation** | "Correlate the connection spike with any error logs"         |

---

## API Endpoints

| Method | Path          | Description                     |
| ------ | ------------- | ------------------------------- |
| GET    | `/health`     | Health check                    |
| GET    | `/databases`  | List available databases        |
| POST   | `/chat`       | Send a message to the agent     |

### POST `/chat` Example

```json
{
  "message": "What's the current connection count?",
  "database": "prod-db-01",
  "conversation_id": "abc-123",
  "history": [
    { "role": "user", "content": "Hello" },
    { "role": "assistant", "content": "Hi! How can I help?" }
  ]
}
```

---

## Project Structure

```
postgres-ai-agent/
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── globals.css          # Global styles & premium theme
│   │   │   ├── layout.tsx           # Root layout
│   │   │   └── page.tsx             # Main chat interface & logic
│   │   ├── components/
│   │   │   ├── ChatWindow.tsx       # Message list & empty state
│   │   │   ├── MessageBubble.tsx    # User/assistant bubbles & Markdown
│   │   │   ├── DatabaseSelector.tsx # Searchable database dropdown
│   │   │   └── ToolCallTrace.tsx    # Collapsible tool call panel
│   │   ├── lib/
│   │   │   └── api.ts               # REST client & types
│   ├── Dockerfile                   # Multi-stage production build
│   ├── package.json
│   ├── next.config.ts
│   └── tsconfig.json
├── backend/
│   ├── main.py                      # FastAPI server
│   ├── agent.py                     # LangGraph ReAct agent + MCP clients
│   ├── config.py                    # Settings & database config loader
│   ├── databases.yaml               # Configurable database list
│   ├── requirements.txt
│   └── Dockerfile                   # Python-based Docker setup
├── docker-compose.yml               # Orchestrates agent + MCP servers
├── .env.example
├── .gitignore
└── README.md
```

---

## Observability

All LLM calls, tool invocations, and agent steps are traced via **Langfuse** when keys are configured. Each trace includes:
- Session ID (conversation)
- Database name as metadata tag
- Full tool call arguments and results

---

## License

MIT

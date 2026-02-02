# myAgent - Multi-Turn Funnel Analysis Agent

AI agent with smart routing for funnel and cohort analysis.

## Features

- 🔄 **Multi-turn conversations** with context preservation
- 🎯 **Smart routing** - LLM decides when to call APIs vs answer from memory
- 🔧 **Two analysis tools**:
  - Funnel Analysis: Overall conversion metrics
  - Cohort Analysis: Deep-dive into specific steps
- 📊 **Structured reports** with insights and recommendations
- 💾 **Persistent sessions** via SQLite
- 🔁 **Automatic retry** with exponential backoff

## Architecture

```
User → FastAPI → LangGraph Agent
                     ↓
          Smart Router (Vertex AI)
                     ↓
         ┌──────────┴──────────┐
         ↓                     ↓
    Funnel API           Cohort API
         ↓                     ↓
    Generate Report ← Answer from Context
```

## Installation

```bash
# Create virtual environment
python3.11 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

## Configuration

Required environment variables in `.env`:

```bash
# Your funnel analysis API
FUNNEL_API_BASE_URL=http://localhost:8080/api

# GCP Vertex AI
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1

# Optional: Service account (or use ADC)
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/sa.json
```

## Quick Start

### Option 1: With Mock API (No Setup Required)

Perfect for testing without real funnel analysis endpoints:

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Start everything at once
python run_all.py

# 3. In another terminal, run the example
python example_usage.py
```

Or manually:

```bash
# Terminal 1: Start Mock API
python mock_api/mock_server.py

# Terminal 2: Start myAgent (no .env needed for mock)
python -m app.main

# Terminal 3: Run examples
python example_usage.py
```

### Option 2: With Real APIs

```bash
# 1. Configure environment
cp .env.example .env
# Edit .env with your GCP and API settings

# 2. Start the server
python -m app.main

# 3. Test the API
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "test-session",
    "message": "Show me the signup funnel for January 2026"
  }'
```

## API Endpoints

### POST /chat
Multi-turn conversation endpoint.

**Request:**
```json
{
  "session_id": "unique-session-id",
  "message": "Show me the signup funnel for January"
}
```

**Response:**
```json
{
  "session_id": "unique-session-id",
  "response": "I need the end date...",
  "needs_input": true,
  "missing_params": ["end_date"],
  "metadata": {
    "action_taken": "ask_user",
    "funnel_id": null
  }
}
```

## Usage Examples

### Initial Analysis
```
User: "Analyze the checkout funnel from Jan 1 to Jan 31"
Agent: [Calls Funnel API] → Returns structured report

User: "What's the overall conversion?"
Agent: [Answers from memory] → "22.5%"

User: "Why are users dropping at payment step?"
Agent: [Calls Cohort API for step 2] → Deep-dive analysis
```

## Project Structure

```
myAgent/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings management
│   ├── models/
│   │   ├── __init__.py
│   │   ├── parameters.py    # Pydantic parameter models
│   │   ├── responses.py     # API response models
│   │   └── state.py         # LangGraph state schema
│   ├── agent/
│   │   ├── __init__.py
│   │   ├── graph.py         # LangGraph state machine
│   │   └── nodes.py         # Agent node implementations
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── funnel_client.py # Funnel API client
│   │   └── cohort_client.py # Cohort API client
│   ├── llm/
│   │   ├── __init__.py
│   │   └── vertex_ai.py     # Vertex AI integration
│   └── session/
│       ├── __init__.py
│       └── manager.py       # SQLite session manager
├── mock_api/
│   ├── __init__.py
│   └── mock_server.py       # Mock funnel/cohort API for testing
├── tests/
│   ├── __init__.py
│   └── test_components.py   # Component tests
├── data/                    # SQLite databases (gitignored)
├── example_usage.py         # Usage examples
├── run_all.py               # Quick start script
├── .env
├── requirements.txt
└── README.md
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run component tests
python tests/test_components.py

# Run tests (when pytest tests are added)
pytest

# Format code
black app/ mock_api/ tests/
ruff check app/ mock_api/ tests/
```

## Mock API Details

The mock server (`mock_api/mock_server.py`) provides:

**Funnel Analysis Endpoint:**
- Generates realistic conversion data with random drop-offs
- Returns a unique `funnel_id` for follow-up queries
- Caches funnel data for cohort analysis

**Cohort Analysis Endpoint:**
- Requires valid `funnel_id` from previous funnel analysis
- Returns characteristics of converted vs dropped users
- Includes insights about key differences

**Example Response:**
```json
{
  "funnel_id": "fnl_a1b2c3d4e5f6",
  "steps": [
    {"step_index": 0, "name": "signup", "users": 10000, "conversion_rate": 100.0},
    {"step_index": 1, "name": "verify_email", "users": 7500, "conversion_rate": 75.0, "drop_off": 2500},
    {"step_index": 2, "name": "first_purchase", "users": 5625, "conversion_rate": 75.0, "drop_off": 1875}
  ],
  "overall_conversion": 56.25,
  "total_users": 10000
}
```

## Troubleshooting

**Mock API won't start:**
- Check if port 8080 is already in use: `lsof -i :8080`
- Kill existing process: `kill -9 <PID>`

**myAgent won't start:**
- Check if port 8000 is in use: `lsof -i :8000`
- Verify dependencies are installed: `pip list | grep -E "(fastapi|langgraph)"`

**Import errors:**
- Make sure you're in the virtual environment: `which python`
- Reinstall dependencies: `pip install -r requirements.txt`

**Vertex AI errors (when using real LLM):**
- Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env`
- Or run: `gcloud auth application-default login`
- Verify project ID: `gcloud config get-value project`

## License

MIT

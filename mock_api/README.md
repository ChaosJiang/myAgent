# Mock API Testing Guide

Quick reference for testing myAgent with mock APIs.

## Starting the Mock Server

```bash
# Default: Port 8080
python mock_api/mock_server.py
```

Server endpoints:
- Health: `GET http://localhost:8080/health`
- Funnel: `POST http://localhost:8080/api/funnel-analysis`
- Cohort: `POST http://localhost:8080/api/cohort-analysis`

## Example Requests

### 1. Funnel Analysis

```bash
curl -X POST http://localhost:8080/api/funnel-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "start_date": "2026-01-01T00:00:00Z",
    "end_date": "2026-01-31T23:59:59Z",
    "funnel_steps": ["signup", "verify_email", "purchase"],
    "user_segment": "new_users"
  }'
```

Response:
```json
{
  "funnel_id": "fnl_abc123",
  "steps": [
    {"step_index": 0, "name": "signup", "users": 10000, ...},
    {"step_index": 1, "name": "verify_email", "users": 7500, ...}
  ],
  "overall_conversion": 56.25,
  "total_users": 10000
}
```

### 2. Cohort Analysis

```bash
curl -X POST http://localhost:8080/api/cohort-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "funnel_id": "fnl_abc123",
    "step_index": 1
  }'
```

Response:
```json
{
  "step_name": "verify_email",
  "step_index": 1,
  "converted": {
    "count": 7500,
    "characteristics": {
      "avg_age": 28.5,
      "device_split": {"mobile": 65, "desktop": 35}
    }
  },
  "dropped": {
    "count": 2500,
    "characteristics": {...}
  },
  "insights": {
    "key_differences": [
      "Dropped users spent 75% less time",
      "Desktop users have higher drop-off"
    ]
  }
}
```

## Testing with myAgent

### Full Stack Test

```bash
# Terminal 1: Mock API
python mock_api/mock_server.py

# Terminal 2: myAgent
python -m app.main

# Terminal 3: Run examples
python example_usage.py
```

### Quick Test

```bash
# Start both services
python run_all.py

# In another terminal
python example_usage.py quick
```

## Mock Data Characteristics

The mock server generates:
- **Funnel steps**: Random conversion rates between 60-85%
- **User counts**: Starts at 10,000, drops per step
- **Cohort data**: Realistic age, geography, device split
- **Insights**: 4 pre-generated insight patterns

Data is randomized per request but realistic for testing agent behavior.

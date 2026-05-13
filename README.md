# ADK Investment Research Agent on GKE

A multi-agent investment research assistant built with [Google Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and deployed to Google Kubernetes Engine (GKE) Autopilot.

Given a company or stock, the agent team researches it on Wikipedia, stress-tests an investment thesis through an analyst/critic loop, then produces parallel bull and bear cases before writing a final report to disk.

## Agent Architecture

```
greeter
  └── SequentialAgent: investment_research_team
        ├── LoopAgent: research_team (max 3 iterations)
        │     ├── researcher          ← Wikipedia research
        │     ├── analyst             ← writes investment thesis
        │     └── devils_advocate     ← critiques; escalates when thesis is solid
        ├── ParallelAgent: case_writers
        │     ├── bull_case_writer    ← optimistic scenario
        │     └── bear_case_writer    ← pessimistic scenario
        └── report_writer             ← saves final .txt report
```

**State keys:** `PROMPT` → `research` → `INVESTMENT_THESIS` ↔ `CRITICAL_FEEDBACK` (loop) → `BULL_CASE` + `BEAR_CASE` → file output saved to `investment_reports/`

## Prerequisites

- Google Cloud project with billing enabled
- `gcloud` CLI authenticated (`gcloud auth login`)
- `kubectl` installed
- Python 3.11+
- A `.env` file in `investment_analyst/` with:

```env
MODEL=gemini-2.5-flash
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
```

## Setup

### 1. Install dependencies

```bash
uv pip install -r investment_analyst/requirements.txt
```

### 2. Run locally with ADK

```bash
cd adk_multiagent_systems
adk web agents
```

## Project Structure

```
adk-gke/
├── investment_analyst/
│   ├── agents/
│   │   ├── agent.py          # all agent definitions and orchestration
│   │   └── __init__.py
│   ├── callback_logging.py   # Cloud Logging hooks for observability
│   └── requirements.txt
└── README.md
```

## Key Dependencies

| Package | Version | Purpose |
|---|---|---|
| `google-adk` | 1.27.5 | Agent Development Kit |
| `langchain-community` | 0.4.1 | Wikipedia tool wrapper |
| `wikipedia` | 1.4.0 | Wikipedia API |
| `fastapi` / `uvicorn` | latest | ADK web server |

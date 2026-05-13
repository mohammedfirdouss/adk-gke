# ADK Investment Analyst — Claude Code Config

## Project

- **GitHub repo**: github.com/<your-username>/adk-gke
- **GCP project**: <your-project-id>
- **Region**: <your-region>
- **Artifact Registry**: investment-repo
- **GKE cluster**: adk-cluster (Autopilot)

## Structure

```
investment_analyst/
├── agents/agent.py     # all agent definitions
├── main.py             # FastAPI entry point
├── Dockerfile
├── deployment.yaml     # envsubst variables — run: envsubst < deployment.yaml | kubectl apply -f -
├── hpa.yaml
└── requirements.txt
```

## MCP

The `gcloud` MCP server is configured in `~/.claude/settings.json` using `@google-cloud/gcloud-mcp`. It uses your existing `gcloud auth` session — no extra setup. Restart Claude Code to activate after any config changes.

## Environment

Set before any gcloud/kubectl commands (see `set_env.txt` for values):

```bash
export GOOGLE_CLOUD_PROJECT=<your-project-id>
export GOOGLE_CLOUD_LOCATION=<your-region>
export GOOGLE_GENAI_USE_VERTEXAI=true
export MODEL=<your-model>
```

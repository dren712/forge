# FORGE REST & Streaming API Reference

## Endpoints

### Experiments
- `POST /api/experiments`: Create new evolution experiment.
- `GET /api/experiments`: List all experiments with generation counts and best scores.
- `GET /api/experiments/{id}`: Fetch experiment metadata.

### Evolution Lifecycle
- `POST /api/experiments/{id}/generate`: Trigger architect to generate baseline G0 AgentSpec.
- `POST /api/experiments/{id}/run`: Run benchmark tasks on specified or current generation.
- `POST /api/experiments/{id}/evolve`: Execute full evolution cycle (Failure analysis -> Mutation -> Candidate -> Acceptance).

### Generations & Traces
- `GET /api/experiments/{id}/generations`: List generational lineage.
- `GET /api/generations/{id}`: Inspect full AgentSpec, mutation diff, and execution stats.
- `GET /api/experiments/{id}/executions`: List task executions and outcomes.
- `GET /api/experiments/{id}/events`: Retrieve tamper-evident trace event list.
- `GET /api/experiments/{id}/provenance`: Verify cryptographic SHA-256 hash chain.

### Live Streaming
- `GET /api/experiments/{id}/stream`: Server-Sent Events (SSE) streaming real-time execution events to web clients.

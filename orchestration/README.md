# Orchestration example

`prefect_flow.py` re-expresses the same pipeline as `run_baseline.py` as a
[Prefect](https://www.prefect.io/) flow instead of a linear script. See the
module docstring for what that buys you (per-task retries, a visible task
graph, parametrized runs) and the main README's "Docker & other
orchestration options" section for when it's actually worth the extra
moving part versus the simpler cron-based setup this project uses by
default.

## Run it

```bash
pip install -r orchestration/requirements.txt
python orchestration/prefect_flow.py
```

This runs against an ephemeral local Prefect server (no setup needed) and
writes `output/report.md` + `output/report.json`, same as
`run_baseline.py`.

## Schedule it for real

Requires a running Prefect server (`prefect server start`) or a free
[Prefect Cloud](https://www.prefect.io/cloud) account:

```bash
prefect deployment build orchestration/prefect_flow.py:collision_risk_flow \
    --name live-4h --cron "0 */4 * * *"
prefect deployment apply collision_risk_flow-deployment.yaml
prefect agent start -q default
```

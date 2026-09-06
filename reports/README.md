# Live reports

This folder is populated automatically by `.github/workflows/live-monitor.yml`,
which runs every 4 hours (Celestrak's own data refresh cadence — see
`src/live_fetch.py` for why running more often wouldn't help), fetches the
current "stations" group TLE catalog, and re-runs the baseline against it.

- `latest.md` — always the most recent run's report.
- `<timestamp>.md` — a snapshot from that specific run, kept for history.

You can also trigger a run manually from the repo's Actions tab
("Live monitor" workflow → "Run workflow") instead of waiting for the
schedule.

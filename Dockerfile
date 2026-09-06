# Slim, single-stage image — this pipeline has no compiled extensions that
# benefit from a multi-stage build, and the dependency set (skyfield, numpy,
# scikit-learn, scipy) is modest.
FROM python:3.12-slim

WORKDIR /app

# Install dependencies first so Docker's layer cache skips this step on
# code-only changes (only re-runs when requirements.txt actually changes).
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src/
COPY run_baseline.py .
COPY data/ ./data/
RUN mkdir -p /app/output

# Not baked in: run as a non-root user for defense in depth.
RUN useradd --create-home appuser && chown -R appuser:appuser /app
USER appuser

# Default: run the static sample. Override at `docker run` time, e.g.:
#   docker run --rm orbital-collision-agent --live --live-group stations
ENTRYPOINT ["python", "run_baseline.py"]
CMD ["--input", "data/sample_catalog.tle", "--output", "/app/output/report.md"]

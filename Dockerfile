FROM python:3.12-slim-bookworm AS base

RUN useradd --create-home --uid 10001 truthexpiry
WORKDIR /app

COPY pyproject.toml requirements.txt ./
COPY truthexpiry ./truthexpiry
COPY adapters ./adapters
COPY listeners ./listeners
COPY agent ./agent
COPY app.py ./

RUN pip install --no-cache-dir -U pip && pip install --no-cache-dir -e .

USER truthexpiry
EXPOSE 8080 9090
STOPSIGNAL SIGTERM
ENTRYPOINT ["python", "app.py"]
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)" || exit 1

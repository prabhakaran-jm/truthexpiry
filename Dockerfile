FROM python:3.12-slim-bookworm AS builder

WORKDIR /build
RUN pip install --no-cache-dir -U pip build

COPY pyproject.toml requirements.txt README.md ./
COPY truthexpiry ./truthexpiry
COPY adapters ./adapters
COPY listeners ./listeners
COPY agent ./agent
COPY lifecycle_mcp ./lifecycle_mcp
COPY app.py ./

RUN python -m build --wheel --outdir /wheels

FROM python:3.12-slim-bookworm AS runtime

RUN useradd --create-home --uid 10001 truthexpiry
WORKDIR /app

COPY --from=builder /wheels /wheels
COPY --from=builder /build/app.py /app/app.py
RUN pip install --no-cache-dir -U pip && \
    pip install --no-cache-dir /wheels/*.whl && \
    rm -rf /wheels

USER truthexpiry
EXPOSE 8080 9090
STOPSIGNAL SIGTERM
ENTRYPOINT ["python", "app.py"]
HEALTHCHECK CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/healthz', timeout=2)" || exit 1

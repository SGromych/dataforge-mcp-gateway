FROM python:3.11-slim AS builder

WORKDIR /app
COPY pyproject.toml .
# pyproject declares readme = "README.md"; without it the metadata step of
# `pip install .` dies with OSError: Readme file does not exist.
COPY README.md .
COPY src/ src/
RUN pip install --no-cache-dir .

FROM python:3.11-slim

WORKDIR /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
# No second copy of src/: the entrypoint runs the installed package from
# site-packages, and a stale copy next to it only confuses a traceback.
COPY docker/healthcheck.py /app/docker/healthcheck.py

# The HTTP transports listen here. Ignored when MCP_TRANSPORT=stdio.
EXPOSE 8080

# /health is served by both HTTP transports and is exempt from bearer auth,
# so this works unchanged when MCP_AUTH_TOKEN is set.
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD ["python", "/app/docker/healthcheck.py"]

ENTRYPOINT ["python", "-m", "dataforge_mcp"]

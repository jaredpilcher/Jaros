# Jaros runs as a long-running daemon (the OS) inside one container = one node.
# Agents are threads inside it; work + plugins arrive only via the /data volume.
FROM python:3.12-slim

WORKDIR /app

# Install the package (no runtime deps beyond the stdlib).
COPY pyproject.toml README.md ./
COPY jaros ./jaros
RUN pip install --no-cache-dir .

# Non-root user; /data is the shared file system (mount a host volume here).
RUN useradd --create-home jaros \
    && mkdir -p /data \
    && chown -R jaros:jaros /data /app
USER jaros

ENV JAROS_DATA_DIR=/data \
    JAROS_TICK_MS=500 \
    JAROS_LLM_PROVIDER=default

VOLUME ["/data"]

# Boot the OS and keep it running. Watch with: docker logs -f <container>
CMD ["jaros", "serve"]

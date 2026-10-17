FROM node:22-bookworm-slim
# Node.js runs the synthetic health check (monitor/healthcheck.mjs); git for fix branches; Python for the agent.
RUN apt-get update && apt-get install -y --no-install-recommends git python3 python3-pip ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && pip3 install --no-cache-dir --break-system-packages anthropic redis==5.2.1
WORKDIR /app
COPY services/agent/app.py .
ENV GIT_AUTHOR_NAME="Self-healing agent" GIT_AUTHOR_EMAIL="agent@freitags.example" \
    GIT_COMMITTER_NAME="Self-healing agent" GIT_COMMITTER_EMAIL="agent@freitags.example"
EXPOSE 8002
CMD ["python3", "-u", "app.py"]

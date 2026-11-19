# Staging only: the real publish agent (publish_agent/) in a container, so the homelab stack publishes the way the
# campus PC will: it polls https://<CMS host> through Cloudflare, uploads over SFTP to the `sftp` stand-in, and
# checks the public URL. Build context: the repository root (Dockerfile.dockerignore keeps it to publish_agent/).
# Runs as the host user (docker-compose.staging.yml `user:`) so it can read its 0600 key and secret files in
# deploy/staging/secrets/agent, mounted at /agent.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/opt/agent \
    HOME=/tmp \
    CRTDH_AGENT_CONFIG=/agent/config.ini

WORKDIR /opt/agent
COPY publish_agent/requirements.txt /tmp/agent-requirements.txt
RUN pip install --no-cache-dir --require-hashes -r /tmp/agent-requirements.txt && rm /tmp/agent-requirements.txt
COPY publish_agent/ /opt/agent/publish_agent/

WORKDIR /agent
ENTRYPOINT ["python", "-m", "publish_agent"]
CMD ["run"]

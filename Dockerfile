FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /action

# ripgrep is needed by the grep_code tool
RUN apt-get update && apt-get install -y --no-install-recommends \
    ripgrep git curl \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./
COPY src ./src
RUN pip install --upgrade pip && pip install -e .

# Entrypoint reads PR diff from GitHub and dispatches to the agent
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh
ENTRYPOINT ["/entrypoint.sh"]

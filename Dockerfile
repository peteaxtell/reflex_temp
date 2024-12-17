FROM python:3.13

RUN apt-get update && apt-get install -y redis-server && rm -rf /var/lib/apt/lists/*
ENV REDIS_URL=redis://localhost PYTHONUNBUFFERED=1

WORKDIR /app
COPY src/ .
COPY requirements.txt .

RUN pip install -r requirements.txt

# Deploy templates and prepare app
RUN reflex init

# Download all npm dependencies and compile frontend
RUN reflex export --frontend-only --no-zip

# Needed until Reflex properly passes SIGTERM on backend.
STOPSIGNAL SIGKILL

# Always apply migrations before starting the backend.
CMD redis-server --daemonize yes && \
    exec reflex run --env prod
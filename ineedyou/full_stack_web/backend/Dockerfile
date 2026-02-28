FROM python:3.9-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app

# Install netcat and dos2unix
RUN apt-get update && apt-get install -y netcat-traditional dos2unix && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/
RUN pip install --upgrade pip && \
    pip install -r requirements.txt

COPY . /app/

# Convert line endings of entrypoint.sh to LF (Unix format) to fix Windows execution issues
RUN dos2unix /app/entrypoint.sh && chmod +x /app/entrypoint.sh

# Use entrypoint script to handle migrations and user creation
ENTRYPOINT ["/app/entrypoint.sh"]

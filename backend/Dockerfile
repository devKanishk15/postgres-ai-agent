# Stage 1: Grab only the Docker CLI binary
FROM docker:27-cli AS docker-cli

# Stage 2: Build the app
FROM python:3.11-slim

WORKDIR /app

# Copy just the Docker CLI (~50MB vs ~400MB for docker.io)
COPY --from=docker-cli /usr/local/bin/docker /usr/local/bin/docker

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

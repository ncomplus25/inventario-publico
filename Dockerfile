# Python slim image
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends     build-essential     && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8080

ENV PORT=8080
ENV ALLOWED_ORIGINS=*
ENV ADMIN_TOKEN=changeme

CMD exec gunicorn --bind 0.0.0.0:${PORT} --workers 2 --threads 4 app_public:app
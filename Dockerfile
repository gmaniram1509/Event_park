# ── Base image ────────────────────────────────────────────
FROM python:3.12-slim

# Set working directory inside container
WORKDIR /app

# Prevents Python from writing .pyc files
ENV PYTHONDONTWRITEBYTECODE=1
# Prevents Python from buffering stdout/stderr
ENV PYTHONUNBUFFERED=1

# ── Install system dependencies ───────────────────────────
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ── Install Python dependencies ───────────────────────────
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# ── Copy application code ─────────────────────────────────
COPY . .

# ── Collect static files ──────────────────────────────────
RUN python manage.py collectstatic --noinput || true

# ── Expose port ───────────────────────────────────────────
EXPOSE 8000

# ── Start Django with gunicorn (production server) ────────
CMD ["sh", "-c", "python manage.py migrate --run-syncdb && gunicorn eventpark.wsgi:application --bind 0.0.0.0:8000 --workers 3"]

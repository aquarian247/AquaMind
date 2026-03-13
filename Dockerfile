FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    DJANGO_SETTINGS_MODULE=aquamind.settings

WORKDIR /app

# Install Python dependencies for the production-style runtime image.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn==23.0.0

# Copy application source. The build context is intentionally trimmed by
# .dockerignore so we only ship runtime assets needed by AquaMind.
COPY . .

RUN useradd -ms /bin/bash appuser \
    && mkdir -p /app/staticfiles /app/media \
    && chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "aquamind.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3", "--timeout", "120"]

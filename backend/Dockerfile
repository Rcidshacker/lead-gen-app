FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH="/scraper:${PYTHONPATH}"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget gnupg \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright chromium
RUN playwright install chromium --with-deps

# Copy app code
COPY . .

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

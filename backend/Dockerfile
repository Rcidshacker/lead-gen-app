FROM python:3.11-slim

WORKDIR /app

ENV PYTHONPATH="/scraper:${PYTHONPATH}"

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential curl wget gnupg \
    fonts-unifont fonts-noto-core \
    libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libdrm2 \
    libxkbcommon0 libxcomposite1 libxdamage1 libxfixes3 libxrandr2 \
    libgbm1 libpango-1.0-0 libcairo2 \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps
COPY backend/requirements.txt .
COPY scraper/requirements.txt scraper_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r scraper_requirements.txt

# Install Playwright chromium (without --with-deps; deps installed above)
RUN playwright install chromium

# Copy app code
COPY backend .
COPY scraper /scraper

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

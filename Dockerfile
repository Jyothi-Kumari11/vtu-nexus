FROM python:3.10-slim-bookworm

ENV DEBIAN_FRONTEND=noninteractive

# Install system deps + Google Chrome in one layer
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       wget gnupg ca-certificates fonts-liberation \
       libnss3 libatk-bridge2.0-0 libgtk-3-0 libasound2 \
       libxcomposite1 libxdamage1 libxrandr2 libgbm1 libpango-1.0-0 \
       libcairo2 libcups2 libdbus-1-3 libxkbcommon0 xdg-utils \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5000

CMD ["python", "app.py"]

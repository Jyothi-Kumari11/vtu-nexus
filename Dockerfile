# Use python 3.10 slim as base image
FROM python:3.10-slim

# Install system dependencies, Google Chrome, and clean up temporary files
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    unzip \
    gnupg \
    libgconf-2-4 \
    libnss3 \
    libxss1 \
    libasound2 \
    libatk-bridge2.0-0 \
    libgtk-3-0 \
    --no-install-recommends \
    && wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Set working directory inside container
WORKDIR /app

# Copy all project files into the container
COPY . .

# Install required Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Expose port 5000 for web traffic
EXPOSE 5000

# Start Flask using Waitress (Production Web Server) instead of debug mode
CMD ["python", "app.py"]

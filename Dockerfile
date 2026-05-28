FROM python:3.10-slim
WORKDIR /app
COPY . /app
RUN apt-get update && apt-get install -y curl gnupg ca-certificates libnss3 libatk1.0-0 libatk-bridge2.0-0 libcups2 libxcomposite1 libxrandr2 libxdamage1 libgbm1 libasound2 libpangocairo-1.0-0 libgtk-3-0 wget --no-install-recommends && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt
# Install Playwright and browsers
RUN python -m pip install playwright && python -m playwright install --with-deps chromium || true
EXPOSE 8000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]

FROM mcr.microsoft.com/playwright/python:v1.53.0-jammy

WORKDIR /app

COPY . .

# Installiere Python-Abhängigkeiten
RUN pip install --no-cache-dir -r requirements.txt

# Installiere Browser + alle System-Dependencies für Playwright
RUN playwright install --with-deps

EXPOSE 5000

CMD ["python", "app.py"]

FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Los datos (registro + fotos) viven en PostgreSQL: aporta DATABASE_URL como variable de entorno.
# El Procfile arranca el mismo comando en plataformas tipo Heroku/Nixpacks; este Dockerfile es una alternativa.
ENV PORT=8000
EXPOSE 8000

CMD ["sh", "-c", "uvicorn server:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips=*"]

FROM python:3.12-slim

# Instala dependências do sistema para Playwright e PostgreSQL
RUN apt-get update && apt-get install -y \
    wget curl git \
    libpq-dev gcc \
    # Dependências do Chromium/Playwright
    libnss3 libnspr4 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libgbm1 \
    libasound2 libxshmfence1 libgles2 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copia e instala dependências Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Instala Playwright e o browser Chromium
RUN playwright install chromium --with-deps

# Copia código da aplicação
COPY . .

# Cria pastas de runtime
RUN mkdir -p logs screenshots

# Porta da aplicação
EXPOSE 8000

# Comando de inicialização
CMD ["sh", "-c", "alembic upgrade head && python -m miles_radar.main"]

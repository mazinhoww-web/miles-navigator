#!/bin/bash
# setup-production.sh — Hardening de produção para Miles Radar
# Configura: Nginx reverse proxy + Certbot (HTTPS) + backup automático + logs de produção
#
# Uso: sudo bash setup-production.sh
# Pré-requisito: sistema já rodando com docker compose up -d
# Pré-requisito: ter um domínio apontando para o IP do servidor (opcional para HTTPS)

set -e

DOMAIN="${1:-}"                  # Ex: radar.meucdominio.com.br
APP_PORT="8000"
EVOLUTION_PORT="8080"
BACKUP_DIR="/opt/milesradar-backups"
APP_DIR="/home/ubuntu/miles-radar-app"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== Miles Radar — Setup de Produção ===${NC}"
echo ""

# ── 1. Firewall UFW ──────────────────────────────────────────────────────────
echo -e "${YELLOW}[1/5] Configurando firewall UFW...${NC}"
apt-get install -y ufw -q
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow "$APP_PORT/tcp"
ufw allow "$EVOLUTION_PORT/tcp"
echo "y" | ufw enable
echo -e "${GREEN}    UFW configurado${NC}"

# ── 2. Nginx ─────────────────────────────────────────────────────────────────
echo -e "${YELLOW}[2/5] Instalando e configurando Nginx...${NC}"
apt-get install -y nginx -q
systemctl enable nginx

if [ -n "$DOMAIN" ]; then
    # Config com domínio
    cat > /etc/nginx/sites-available/milesradar << NGINX_CONF
server {
    listen 80;
    server_name $DOMAIN;

    # Redireciona para HTTPS (após certbot configurar)
    location /.well-known/acme-challenge/ {
        root /var/www/html;
    }

    location / {
        return 301 https://\$host\$request_uri;
    }
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL será configurado pelo Certbot
    # ssl_certificate e ssl_certificate_key adicionados pelo certbot

    # Segurança
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-XSS-Protection "1; mode=block" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "no-referrer-when-downgrade" always;

    # Gzip
    gzip on;
    gzip_types text/plain application/json text/html text/css application/javascript;

    # Dashboard Miles Radar
    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        proxy_read_timeout 120s;
    }

    # Evolution API (restrito por IP se necessário)
    location /evolution/ {
        proxy_pass http://127.0.0.1:$EVOLUTION_PORT/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }
}
NGINX_CONF

    ln -sf /etc/nginx/sites-available/milesradar /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    echo -e "${GREEN}    Nginx configurado para domínio: $DOMAIN${NC}"
else
    # Config sem domínio (acesso por IP)
    cat > /etc/nginx/sites-available/milesradar << NGINX_CONF
server {
    listen 80 default_server;
    listen [::]:80 default_server;

    location / {
        proxy_pass http://127.0.0.1:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_read_timeout 120s;
    }
}
NGINX_CONF

    ln -sf /etc/nginx/sites-available/milesradar /etc/nginx/sites-enabled/
    rm -f /etc/nginx/sites-enabled/default
    nginx -t && systemctl reload nginx
    echo -e "${GREEN}    Nginx configurado (sem domínio — acesso por IP)${NC}"
fi

# ── 3. Certbot (HTTPS) ───────────────────────────────────────────────────────
if [ -n "$DOMAIN" ]; then
    echo -e "${YELLOW}[3/5] Configurando HTTPS com Certbot...${NC}"
    apt-get install -y certbot python3-certbot-nginx -q
    certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos \
        --email "admin@$DOMAIN" --redirect || echo -e "${YELLOW}    Certbot falhou — configure manualmente após verificar DNS${NC}"
    # Renovação automática (Certbot já configura via cron/systemd)
    echo -e "${GREEN}    HTTPS configurado para https://$DOMAIN${NC}"
else
    echo -e "${YELLOW}[3/5] Sem domínio — pulando Certbot${NC}"
    echo "    Para adicionar HTTPS depois: sudo certbot --nginx -d SEU_DOMINIO"
fi

# ── 4. Backup automático ─────────────────────────────────────────────────────
echo -e "${YELLOW}[4/5] Configurando backup automático do banco...${NC}"
mkdir -p "$BACKUP_DIR"
chmod 700 "$BACKUP_DIR"

# Script de backup
cat > /usr/local/bin/milesradar-backup.sh << 'BACKUP_SCRIPT'
#!/bin/bash
set -e
BACKUP_DIR="/opt/milesradar-backups"
APP_DIR="/home/ubuntu/miles-radar-app"
DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/milesradar_$DATE.sql.gz"

# Carrega variáveis de ambiente
source "$APP_DIR/.env" 2>/dev/null || true

# Executa backup via docker
docker exec miles_postgres pg_dump "$DATABASE_URL" 2>/dev/null | \
    gzip > "$BACKUP_FILE" || \
    docker exec miles_postgres pg_dumpall -U milesradar | gzip > "$BACKUP_FILE"

# Remove backups com mais de 7 dias
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete

# Log
echo "$(date): Backup criado: $BACKUP_FILE ($(du -sh $BACKUP_FILE | cut -f1))" \
    >> "$BACKUP_DIR/backup.log"
BACKUP_SCRIPT
chmod +x /usr/local/bin/milesradar-backup.sh

# Cron job: 03:00 todos os dias
CRON_ENTRY="0 3 * * * /usr/local/bin/milesradar-backup.sh >> /opt/milesradar-backups/cron.log 2>&1"
(crontab -l 2>/dev/null | grep -v milesradar-backup; echo "$CRON_ENTRY") | crontab -
echo -e "${GREEN}    Backup automático: todo dia às 03:00 → $BACKUP_DIR (retenção 7 dias)${NC}"

# ── 5. Auto-restart no boot ──────────────────────────────────────────────────
echo -e "${YELLOW}[5/5] Configurando auto-start no boot...${NC}"
cat > /etc/systemd/system/milesradar.service << SYSTEMD
[Unit]
Description=Miles Radar — Monitor de Campanhas de Milhas
Requires=docker.service
After=docker.service network.target

[Service]
Type=simple
User=ubuntu
WorkingDirectory=$APP_DIR
ExecStart=/usr/bin/docker compose up
ExecStop=/usr/bin/docker compose down
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
SYSTEMD

systemctl daemon-reload
systemctl enable milesradar.service
echo -e "${GREEN}    Serviço milesradar.service habilitado${NC}"

# ── Resumo ───────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}=== Setup concluído! ===${NC}"
echo ""
echo "Dashboard:    http://${DOMAIN:-SEU_IP}/"
[ -n "$DOMAIN" ] && echo "HTTPS:        https://$DOMAIN/"
echo "Evolution:    http://${DOMAIN:-SEU_IP}:$EVOLUTION_PORT/docs"
echo "Backups:      $BACKUP_DIR"
echo "Logs:         docker compose -f $APP_DIR/docker-compose.yml logs -f app"
echo ""
echo "Comandos úteis:"
echo "  sudo systemctl status milesradar    — status do serviço"
echo "  /usr/local/bin/milesradar-backup.sh — forçar backup agora"
echo "  certbot renew --dry-run             — testar renovação SSL"

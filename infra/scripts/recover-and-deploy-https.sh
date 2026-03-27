#!/bin/bash
# ============================================================
# KT Monetization OS — Recovery + HTTPS Deploy Script
# Run ONCE after VPS recovery to restore everything
# Usage: bash /opt/kt-monetization-os/infra/scripts/recover-and-deploy-https.sh
# ============================================================
set -e
DOMAIN="tkverse.ca"
APP_DIR="/opt/kt-monetization-os"

echo "══════════════════════════════════════════"
echo "  KT Recovery + HTTPS Deploy"
echo "══════════════════════════════════════════"

# ── STEP 1: Kill nftables permanently ───────────────────────
echo "[1/8] Removing nftables..."
systemctl stop nftables 2>/dev/null || true
systemctl disable nftables 2>/dev/null || true
nft flush ruleset 2>/dev/null || true
apt-get remove -y nftables 2>/dev/null | tail -1 || true
echo "  OK nftables removed permanently"

# ── STEP 2: Restore UFW + iptables ──────────────────────────
echo "[2/8] Restoring firewall..."
iptables -P INPUT ACCEPT
iptables -P FORWARD ACCEPT
ufw --force enable
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw deny 8020/tcp
ufw deny 9091/tcp
ufw reload
echo "  OK UFW restored — SSH/HTTP/HTTPS open"

# ── STEP 3: Restore security services ───────────────────────
echo "[3/8] Restarting security services..."
for svc in fail2ban crowdsec kt-spy-agent kt-watchdog; do
    systemctl start $svc 2>/dev/null && echo "  OK $svc" || echo "  SKIP $svc"
done

# ── STEP 4: Fix .env for domain-based URLs ──────────────────
echo "[4/8] Updating .env for https://$DOMAIN..."
cd $APP_DIR

if grep -q "NEXT_PUBLIC_API_URL" .env; then
    sed -i "s|NEXT_PUBLIC_API_URL=.*|NEXT_PUBLIC_API_URL=https://api.$DOMAIN|g" .env
else
    echo "NEXT_PUBLIC_API_URL=https://api.$DOMAIN" >> .env
fi

if grep -q "^DOMAIN=" .env; then
    sed -i "s|^DOMAIN=.*|DOMAIN=$DOMAIN|g" .env
else
    echo "DOMAIN=$DOMAIN" >> .env
fi

if grep -q "ALLOWED_ORIGINS" .env; then
    sed -i "s|ALLOWED_ORIGINS=.*|ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN,https://app.$DOMAIN,https://api.$DOMAIN|g" .env
else
    echo "ALLOWED_ORIGINS=https://$DOMAIN,https://www.$DOMAIN,https://app.$DOMAIN,https://api.$DOMAIN" >> .env
fi

sed -i '/ACME_EMAIL/d' .env
echo "ACME_EMAIL=admin@$DOMAIN" >> .env
echo "  OK .env updated"

# ── STEP 5: Pull latest code ─────────────────────────────────
echo "[5/8] Pulling latest code from GitHub..."
cd $APP_DIR
git pull origin main 2>&1 | tail -3
chmod +x infra/scripts/*.sh 2>/dev/null || true
echo "  OK Code updated ($(git rev-parse --short HEAD))"

# ── STEP 6: Check DNS ────────────────────────────────────────
echo "[6/8] Checking DNS for $DOMAIN..."
apt-get install -y dnsutils 2>/dev/null | tail -1 || true
RESOLVED=$(dig +short $DOMAIN @8.8.8.8 2>/dev/null | tail -1)
if [ "$RESOLVED" = "167.114.155.166" ]; then
    echo "  OK DNS: $DOMAIN -> $RESOLVED"
    DNS_OK=true
else
    echo "  WARN DNS not ready ($RESOLVED) — Caddy auto-issues cert once DNS propagates"
    DNS_OK=false
fi

# ── STEP 7: Rebuild + restart all containers ────────────────
echo "[7/8] Rebuilding and restarting containers..."
cd $APP_DIR
docker compose -f infra/docker-compose.prod.yml --env-file .env up -d --remove-orphans 2>&1 | tail -8
sleep 8
echo "  OK Containers started"

# ── STEP 8: Final status ─────────────────────────────────────
echo "[8/8] Final status..."
echo ""
for svc in ufw fail2ban crowdsec kt-spy-agent kt-watchdog; do
    STATUS=$(systemctl is-active $svc 2>/dev/null || echo "inactive")
    [ "$STATUS" = "active" ] && echo "  OK $svc" || echo "  ERR $svc"
done
echo ""
docker ps --format "  {{.Names}} {{.Status}}" 2>/dev/null
echo ""
echo "  NEXT_PUBLIC_API_URL=$(grep NEXT_PUBLIC_API_URL .env | cut -d= -f2)"
echo "  DOMAIN=$(grep '^DOMAIN=' .env | cut -d= -f2)"
echo ""
if [ "$DNS_OK" = true ]; then
    echo "LIVE: https://$DOMAIN"
    echo "LIVE: https://api.$DOMAIN"
    echo "LIVE: https://admin.$DOMAIN"
    echo "LIVE: https://monitor.$DOMAIN"
else
    echo "Add A records in OVH DNS:"
    echo "  tkverse.ca         -> 167.114.155.166"
    echo "  api.tkverse.ca     -> 167.114.155.166"
    echo "  app.tkverse.ca     -> 167.114.155.166"
    echo "  admin.tkverse.ca   -> 167.114.155.166"
    echo "  monitor.tkverse.ca -> 167.114.155.166"
    echo "  www.tkverse.ca     -> 167.114.155.166"
fi
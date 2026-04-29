# RUNBOOK — Nanovia OS

## Prérequis Locaux

- Python 3.12+ (3.14 confirmé présent)
- Node.js 18+
- PostgreSQL 16 OU SQLite (dev)
- Redis (ou skip si indisponible — fail open)
- Stripe CLI (optionnel, pour tester les webhooks)

---

## 1. Setup Backend (FastAPI)

### Installer les dépendances
```powershell
cd C:\Users\Alienware\kt-monetization-os
pip install -r backend/requirements.txt
```

### Configurer l'env
```powershell
# Copier le template racine si nécessaire :
# Copy-Item .env.example .env
#
# Vérifier surtout :
# APP_ENV, DATABASE_URL, JWT_SECRET_KEY, STRIPE_SECRET_KEY,
# PUBLIC_WEB_URL, PRIVATE_ADMIN_URL, ADMIN_ALLOWED_IPS
# Pour dev SQLite rapide :
# DATABASE_URL=sqlite+aiosqlite:///./dev.db
```

### Lancer l'API (dev)
```powershell
cd C:\Users\Alienware\kt-monetization-os
$env:PYTHONPATH = "backend"
uvicorn api.main:app --reload --host 127.0.0.1 --port 8010
```

### Vérifier /health
```powershell
Invoke-WebRequest -Uri "http://localhost:8010/health" | Select-Object -ExpandProperty Content
# Attendu: {"status":"ok",...}
```

### Vérifier /docs (Swagger)
Ouvrir dans un navigateur : http://localhost:8010/docs

---

## 2. Setup Frontend (Next.js Web)

### Installer les dépendances
```powershell
cd C:\Users\Alienware\kt-monetization-os\frontend\client
npm install
```

### Configurer l'env frontend
```powershell
# Créer frontend\client\.env.local si nécessaire :
# NEXT_PUBLIC_API_URL=http://127.0.0.1:8010
# NEXT_PUBLIC_PRIVATE_ORCHESTRATOR_ENABLED=false
```

### Lancer le frontend
```powershell
npm run dev
# Ouvre : http://localhost:3000
```

### Build de production
```powershell
npm run build
npm run start
```

---

## 3. Setup Stripe (local webhook forwarding)

### Installer Stripe CLI
```powershell
# Windows : https://stripe.com/docs/stripe-cli
# Ou via scoop : scoop install stripe
```

### Écouter les webhooks en local
```powershell
stripe listen --forward-to localhost:8010/api/v1/billing/webhook
# Copier le "webhook signing secret" (stripe_webhook_...) dans .env → STRIPE_WEBHOOK_SECRET
```

### Tester un paiement test
```powershell
stripe trigger checkout.session.completed
```

---

## 4. Bootstrap Stripe (créer produits/prix — 1 fois)

```powershell
cd C:\Users\Alienware\kt-monetization-os
python stripe/setup_stripe.py
# → Génère stripe/stripe_ids.json avec les IDs
# → Copier les price_ids dans .env
```

---

## 5. Démarrage Complet (Docker — prod)

```powershell
cd C:\Users\Alienware\kt-monetization-os

# Production public stack
Copy-Item infra\env\.env.example .env.production
python scripts\validate_runtime_env.py --env-file .env.production --target-env production
docker compose -p nanovia-prod -f infra\docker-compose.prod.yml --env-file .env.production up -d

# Staging isolé sur le même VPS (ports loopback + pas de Caddy)
Copy-Item infra\env\.env.staging.example .env.staging
python scripts\validate_runtime_env.py --env-file .env.staging --target-env staging
docker compose -p nanovia-staging -f infra\docker-compose.prod.yml -f infra\docker-compose.staging.yml --env-file .env.staging up -d

# Vérifier :
docker compose ps
```

### Déploiement GitHub Actions (OVH)

- `main` => environnement GitHub `production`
- `staging` => environnement GitHub `staging`
- `APP_RUNTIME_ENV_FILE` doit pointer vers le bon fichier (`../.env.production`, `../.env.staging` ou `../.env` legacy)
- Le préflight `scripts\validate_runtime_env.py` bloque maintenant les placeholders restants, l'absence de `TOTP_ENCRYPTION_KEY` et l'oubli de l'allowlist admin en production.
- Secrets attendus par environnement :
  - `VPS_HOST`
  - `VPS_SSH_PRIVATE_KEY`
  - `DEPLOY_PATH`
- Variables utiles :
  - `APP_DOMAIN`, `PUBLIC_IP`
  - `STAGING_BIND_ADDRESS`, `STAGING_WEB_PORT`, `STAGING_ADMIN_PORT`, `STAGING_API_PORT`, `STAGING_AI_PORT`
- Garde-fous actuels du workflow :
  - `production` exige `STRIPE_SECRET_KEY=stripe_live_...`
  - `staging` refuse les clés Stripe live
  - `APP_RUNTIME_ENV_FILE` est réécrit vers `../.env.production` ou `../.env.staging`

### Accès staging recommandé

```powershell
ssh -L 13000:127.0.0.1:13000 -L 13020:127.0.0.1:13020 -L 18010:127.0.0.1:18010 deploy@VPS_HOST
```

- Web staging : `http://127.0.0.1:13000`
- Admin staging : `http://127.0.0.1:13020`
- API staging : `http://127.0.0.1:18010`
- Garder Stripe en `stripe_test_...` / `stripe_public_test_...` / `stripe_webhook_...`
- En production, le frontend admin reste un service séparé mais n'est pas publié publiquement par le `Caddyfile` par défaut.

---

## 6. Check Santé Rapide

```powershell
# API backend
Invoke-WebRequest -Uri "http://localhost:8010/health" -ErrorAction SilentlyContinue | Select-Object StatusCode, Content

# API ready (check DB + Redis)
Invoke-WebRequest -Uri "http://localhost:8010/api/v1/health/ready" -ErrorAction SilentlyContinue | Select-Object StatusCode, Content

# Frontend
Invoke-WebRequest -Uri "http://localhost:3000" -ErrorAction SilentlyContinue | Select-Object StatusCode

# Script de vérification intégré
python scripts/check_health.py
```

---

## 7. Variables d'Env Critiques à Vérifier

```
DATABASE_URL          → doit pointer vers postgres (prod) ou sqlite (dev)
JWT_SECRET_KEY        → doit être long et aléatoire
STRIPE_SECRET_KEY     → stripe_test_... (dev) ou stripe_live_... (prod)
STRIPE_WEBHOOK_SECRET → stripe_webhook_... (obtenu via stripe listen ou dashboard)
PUBLIC_WEB_URL        → URL publique utilisée pour Stripe/email
PRIVATE_ADMIN_URL     → URL/admin origin privé
APP_RUNTIME_ENV_FILE  → ../.env.production ou ../.env.staging en Docker
ADMIN_ALLOWED_IPS     → CIDR(s) autorisés pour /api/v1/admin/*
PRIVATE_ORCHESTRATOR_ENABLED      → true uniquement si le slice admin privé doit répondre
NEXT_PUBLIC_PRIVATE_ORCHESTRATOR_ENABLED → true uniquement pour afficher l'UI admin
STRIPE_PRICE_PRO_MONTHLY_ID   → value from stripe/stripe_ids.json or Stripe dashboard
STRIPE_PRICE_PRO_YEARLY_ID    → price_...
STRIPE_PRICE_BUSINESS_MONTHLY_ID → value from stripe/stripe_ids.json or Stripe dashboard
STRIPE_PRICE_BUSINESS_YEARLY_ID  → price_...
```

---

## 8. Commandes Utiles

```powershell
# Voir les logs API (si démarré en arrière-plan)
Get-Content logs\api.log -Tail 50
Get-Content logs\api_err.log -Tail 20

# Tester la config Python
cd C:\Users\Alienware\kt-monetization-os
python -c "import sys; sys.path.insert(0,'backend'); from api.config import settings; print(settings.APP_NAME)"

# Vérifier les routes disponibles
python -c "import sys; sys.path.insert(0,'backend'); from api.main import app; [print(r.path) for r in app.routes]"

# Lister les derniers webhooks Stripe (admin token requis)
curl.exe -H "Authorization: Bearer ADMIN_TOKEN" http://127.0.0.1:8010/api/v1/admin/webhooks

# Rejouer un webhook stocké (forcer si déjà processed)
curl.exe -X POST -H "Authorization: Bearer ADMIN_TOKEN" -H "Content-Type: application/json" `
  -d "{\"force\":true}" http://127.0.0.1:8010/api/v1/admin/webhooks/EVENT_ID/reprocess

# Resynchroniser l'abonnement d'un utilisateur depuis Stripe
curl.exe -X POST -H "Authorization: Bearer ADMIN_TOKEN" `
  http://127.0.0.1:8010/api/v1/admin/users/USER_ID/resync-subscription

# Vérifier le slice private orchestrator (404 si flag off)
curl.exe -H "Authorization: Bearer ADMIN_TOKEN" http://127.0.0.1:8010/api/v1/admin/orchestrator/overview
```

### Notes opérateur

- Le slice private orchestrator reste **admin-only**, **feature-flagged** et **read-only**.
- Flags requis pour le rendre visible :
  - API : `PRIVATE_ORCHESTRATOR_ENABLED=true`
  - Frontend admin : `NEXT_PUBLIC_PRIVATE_ORCHESTRATOR_ENABLED=true`
- Endpoints publiés :
  - `/api/v1/admin/orchestrator/overview`
  - `/api/v1/admin/orchestrator/agents`
- Recovery Stripe :
  - d'abord inspecter `/api/v1/admin/webhooks`
  - ensuite `reprocess`
  - si l'état utilisateur reste incohérent, lancer `resync-subscription`

---

## INCIDENT RESPONSE

### IR-1: Redis Down

**Symptoms:** API starts failing rate-limit checks (fail-open), session operations slow, 500s on billing endpoints that use Redis caching.

**Detection:**
```powershell
kubectl exec -n nanovia deploy/nanovia-api -- redis-cli -u $REDIS_URL ping
# Expected: PONG. If timeout/error → Redis is down.
docker compose -f infra/docker-compose.prod.yml logs redis --tail=50
```

**Remediation:**
1. Check Redis container/pod is running: `kubectl get pods -n nanovia | grep redis`
2. If crashed: `kubectl rollout restart deployment/redis -n nanovia` or `docker compose restart redis`
3. Check disk full (Redis AOF): `df -h /var/lib/redis`
4. If data corrupted: `redis-cli DEBUG RELOAD` — or restore from last AOF snapshot
5. Verify after: `redis-cli ping` returns `PONG`

**Rollback:** Redis is stateless for rate-limiting — loss of rate limit counters is acceptable. Restart is safe.

---

### IR-2: Worker Crash / Zombie

**Symptoms:** Scrape jobs stuck in `pending`, queue depth rising, no job completions in logs.

**Detection:**
```bash
kubectl get pods -n nanovia | grep worker
# Look for CrashLoopBackOff or Restart count > 3
kubectl logs -n nanovia deploy/nanovia-worker --tail=100

# On VPS
ps aux | grep worker.py
```

**Remediation:**
1. Check logs for OOM or exception: `kubectl logs -n nanovia deploy/nanovia-worker --previous`
2. Restart: `kubectl rollout restart deployment/nanovia-worker -n nanovia`
3. If zombie browser processes: `kubectl exec -n nanovia <worker-pod> -- pkill -f chromium`
4. Check memory limits — if OOM: increase worker memory limit in `infra/k8s/base/worker/deployment.yaml`
5. The zombie killer background task (`_zombie_killer` in fetcher.py) auto-closes idle browsers every 5 min

---

### IR-3: Region Outage

**Symptoms:** Requests from a geographic region timing out, CDN/edge returning 502/503.

**Detection:**
```bash
# Check multi-region routing (Cloudflare / AWS Route53 health checks)
curl -I https://nanovia.ca/api/v1/health/ready
# Check from multiple regions via curl --resolve or external uptime monitor
```

**Failover Steps:**
1. Identify affected region via monitoring dashboard (Grafana → geo map)
2. Update DNS/routing to bypass affected region (Cloudflare: disable affected origin)
3. Scale up remaining regions: `kubectl scale deployment nanovia-api --replicas=6 -n nanovia`
4. Open incident channel, notify stakeholders
5. Monitor error rate dropping: Grafana → API error rate panel
6. Once region recovered: restore DNS, scale down extra replicas

---

### IR-4: Queue Saturation

**Symptoms:** Scrape queue depth > 500, jobs completing slowly or not at all, Redis memory high.

**Detection:**
```bash
redis-cli -u $REDIS_URL LLEN scrape:queue
# > 500 = saturation
kubectl get hpa -n nanovia  # check HPA status
```

**Remediation:**
1. **Scale workers immediately:** `kubectl scale deployment nanovia-worker --replicas=8 -n nanovia`
2. Check for stuck jobs: jobs with no worker processing them
3. If queue is poisoned (bad jobs looping): inspect and flush:
   ```bash
   redis-cli -u $REDIS_URL LRANGE scrape:queue 0 10  # inspect
   redis-cli -u $REDIS_URL DEL scrape:queue           # nuclear option — flush all pending
   ```
4. Set HPA max replicas higher in `infra/k8s/base/worker/` if recurring
5. Alert on queue depth > 200 in Prometheus alerts

---

### IR-5: Proxy Failure (All Proxies Dead)

**Symptoms:** All scraping requests returning 403/429, proxy pool shows 0 alive proxies, logs show `[proxy_pool] healthcheck: 0 alive`.

**Detection:**
```bash
# Check API logs
kubectl logs -n nanovia deploy/nanovia-api | grep proxy_pool
# Look for: "[proxy_pool] healthcheck: 0 alive, N dead"
```

**Remediation:**
1. **Fallback to direct:** Set `SCRAPING_PROXY_ROTATION_ENABLED=false` in env, restart API
2. Check proxy provider dashboard for account suspension or IP bans
3. Rotate proxy credentials: update `SCRAPING_PROXY_LIST` in secrets/env
4. Restart API to reload proxy pool: `kubectl rollout restart deployment/nanovia-api -n nanovia`
5. If using stealth mode: verify `SCRAPING_STEALTH_MODE=true` is still appropriate
6. Once new proxies configured: re-enable `SCRAPING_PROXY_ROTATION_ENABLED=true`

---

### IR-6: High Error Rate (> 5%)

**Symptoms:** Grafana alert fires, Prometheus `http_requests_total{status=~"5.."}` rate > 5%.

**Detection:**
```bash
# Prometheus query
rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05

# API logs
kubectl logs -n nanovia deploy/nanovia-api --tail=200 | grep '"level":"ERROR"'
```

**Remediation:**
1. Identify the failing endpoint from logs/metrics (highest 5xx rate)
2. Check for DB connectivity: `kubectl exec deploy/nanovia-api -- python -c "from api.database import engine; print('ok')"`
3. Check for Redis: `redis-cli ping`
4. Look for recent deploys: `git log --oneline -10`
5. If caused by a deploy: rollback `kubectl rollout undo deployment/nanovia-api -n nanovia`
6. Check for upstream dependency failures (Stripe, external APIs) — check their status pages

---

### IR-7: Memory Leak

**Symptoms:** Grafana alert `process_resident_memory_bytes` growing continuously, pod OOMKilled.

**Detection:**
```bash
# Prometheus
process_resident_memory_bytes{job="nanovia-api"} > 1.5e9  # > 1.5 GB

kubectl top pods -n nanovia
kubectl describe pod <api-pod> | grep -A5 OOM
```

**Remediation:**
1. **Immediate:** Rolling restart to recover: `kubectl rollout restart deployment/nanovia-api -n nanovia`
2. Identify leak source:
   - Check Playwright browser pool — zombie killer should auto-close idle browsers
   - Check Redis connection pool leaks
   - Check asyncio task accumulation: add `asyncio.all_tasks()` count to health endpoint
3. Set memory limit and request in K8s deployment (`infra/k8s/base/api/deployment.yaml`)
4. Enable Python memory profiler in staging: `pip install memray`
5. Long-term: add `process_resident_memory_bytes` alert with 30-min threshold

---

### IR-8: Database Connection Exhaustion

**Symptoms:** `too many connections` errors in logs, API returning 500 on all DB-dependent endpoints.

**Detection:**
```bash
kubectl logs -n nanovia deploy/nanovia-api | grep "too many connections"

# On Postgres
psql -U $POSTGRES_USER -c "SELECT count(*) FROM pg_stat_activity;"
# If > max_connections (default 100): exhausted
```

**Remediation:**
1. **Immediate:** Restart API to release connections: `kubectl rollout restart deployment/nanovia-api -n nanovia`
2. Check connection pool settings in `backend/api/database.py` (`pool_size=10, max_overflow=20`)
3. If pgBouncer is deployed: `docker compose restart pgbouncer` or `kubectl rollout restart deployment/pgbouncer`
4. Reduce `pool_size` + `max_overflow` if running many API replicas (total = replicas × pool_size)
5. Check for connection leaks: sessions not being closed after errors
6. Long-term: Deploy pgBouncer in transaction mode to pool connections across replicas

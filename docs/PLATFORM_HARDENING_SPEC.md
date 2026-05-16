# PLATFORM HARDENING SPEC

## Purpose
This document is the hardening roadmap and reference spec for the scraping and platform reliability work on this branch.

It is intentionally derived from the **existing repository code as source of truth**. If code and this document diverge, the implementation in the repository wins and this file should be updated to match it.

## Guardrails
- Prefer minimal, surgical changes.
- No breaking change to existing public contracts unless explicitly called out.
- Keep `/scrape` backward-compatible.
- No open proxy behavior.
- No hardcoded secrets.
- Reuse existing route/service/infra patterns instead of refactoring broadly.

---

## PHASE 1 — Scraping proxy prod-ready

**Objective**
- Harden `GET /scrape?url=...` without breaking the existing input/output contract.

**Expected behavior**
- Preserve existing `/scrape` request and response semantics.
- Support feature-flagged scraping through `SCRAPING_ENABLED` / `ENABLE_SCRAPE_PROXY`.
- Use Redis read-through cache with configurable TTL.
- Derive cache keys from normalized URL SHA256.
- Fail open when Redis is unavailable instead of crashing the API.
- Keep logs clean and redact sensitive URLs / proxy credentials.
- Prevent `/scrape` from behaving like an open proxy.

**Implementation notes**
- Route contract remains owned by the existing scrape router and service.
- Cache and queue/storage behavior reuse the current Redis/local-fallback helpers.
- URL normalization, logging redaction, and proxy handling follow the existing scraping modules.

**Validation**
- Backend scraping tests pass.
- `docker compose config` remains valid.
- `/scrape` works with the feature flag both enabled and disabled.

**Status on this branch**
- Implemented.

---

## PHASE 2 — Queue + worker robuste

**Objective**
- Add resilient async scrape processing without breaking synchronous `/scrape`.

**Status on this branch**
- Implemented on the existing Python-native Redis queue/worker path.

**Delivered scope**
- Request de-duplication keyed on normalized URL + `render_js`.
- Dedicated worker process support.
- Queue backpressure with max depth enforcement.
- Retry/backoff behavior integrated with current scraping flow.
- Worker cleanup and browser zombie-killer hardening.
- Graceful API behavior when worker or Redis is unavailable.

---

## PHASE 3 — Sécurité SSRF hardcore

**Objective**
- Block internal network abuse and prevent `/scrape` from being used as an SSRF primitive.

**Status on this branch**
- Implemented.

**Delivered scope**
- Strict URL validation (`http` / `https` only).
- Private/local/link-local/metadata endpoint blocking.
- Sensitive port blocking.
- Redirect hop validation.
- Dual-stack DNS validation and rebinding-style rechecks.

---

## PHASE 4 — Stealth anti-bot réaliste

**Objective**
- Improve Playwright realism without unstable random fingerprinting or aggressive behavior.

**Status on this branch**
- Implemented.

**Delivered scope**
- Stable named stealth profiles.
- Coherent `User-Agent`, `Accept-Language`, locale, timezone, viewport.
- Optional proxy rotation and proxy health checks via env.
- Human jitter and optional light scroll.
- No infinite retry loop on bot-block / 403 scenarios.

---

## PHASE 5 — Kubernetes + HPA

**Objective**
- Prepare real K8s deployment without breaking the current Docker deployment model.

**Status on this branch**
- Implemented.

**Delivered scope**
- API + worker deployments.
- Service + ingress/TLS baseline.
- Readiness/liveness probes.
- Requests/limits.
- Worker PodDisruptionBudget.
- HPA for CPU/memory and optional queue-depth HPA manifest.

---

## PHASE 6 — Multi-region

**Objective**
- Define a pragmatic primary/fallback multi-region approach without active/active complexity.

**Status on this branch**
- Implemented as documented platform strategy.

**Delivered scope**
- Primary write region + warm fallback model.
- Regional blast-radius isolation.
- Regional Redis/cache/queue strategy.
- Routing/failover config and runbook guidance.

---

## PHASE 7 — Observability

**Objective**
- Make runtime behavior visible and operable in production.

**Status on this branch**
- Implemented.

**Delivered scope**
- Structured JSON logs.
- `traceId` + `correlationId`.
- `/health`, `/ready`, `/metrics`.
- Scrape metrics for latency, retries, cache behavior, queue depth, and worker heartbeat/status.
- Prometheus alert recommendations and incident runbook updates.

---

## PHASE 8 — Audit complet ligne par ligne

**Objective**
- Remove remaining high-signal platform risks before deployment.

**Status on this branch**
- Implemented.

**Delivered scope**
- Explicit release of scrape inflight locks.
- Redis client timeout tightening and pool cleanup on shutdown.
- PostgreSQL connection timeout / statement timeout defaults.
- K8s Postgres secret wiring fix.
- K8s Redis password enforcement and authenticated probes.
- Prometheus scrape timeout hardening.
- Regression tests for degraded readiness and inflight lock cleanup.

---

## Final branch status

The branch currently reflects a completed hardening track through **phases 1 to 8** with the following principles preserved:
- no `/scrape` contract break
- no hardcoded secrets
- safe degraded behavior when Redis or worker components are unavailable
- deployable Docker + K8s + monitoring configuration

## Suggested usage

When using this file in prompts or future implementation work, prefer wording like:

> Using the existing repo code as source of truth, implement the next incomplete phase from `docs/PLATFORM_HARDENING_SPEC.md` with minimal changes and no breaking change.

At the time this file was generated, **phases 1 to 8 are already implemented on this branch**.

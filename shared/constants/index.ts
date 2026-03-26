/**
 * shared/constants/index.ts
 * Constantes partagées — plans, modules, rôles, routes API
 * RÈGLE : jamais de logique métier ici, seulement des valeurs
 */
import type { ModuleKey, PlanSlug, UserRole } from "../types";

// ─── Plans ────────────────────────────────────────────────────────────────────
export const PLAN_SLUGS: Record<PlanSlug, PlanSlug> = {
  free: "free",
  pro: "pro",
  business: "business",
};

export const PLAN_HIERARCHY: Record<PlanSlug, number> = {
  free: 0,
  pro: 1,
  business: 2,
};

/** true si userPlan >= requiredPlan */
export const hasPlanAccess = (userPlan: PlanSlug, required: PlanSlug): boolean =>
  PLAN_HIERARCHY[userPlan] >= PLAN_HIERARCHY[required];

// ─── Roles ────────────────────────────────────────────────────────────────────
export const ROLES: Record<UserRole, UserRole> = {
  user: "user",
  admin: "admin",
  vip: "vip",
};

// ─── Modules ──────────────────────────────────────────────────────────────────
export const MODULE_KEYS: Record<string, ModuleKey> = {
  OPERATOR: "operator",
  CONTENT_CLONER: "content_cloner",
  MICRO_SAAS: "micro_saas",
  GHOST_AGENCY: "ghost_agency",
  DECISION_ENGINE: "decision_engine",
  KNOWLEDGE_WEAPON: "knowledge_weapon",
  DIGITAL_LEVERAGE: "digital_leverage",
  REVERSE_ENGINEERING: "reverse_engineering",
  OFFER_GENERATOR: "offer_generator",
  EXECUTION_SERVICE: "execution_service",
};

/** Modules disponibles sur mobile v1 */
export const MOBILE_MODULES: ModuleKey[] = [
  "operator",
  "decision_engine",
  "ghost_agency",
];

// ─── Routes API ───────────────────────────────────────────────────────────────
export const API_ROUTES = {
  // Auth
  AUTH_LOGIN: "/api/v1/auth/login",
  AUTH_REFRESH: "/api/v1/auth/refresh",
  AUTH_LOGOUT: "/api/v1/auth/logout",
  AUTH_REGISTER: "/api/v1/auth/register",

  // Users
  USERS_ME: "/api/v1/users/me",
  USERS_SESSIONS: "/api/v1/users/me/sessions",
  USERS_SESSION_DELETE: (id: string) => `/api/v1/users/me/sessions/${id}`,

  // Modules
  MODULES_CATALOG: "/api/v1/modules/catalog",
  MODULES_ME: "/api/v1/modules/me",
  MODULES_DETAIL: (key: string) => `/api/v1/modules/${key}`,
  OPERATOR_CHAT: "/api/v1/modules/operator/chat",
  OPERATOR_HISTORY: "/api/v1/modules/operator/history",

  // Entitlements & Billing
  ENTITLEMENTS_ME: "/api/v1/billing/entitlements",
  BILLING_ME: "/api/v1/billing/subscription",
  BILLING_PLANS: "/api/v1/billing/plans",
  BILLING_CHECKOUT: "/api/v1/billing/checkout-session",
  BILLING_PORTAL: "/api/v1/billing/portal-session",

  // Notifications
  NOTIF_REGISTER_DEVICE: "/api/v1/notifications/register-device",
  NOTIF_ME: "/api/v1/notifications/me",
  NOTIF_READ: (id: string) => `/api/v1/notifications/${id}/read`,

  // VIP
  VIP_OVERVIEW: "/api/v1/vip/overview",
  VIP_ALERTS: "/api/v1/vip/alerts",
  VIP_KPIS: "/api/v1/vip/kpis",
} as const;

// ─── Token config ─────────────────────────────────────────────────────────────
export const TOKEN_CONFIG = {
  ACCESS_EXPIRE_MINUTES: 30,
  REFRESH_EXPIRE_DAYS: 30,
  SECURE_STORE_KEY: "kt_refresh_token",
  SECURE_STORE_DEVICE_KEY: "kt_device_id",
} as const;

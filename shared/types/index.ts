/**
 * shared/types/index.ts
 * Source de vérité unique pour tous les types partagés
 * Utilisé par : web, admin, mobile, API client
 */

// ─── Plans ────────────────────────────────────────────────────────────────────
export type PlanSlug = "free" | "pro" | "business";

export interface PlanLimits {
  ai_messages_per_month: number; // -1 = unlimited
  conversations: number;
  active_modules: number;
}

export interface Plan {
  slug: PlanSlug;
  name: string;
  price_monthly_usd: number;
  price_yearly_usd: number;
  limits: PlanLimits;
  features: string[];
}

// ─── User ─────────────────────────────────────────────────────────────────────
export type UserRole = "user" | "admin" | "vip";

export interface User {
  id: string;
  email: string;
  full_name: string;
  plan: PlanSlug;
  role: UserRole;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface UserSession {
  id: string;
  device_id: string;
  device_name: string;
  ip_address: string;
  last_seen: string;
  is_current: boolean;
}

// ─── Auth ─────────────────────────────────────────────────────────────────────
export interface TokenPair {
  access_token: string;
  refresh_token: string;
  token_type: "bearer";
  expires_in: number;
}

export interface AuthState {
  user: User | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

// ─── Modules ──────────────────────────────────────────────────────────────────
export type ModuleKey =
  | "operator"
  | "content_cloner"
  | "micro_saas"
  | "ghost_agency"
  | "decision_engine"
  | "knowledge_weapon"
  | "digital_leverage"
  | "reverse_engineering"
  | "offer_generator"
  | "execution_service";

export type ModuleCategory =
  | "productivity"
  | "marketing"
  | "sales"
  | "intelligence"
  | "automation";

export interface Module {
  key: ModuleKey;
  name: string;
  description: string;
  category: ModuleCategory;
  icon: string;
  enabled: boolean;
  visible_on_mobile: boolean;
  entitlements_required: PlanSlug[];
  roles_allowed: UserRole[];
  is_available: boolean; // computed: user has access?
}

// ─── Entitlements ─────────────────────────────────────────────────────────────
export interface Entitlements {
  plan: PlanSlug;
  status: "active" | "past_due" | "canceled" | "free" | "inactive";
  limits: PlanLimits;
  features: string[];
  subscription: {
    id: string | null;
    current_period_end: string | null;
    cancel_at_period_end: boolean;
  };
}

// ─── Billing ──────────────────────────────────────────────────────────────────
export interface Subscription {
  plan: PlanSlug;
  status: string;
  subscription_id: string | null;
  current_period_end: string | null;
  cancel_at_period_end: boolean;
}

export interface Invoice {
  id: string;
  amount_paid: number;
  currency: string;
  status: string;
  created: string;
  invoice_pdf: string | null;
}

// ─── Notifications ────────────────────────────────────────────────────────────
export type NotificationType =
  | "billing"
  | "module"
  | "system"
  | "vip"
  | "alert";

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  body: string;
  read: boolean;
  data: Record<string, unknown>;
  created_at: string;
}

export interface DeviceRegistration {
  push_token: string;
  device_id: string;
  device_name: string;
  platform: "ios" | "android";
}

// ─── VIP ──────────────────────────────────────────────────────────────────────
export interface KPI {
  key: string;
  label: string;
  value: number | string;
  trend?: "up" | "down" | "stable";
  unit?: string;
}

export interface VIPOverview {
  kpis: KPI[];
  alerts: VIPAlert[];
  last_updated: string;
}

export interface VIPAlert {
  id: string;
  severity: "critical" | "warning" | "info";
  message: string;
  created_at: string;
}

// ─── API Responses ────────────────────────────────────────────────────────────
export interface APIError {
  detail: string;
  status_code?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

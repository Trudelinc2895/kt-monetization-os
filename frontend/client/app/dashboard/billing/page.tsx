"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import {
  createCheckoutSession,
  createAddonCheckout,
  createPortalSession,
  getEntitlements,
  getPlans,
  getUsageStats,
  getAddons,
  type Entitlements,
  type Plan,
  type UsageStats,
  type AddonPublic,
  type UpsellSuggestion,
} from "@/lib/api";

function UsageBar({ count, limit, pct }: { count: number; limit: number; pct: number }) {
  const isUnlimited = limit === -1;
  const color = pct >= 90 ? "bg-red-500" : pct >= 70 ? "bg-yellow-400" : "bg-purple-500";
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-400">
        <span>{count.toLocaleString()} messages utilisés</span>
        <span>{isUnlimited ? "∞ illimités" : `${limit.toLocaleString()} / mois`}</span>
      </div>
      {!isUnlimited && (
        <div className="w-full bg-gray-800 rounded-full h-2">
          <div
            className={`h-2 rounded-full transition-all ${color}`}
            style={{ width: `${Math.min(pct, 100)}%` }}
          />
        </div>
      )}
      {pct >= 80 && !isUnlimited && (
        <p className="text-xs text-yellow-400">⚠ {Math.round(pct)}% de ta limite mensuelle atteinte</p>
      )}
    </div>
  );
}

function UpsellBanner({ upsell }: { upsell: UpsellSuggestion }) {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleUpgrade = async (interval: "monthly" | "yearly") => {
    setLoading(true);
    setError("");
    try {
      const res = await createCheckoutSession(upsell.next_plan, interval);
      window.location.href = res.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur de paiement");
      setLoading(false);
    }
  };

  return (
    <div className="bg-purple-950/40 border border-purple-700/50 rounded-2xl p-5 mb-8">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <div className="text-purple-300 font-bold text-base mb-1">⚡ {upsell.headline}</div>
          {upsell.trigger === "usage_limit_80pct" && (
            <p className="text-sm text-gray-400">Tu approches ta limite. Upgrade maintenant pour ne jamais être bloqué.</p>
          )}
          {upsell.yearly_savings_usd > 0 && (
            <p className="text-xs text-green-400 mt-1">
              💰 Économise ${upsell.yearly_savings_usd}/an avec le plan annuel
            </p>
          )}
          {upsell.new_features.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-2">
              {upsell.new_features.slice(0, 4).map((f) => (
                <span key={f} className="text-xs bg-purple-900/50 text-purple-300 px-2 py-0.5 rounded-full">{f}</span>
              ))}
            </div>
          )}
        </div>
        <div className="flex flex-col gap-2 shrink-0">
          <button
            onClick={() => handleUpgrade("yearly")}
            disabled={loading}
            className="bg-purple-600 hover:bg-purple-500 disabled:opacity-50 text-white font-semibold px-5 py-2 rounded-xl text-sm transition"
          >
            {loading ? "..." : `Annuel — $${upsell.price_yearly_usd}/an`}
          </button>
          <button
            onClick={() => handleUpgrade("monthly")}
            disabled={loading}
            className="border border-purple-700 hover:border-purple-500 text-purple-300 px-5 py-2 rounded-xl text-sm transition"
          >
            Mensuel — ${upsell.price_monthly_usd}/mois
          </button>
        </div>
      </div>
      {error && <p className="text-red-400 text-xs mt-2">{error}</p>}
    </div>
  );
}

export default function BillingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [plans, setPlans] = useState<Plan[]>([]);
  const [entitlements, setEntitlements] = useState<Entitlements | null>(null);
  const [usage, setUsage] = useState<UsageStats | null>(null);
  const [addons, setAddons] = useState<AddonPublic[]>([]);
  const [yearly, setYearly] = useState(false);
  const [loadingPlan, setLoadingPlan] = useState<string | null>(null);
  const [loadingAddon, setLoadingAddon] = useState<string | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!loading && !user) router.push("/login");
  }, [loading, user, router]);

  useEffect(() => {
    if (!user) return;
    getPlans().then(setPlans).catch(console.error);
    getEntitlements().then(setEntitlements).catch(console.error);
    getUsageStats().then(setUsage).catch(console.error);
    getAddons().then(setAddons).catch(console.error);
  }, [user]);

  const handleUpgrade = async (slug: string) => {
    setLoadingPlan(slug);
    setError("");
    try {
      const res = await createCheckoutSession(slug, yearly ? "yearly" : "monthly");
      window.location.href = res.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Impossible de lancer le paiement");
      setLoadingPlan(null);
    }
  };

  const handleAddon = async (slug: string) => {
    setLoadingAddon(slug);
    setError("");
    try {
      const res = await createAddonCheckout(slug);
      window.location.href = res.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur add-on");
      setLoadingAddon(null);
    }
  };

  const handlePortal = async () => {
    setError("");
    try {
      const res = await createPortalSession();
      window.location.href = res.url;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur portail");
    }
  };

  if (loading || !user) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <div className="text-purple-400 animate-pulse">Chargement...</div>
      </div>
    );
  }

  const currentPlan = plans.find((p) => p.slug === entitlements?.plan);
  const upsell = entitlements?.upsell ?? null;

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/dashboard" className="text-gray-500 hover:text-white transition">←</Link>
            <span className="font-bold">💳 Billing & Plans</span>
          </div>
          {entitlements && (
            <div className="flex items-center gap-3 text-sm">
              <span className="text-gray-500">Crédits overage :</span>
              <span className="font-bold text-purple-300">{entitlements.credits}</span>
            </div>
          )}
        </div>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-10 space-y-10">
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
            {error}
          </div>
        )}

        {/* Current plan + usage */}
        {entitlements && (
          <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6 space-y-5">
            <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
              <div>
                <div className="text-xs text-gray-500 uppercase tracking-wider mb-1">Plan actuel</div>
                <div className="flex items-center gap-3">
                  <span className="text-2xl font-black uppercase">{entitlements.plan}</span>
                  <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                    entitlements.status === "active" ? "bg-green-900/50 text-green-400" : "bg-yellow-900/50 text-yellow-400"
                  }`}>{entitlements.status}</span>
                </div>
                {entitlements.subscription.current_period_end && (
                  <p className="text-xs text-gray-500 mt-1">
                    Renouvellement : {new Date(entitlements.subscription.current_period_end).toLocaleDateString("fr-CA")}
                    {entitlements.subscription.cancel_at_period_end && (
                      <span className="text-orange-400 ml-2">(annulation prévue)</span>
                    )}
                  </p>
                )}
              </div>
              <div className="flex gap-2">
                {entitlements.plan !== "free" && (
                  <button
                    onClick={handlePortal}
                    className="border border-gray-700 hover:border-purple-600 text-gray-400 hover:text-white px-4 py-2 rounded-xl text-sm transition"
                  >
                    Gérer →
                  </button>
                )}
                <Link
                  href="/dashboard/analytics"
                  className="border border-gray-700 hover:border-gray-600 text-gray-400 hover:text-white px-4 py-2 rounded-xl text-sm transition"
                >
                  Analytics →
                </Link>
              </div>
            </div>

            {/* Usage bar */}
            {usage && (
              <UsageBar
                count={usage.messages_count}
                limit={usage.messages_limit}
                pct={usage.usage_pct}
              />
            )}

            {/* Credit balance */}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 pt-2">
              <div className="bg-gray-800/50 rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-purple-300">{entitlements.credits}</div>
                <div className="text-xs text-gray-500 mt-0.5">Crédits overage</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-white">
                  {entitlements.limits.ai_messages_per_month === -1 ? "∞" : entitlements.limits.ai_messages_per_month.toLocaleString()}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Messages/mois</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-white">
                  {entitlements.limits.active_modules}
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Modules actifs</div>
              </div>
              <div className="bg-gray-800/50 rounded-xl p-3 text-center">
                <div className="text-xl font-bold text-white">
                  {entitlements.limits.storage_gb} GB
                </div>
                <div className="text-xs text-gray-500 mt-0.5">Stockage</div>
              </div>
            </div>
          </div>
        )}

        {/* Contextual upsell banner */}
        {upsell && <UpsellBanner upsell={upsell} />}

        {/* Billing toggle */}
        <div>
          <h2 className="text-lg font-bold mb-6">Choisir un plan</h2>
          <div className="flex items-center gap-4 mb-8">
            <span className={`text-sm ${!yearly ? "text-white" : "text-gray-500"}`}>Mensuel</span>
            <button
              onClick={() => setYearly(!yearly)}
              className={`relative w-12 h-6 rounded-full transition ${yearly ? "bg-purple-600" : "bg-gray-700"}`}
              aria-label="Toggle annual billing"
            >
              <span className={`absolute top-1 left-1 w-4 h-4 bg-white rounded-full transition-transform ${yearly ? "translate-x-6" : ""}`} />
            </button>
            <span className={`text-sm ${yearly ? "text-white" : "text-gray-500"}`}>
              Annuel <span className="text-green-400 text-xs font-semibold">(-17%)</span>
            </span>
          </div>

          {/* Plans grid */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
            {plans.map((plan) => {
              const isCurrent = entitlements?.plan === plan.slug;
              const price = yearly ? plan.price_yearly_usd : plan.price_monthly_usd;
              const isPopular = plan.slug === "pro";
              const savingsPerYear = plan.yearly_discount_pct > 0
                ? Math.round((plan.price_monthly_usd * 12) - plan.price_yearly_usd)
                : 0;

              return (
                <div
                  key={plan.slug}
                  className={`bg-gray-900 border rounded-2xl p-6 flex flex-col relative ${
                    isCurrent
                      ? "border-purple-600 shadow-lg shadow-purple-500/10"
                      : isPopular
                      ? "border-purple-700"
                      : "border-gray-800"
                  }`}
                >
                  {isPopular && !isCurrent && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-bold text-white bg-purple-600 px-3 py-1 rounded-full">
                      ★ Populaire
                    </div>
                  )}
                  {isCurrent && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 text-xs font-bold text-white bg-green-600 px-3 py-1 rounded-full">
                      ✓ Plan actuel
                    </div>
                  )}

                  <div className="font-bold text-white text-lg capitalize mb-1">{plan.name}</div>
                  <div className="flex items-end gap-1 mb-1">
                    <span className="text-3xl font-black">
                      {price === 0 ? "Gratuit" : `$${price}`}
                    </span>
                    {price > 0 && <span className="text-gray-500 text-sm mb-1">/ {yearly ? "an" : "mois"}</span>}
                  </div>
                  {yearly && savingsPerYear > 0 && (
                    <p className="text-xs text-green-400 mb-3">💰 Économise ${savingsPerYear}/an</p>
                  )}
                  {plan.trial_days > 0 && !isCurrent && (
                    <p className="text-xs text-purple-400 mb-3">✨ {plan.trial_days} jours gratuits</p>
                  )}

                  <ul className="space-y-2 text-sm text-gray-400 flex-1 my-4">
                    {plan.features.map((f, i) => (
                      <li key={i} className="flex items-start gap-2">
                        <span className="text-green-400 mt-0.5 shrink-0">✓</span>
                        <span>{f}</span>
                      </li>
                    ))}
                  </ul>

                  {isCurrent ? (
                    <div className="w-full text-center bg-gray-800 text-gray-400 font-semibold py-2.5 rounded-xl text-sm">
                      Plan actuel
                    </div>
                  ) : plan.slug === "free" ? (
                    <div className="w-full text-center bg-gray-800/50 text-gray-500 font-semibold py-2.5 rounded-xl text-sm">
                      Gratuit pour toujours
                    </div>
                  ) : (
                    <button
                      onClick={() => handleUpgrade(plan.slug)}
                      disabled={!!loadingPlan}
                      className={`w-full font-semibold py-2.5 rounded-xl text-sm transition disabled:opacity-50 ${
                        isPopular
                          ? "bg-purple-600 hover:bg-purple-500 text-white"
                          : "border border-gray-700 hover:border-purple-600 text-gray-300 hover:text-white"
                      }`}
                    >
                      {loadingPlan === plan.slug ? "Redirection..." : "Choisir ce plan"}
                    </button>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Add-ons section */}
        {addons.length > 0 && (
          <div>
            <h2 className="text-lg font-bold mb-2">Add-ons disponibles</h2>
            <p className="text-sm text-gray-500 mb-6">Achetez en une seule fois. S&apos;applique immédiatement à votre compte.</p>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              {addons.map((addon) => (
                <div key={addon.slug} className="bg-gray-900 border border-gray-800 rounded-2xl p-5 flex flex-col gap-3">
                  <div className="font-bold text-white text-sm">{addon.name}</div>
                  <p className="text-xs text-gray-400 flex-1">{addon.description}</p>
                  <div className="flex items-center justify-between">
                    <span className="text-xl font-black text-white">${addon.price_usd}</span>
                    <button
                      onClick={() => handleAddon(addon.slug)}
                      disabled={!!loadingAddon}
                      className="bg-gray-800 hover:bg-gray-700 text-white text-xs font-semibold px-4 py-2 rounded-xl transition disabled:opacity-50"
                    >
                      {loadingAddon === addon.slug ? "..." : "Acheter"}
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Feature gates overview */}
        {entitlements && currentPlan && (
          <div>
            <h2 className="text-lg font-bold mb-4">Fonctionnalités incluses</h2>
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
              {Object.entries(entitlements.features_enabled).map(([key, enabled]) => {
                const labels: Record<string, string> = {
                  api_access: "API Access",
                  white_label: "White-label",
                  priority_support: "Support prioritaire",
                  advanced_analytics: "Analytics avancés",
                  custom_modules: "Modules custom",
                  automation: "Automation",
                  team_seats: "Team seats",
                  data_export: "Export CSV",
                  overage_allowed: "Overage crédits",
                  early_access: "Early access",
                };
                return (
                  <div
                    key={key}
                    className={`rounded-xl p-3 text-center text-xs ${
                      enabled
                        ? "bg-purple-900/20 border border-purple-700/30 text-purple-300"
                        : "bg-gray-900 border border-gray-800 text-gray-600"
                    }`}
                  >
                    <div className="text-lg mb-1">{enabled ? "✓" : "✗"}</div>
                    <div>{labels[key] ?? key}</div>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

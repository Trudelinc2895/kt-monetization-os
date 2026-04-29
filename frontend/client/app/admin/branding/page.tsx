"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getBranding, updateBranding, type BrandingSettings } from "@/lib/api";
import { Button } from "@/components/ui";

export default function AdminBrandingPage() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const [form, setForm] = useState<Partial<BrandingSettings>>({
    company_name: null,
    logo_url: null,
    primary_color: null,
    accent_color: null,
    support_email: null,
    custom_domain: null,
  });
  const [saving, setSaving] = useState(false);
  const [loadingData, setLoadingData] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  useEffect(() => {
    if (!loading && !user) router.push("/login");
    if (!loading && user && !user.is_admin) router.push("/dashboard");
  }, [user, loading, router]);

  useEffect(() => {
    if (!user?.is_admin) return;
    getBranding()
      .then((data) => setForm(data))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingData(false));
  }, [user]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    setSuccess(null);
    try {
      const updated = await updateBranding(form);
      setForm(updated);
      setSuccess("✅ Paramètres de marque sauvegardés.");
    } catch (err: unknown) {
      setError((err as Error).message ?? "Erreur lors de la sauvegarde.");
    } finally {
      setSaving(false);
    }
  };

  if (loading || loadingData) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <p className="text-gray-500 animate-pulse">Chargement...</p>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Marque blanche</h1>
        <p className="text-sm text-gray-500 mt-1">Personnalise l&apos;apparence de la plateforme</p>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700/50 text-red-300 rounded-lg px-4 py-3 mb-4 text-sm">
          {error}
        </div>
      )}
      {success && (
        <div className="bg-green-900/30 border border-green-700/50 text-green-300 rounded-lg px-4 py-3 mb-4 text-sm">
          {success}
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">
          {/* Company Name */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Nom de l&apos;entreprise</label>
            <input
              type="text"
              value={form.company_name ?? ""}
              onChange={(e) => setForm({ ...form, company_name: e.target.value || null })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
              placeholder="Nanovia"
              maxLength={120}
            />
          </div>

          {/* Logo URL */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">URL du logo</label>
            <input
              type="url"
              value={form.logo_url ?? ""}
              onChange={(e) => setForm({ ...form, logo_url: e.target.value || null })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
              placeholder="https://cdn.example.com/logo.png"
            />
          </div>

          {/* Primary Color */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Couleur principale</label>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={form.primary_color ?? ""}
                onChange={(e) => setForm({ ...form, primary_color: e.target.value || null })}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
                placeholder="#7C3AED"
                maxLength={7}
              />
              {form.primary_color && /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(form.primary_color) && (
                <div
                  className="w-8 h-8 rounded-lg border border-gray-600 flex-shrink-0"
                  style={{ backgroundColor: form.primary_color }}
                />
              )}
            </div>
          </div>

          {/* Accent Color */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Couleur d&apos;accentuation</label>
            <div className="flex items-center gap-3">
              <input
                type="text"
                value={form.accent_color ?? ""}
                onChange={(e) => setForm({ ...form, accent_color: e.target.value || null })}
                className="flex-1 bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
                placeholder="#10B981"
                maxLength={7}
              />
              {form.accent_color && /^#([0-9A-Fa-f]{3}|[0-9A-Fa-f]{6})$/.test(form.accent_color) && (
                <div
                  className="w-8 h-8 rounded-lg border border-gray-600 flex-shrink-0"
                  style={{ backgroundColor: form.accent_color }}
                />
              )}
            </div>
          </div>

          {/* Support Email */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Email de support</label>
            <input
              type="email"
              value={form.support_email ?? ""}
              onChange={(e) => setForm({ ...form, support_email: e.target.value || null })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
              placeholder="support@example.com"
              maxLength={254}
            />
          </div>

          {/* Custom Domain */}
          <div>
            <label className="block text-sm text-gray-400 mb-1">Domaine personnalisé</label>
            <input
              type="text"
              value={form.custom_domain ?? ""}
              onChange={(e) => setForm({ ...form, custom_domain: e.target.value || null })}
              className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
              placeholder="app.example.com"
              maxLength={253}
            />
          </div>

          <div className="pt-2">
            <Button type="submit" loading={saving}>
              Sauvegarder les paramètres
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}

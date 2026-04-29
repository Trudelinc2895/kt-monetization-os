"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth-context";
import { listCustomModules, createCustomModule, deleteCustomModule, type CustomModuleData } from "@/lib/api";
import { Button } from "@/components/ui";

export default function CustomModulesPage() {
  const { user, loading } = useAuth();
  const [modules, setModules] = useState<CustomModuleData[]>([]);
  const [loadingModules, setLoadingModules] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  const [form, setForm] = useState({ name: "", description: "", prompt_template: "" });
  const [creating, setCreating] = useState(false);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const loadModules = () => {
    setLoadingModules(true);
    listCustomModules()
      .then(setModules)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoadingModules(false));
  };

  useEffect(() => {
    if (!user) return;
    if (user.plan !== "business") return;
    loadModules();
  }, [user]);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setCreating(true);
    setError(null);
    setSuccess(null);
    try {
      await createCustomModule({
        name: form.name,
        description: form.description || undefined,
        prompt_template: form.prompt_template,
      });
      setForm({ name: "", description: "", prompt_template: "" });
      setSuccess("✅ Module créé avec succès.");
      loadModules();
    } catch (err: unknown) {
      setError((err as Error).message ?? "Erreur lors de la création.");
    } finally {
      setCreating(false);
    }
  };

  const handleDelete = async (id: string) => {
    setDeletingId(id);
    try {
      await deleteCustomModule(id);
      setModules((prev) => prev.filter((m) => m.id !== id));
    } catch (err: unknown) {
      setError((err as Error).message ?? "Erreur lors de la suppression.");
    } finally {
      setDeletingId(null);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-950">
        <p className="text-gray-500 animate-pulse">Chargement...</p>
      </div>
    );
  }

  if (!user || user.plan !== "business") {
    return (
      <div className="min-h-screen bg-gray-950 text-white flex items-center justify-center">
        <div className="max-w-md text-center space-y-4 px-6">
          <div className="text-5xl">🔒</div>
          <h1 className="text-2xl font-bold">Fonctionnalité Business</h1>
          <p className="text-gray-400 text-sm">
            Les modules personnalisés sont réservés au plan Business. Mettez à niveau votre abonnement pour accéder à cette fonctionnalité.
          </p>
          <a
            href="/dashboard/billing"
            className="inline-block mt-2 bg-purple-600 hover:bg-purple-500 text-white font-semibold px-6 py-2.5 rounded-xl text-sm transition"
          >
            Voir les plans →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <header className="border-b border-gray-800 bg-gray-900/50 backdrop-blur sticky top-0 z-10">
        <div className="max-w-3xl mx-auto px-6 py-4 flex items-center gap-3">
          <a href="/dashboard" className="text-gray-500 hover:text-white transition">←</a>
          <span className="font-bold">🧩 Modules personnalisés</span>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-6 py-10 space-y-8">
        {error && (
          <div className="bg-red-500/10 border border-red-500/30 text-red-400 rounded-xl px-4 py-3 text-sm">
            ⚠️ {error}
          </div>
        )}
        {success && (
          <div className="bg-green-500/10 border border-green-500/30 text-green-400 rounded-xl px-4 py-3 text-sm">
            {success}
          </div>
        )}

        {/* Create form */}
        <div className="bg-gray-900 border border-gray-800 rounded-2xl p-6">
          <h2 className="text-lg font-bold mb-4">Créer un module</h2>
          <form onSubmit={handleCreate} className="space-y-4">
            <div>
              <label className="block text-sm text-gray-400 mb-1">Nom <span className="text-red-400">*</span></label>
              <input
                type="text"
                value={form.name}
                onChange={(e) => setForm({ ...form, name: e.target.value })}
                required
                minLength={3}
                maxLength={80}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
                placeholder="Mon module IA"
              />
            </div>
            <div>
              <label className="block text-sm text-gray-400 mb-1">Description (optionnel)</label>
              <input
                type="text"
                value={form.description}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                maxLength={200}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition"
                placeholder="Décris ce que fait ce module..."
              />
            </div>
            <div>
              <div className="flex items-center justify-between mb-1">
                <label className="block text-sm text-gray-400">Prompt template <span className="text-red-400">*</span></label>
                <span className={`text-xs ${form.prompt_template.length > 9000 ? "text-red-400" : "text-gray-500"}`}>
                  {form.prompt_template.length}/10 000
                </span>
              </div>
              <textarea
                value={form.prompt_template}
                onChange={(e) => setForm({ ...form, prompt_template: e.target.value })}
                required
                minLength={10}
                maxLength={10000}
                rows={6}
                className="w-full bg-gray-800 border border-gray-700 rounded-lg px-4 py-2.5 text-white text-sm focus:outline-none focus:border-purple-500 transition resize-y"
                placeholder="Tu es un assistant spécialisé dans... Réponds toujours en..."
              />
            </div>
            <Button type="submit" loading={creating} size="sm">
              Créer le module
            </Button>
          </form>
        </div>

        {/* Modules list */}
        <div className="space-y-3">
          <h2 className="text-lg font-bold">Mes modules</h2>
          {loadingModules ? (
            <p className="text-sm text-gray-500 animate-pulse">Chargement...</p>
          ) : modules.length === 0 ? (
            <p className="text-sm text-gray-500">Aucun module créé pour l&apos;instant.</p>
          ) : (
            modules.map((mod) => (
              <div key={mod.id} className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start justify-between gap-4">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-white text-sm">{mod.name}</h3>
                    <span className="text-xs font-mono text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                      /{mod.slug}
                    </span>
                  </div>
                  {mod.description && (
                    <p className="text-xs text-gray-400 mt-1">{mod.description}</p>
                  )}
                  <p className="text-xs text-gray-600 mt-1 truncate">
                    {mod.prompt_template.slice(0, 80)}…
                  </p>
                </div>
                <button
                  onClick={() => handleDelete(mod.id)}
                  disabled={deletingId === mod.id}
                  className="text-xs px-3 py-1 rounded-lg border border-red-700/40 text-red-400 hover:bg-red-900/20 disabled:opacity-50 transition flex-shrink-0"
                >
                  {deletingId === mod.id ? "⏳" : "Supprimer"}
                </button>
              </div>
            ))
          )}
        </div>
      </main>
    </div>
  );
}

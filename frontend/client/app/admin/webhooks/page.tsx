"use client";

import { useEffect, useState } from "react";
import { getAdminWebhooks, replayWebhook, type AdminWebhookEvent } from "@/lib/api";

const STATUS_BADGE: Record<string, string> = {
  processed: "bg-green-900/40 text-green-400",
  failed: "bg-red-900/40 text-red-400",
  ignored: "bg-gray-700 text-gray-400",
};

function truncate(str: string | null | undefined, max = 40): string {
  if (!str) return "—";
  return str.length > max ? str.slice(0, max) + "…" : str;
}

export default function AdminWebhooksPage() {
  const [webhooks, setWebhooks] = useState<AdminWebhookEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [replayingId, setReplayingId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const loadWebhooks = () => {
    setLoading(true);
    setError(null);
    getAdminWebhooks(50)
      .then((res) => setWebhooks(res.webhooks))
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadWebhooks();
  }, []);

  const handleReplay = async (stripeEventId: string) => {
    setReplayingId(stripeEventId);
    setToast(null);
    try {
      await replayWebhook(stripeEventId);
      setToast("✅ Événement rejoué avec succès.");
      loadWebhooks();
    } catch (e: unknown) {
      setToast("❌ " + ((e as Error).message ?? "Erreur lors du rejeu."));
    } finally {
      setReplayingId(null);
    }
  };

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-white">Webhook Events</h1>
        <p className="text-sm text-gray-500 mt-1">Last 50 Stripe webhook events</p>
      </div>

      {error && (
        <div className="bg-red-900/30 border border-red-700/50 text-red-300 rounded-lg px-4 py-3 mb-4">
          {error}
        </div>
      )}

      {toast && (
        <div className="bg-gray-800 border border-gray-700 text-gray-200 rounded-lg px-4 py-3 mb-4 text-sm">
          {toast}
        </div>
      )}

      <div className="bg-gray-900 border border-gray-800 rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-800 text-left">
              <th className="px-4 py-3 text-gray-500 font-medium">Event ID</th>
              <th className="px-4 py-3 text-gray-500 font-medium">Type</th>
              <th className="px-4 py-3 text-gray-500 font-medium">Status</th>
              <th className="px-4 py-3 text-gray-500 font-medium">Error</th>
              <th className="px-4 py-3 text-gray-500 font-medium">Processed At</th>
              <th className="px-4 py-3 text-gray-500 font-medium">Actions</th>
            </tr>
          </thead>
          <tbody>
            {loading ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-gray-500 animate-pulse">
                  Loading...
                </td>
              </tr>
            ) : webhooks.length === 0 ? (
              <tr>
                <td colSpan={6} className="px-4 py-10 text-center text-gray-500">
                  No webhook events.
                </td>
              </tr>
            ) : (
              webhooks.map((evt) => (
                <tr key={evt.id} className="border-b border-gray-800/50">
                  <td className="px-4 py-2.5 font-mono text-gray-400 text-xs">
                    {truncate(evt.stripe_event_id, 28)}
                  </td>
                  <td className="px-4 py-2.5 text-gray-200">{evt.event_type}</td>
                  <td className="px-4 py-2.5">
                    <span
                      className={`text-xs px-2 py-0.5 rounded-full ${
                        STATUS_BADGE[evt.status] ?? "bg-gray-700 text-gray-400"
                      }`}
                    >
                      {evt.status}
                    </span>
                  </td>
                  <td className="px-4 py-2.5 text-gray-500 max-w-[180px] truncate">
                    {truncate(evt.error, 40)}
                  </td>
                  <td className="px-4 py-2.5 text-gray-500">
                    {evt.processed_at
                      ? new Date(evt.processed_at).toLocaleString()
                      : "—"}
                  </td>
                  <td className="px-4 py-2.5">
                    {(evt.status === "failed" || evt.status === "ignored") && (
                      <button
                        onClick={() => handleReplay(evt.stripe_event_id)}
                        disabled={replayingId === evt.stripe_event_id}
                        className="text-xs px-3 py-1 rounded-lg bg-purple-700/30 hover:bg-purple-700/60 text-purple-300 border border-purple-700/40 disabled:opacity-50 transition"
                      >
                        {replayingId === evt.stripe_event_id ? (
                          <span className="animate-pulse">⏳</span>
                        ) : (
                          "Rejouer"
                        )}
                      </button>
                    )}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

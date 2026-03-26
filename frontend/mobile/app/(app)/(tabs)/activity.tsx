/**
 * app/(app)/(tabs)/activity.tsx — Historique conversations IA
 */
import { ScrollView, View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { apiClient } from "../../../lib/apiClient";
import { API_ROUTES } from "@shared/constants";

interface ConvSummary { id: string; title: string; module: string; updated_at: string; }

export default function ActivityScreen() {
  const { data: history, isLoading } = useQuery<ConvSummary[]>({
    queryKey: ["operator-history"],
    queryFn: () => apiClient.get(API_ROUTES.OPERATOR_HISTORY),
  });

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>Activité</Text>
      <Text style={styles.subtitle}>Historique de tes conversations IA</Text>
      {history?.length === 0 && <Text style={styles.empty}>Aucune conversation pour l'instant.</Text>}
      {history?.map((c) => (
        <TouchableOpacity key={c.id} style={styles.card} onPress={() => router.push(`/(app)/modules/operator?id=${c.id}`)}>
          <Text style={styles.convTitle}>{c.title || "Conversation sans titre"}</Text>
          <Text style={styles.convMeta}>{c.module} · {new Date(c.updated_at).toLocaleDateString("fr-CA")}</Text>
        </TouchableOpacity>
      ))}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0A0F" },
  content: { padding: 20, paddingTop: 60 },
  pageTitle: { color: "#FFF", fontSize: 24, fontWeight: "800" },
  subtitle: { color: "#666", fontSize: 13, marginTop: 4, marginBottom: 24 },
  empty: { color: "#444", textAlign: "center", marginTop: 40 },
  card: { backgroundColor: "#1A1A2E", borderRadius: 12, padding: 16, marginBottom: 10 },
  convTitle: { color: "#FFF", fontWeight: "600" },
  convMeta: { color: "#666", fontSize: 12, marginTop: 4 },
});

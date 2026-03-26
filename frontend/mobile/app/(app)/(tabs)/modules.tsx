/**
 * app/(app)/(tabs)/modules.tsx — Liste des modules mobile
 */
import { ScrollView, View, Text, StyleSheet, TouchableOpacity } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { router } from "expo-router";
import { apiClient } from "../../../lib/apiClient";
import type { Module } from "@shared/types";

const CATEGORY_LABELS: Record<string, string> = {
  productivity: "🧠 Productivité",
  marketing: "📣 Marketing",
  sales: "💰 Ventes",
  intelligence: "⚡ Intelligence",
  automation: "🤖 Automation",
};

export default function ModulesScreen() {
  const { data: modules, isLoading } = useQuery<Module[]>({
    queryKey: ["mobile-modules"],
    queryFn: () => apiClient.get("/api/v1/modules/catalog/mobile"),
  });

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>Modules</Text>
      <Text style={styles.subtitle}>Tes outils IA disponibles sur mobile</Text>

      {modules?.map((m) => (
        <TouchableOpacity
          key={m.key}
          style={[styles.card, !m.is_available && styles.cardDisabled]}
          onPress={() => m.is_available && router.push(`/(app)/modules/${m.key}`)}
          activeOpacity={m.is_available ? 0.7 : 1}
        >
          <View style={styles.cardHeader}>
            <Text style={styles.moduleCategory}>{CATEGORY_LABELS[m.category] ?? m.category}</Text>
            {m.is_available ? (
              <View style={styles.activeBadge}><Text style={styles.activeText}>Actif</Text></View>
            ) : (
              <View style={styles.upgradeBadge}><Text style={styles.upgradeText}>Pro requis</Text></View>
            )}
          </View>
          <Text style={styles.moduleName}>{m.name}</Text>
          <Text style={styles.moduleDesc}>{m.description}</Text>
          {m.is_available && <Text style={styles.cta}>Ouvrir →</Text>}
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
  card: { backgroundColor: "#1A1A2E", borderRadius: 16, padding: 18, marginBottom: 12, borderWidth: 1, borderColor: "#2A2A4A" },
  cardDisabled: { opacity: 0.45 },
  cardHeader: { flexDirection: "row", justifyContent: "space-between", marginBottom: 8 },
  moduleCategory: { color: "#888", fontSize: 11 },
  activeBadge: { backgroundColor: "#22C55E33", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  activeText: { color: "#22C55E", fontSize: 11, fontWeight: "700" },
  upgradeBadge: { backgroundColor: "#F59E0B22", paddingHorizontal: 8, paddingVertical: 2, borderRadius: 10 },
  upgradeText: { color: "#F59E0B", fontSize: 11, fontWeight: "700" },
  moduleName: { color: "#FFF", fontSize: 16, fontWeight: "700" },
  moduleDesc: { color: "#888", fontSize: 12, marginTop: 4 },
  cta: { color: "#7C3AED", fontWeight: "700", marginTop: 10, fontSize: 13 },
});

/**
 * app/(app)/(tabs)/vip.tsx — VIP Panel (Pro/Business uniquement)
 */
import { ScrollView, View, Text, StyleSheet, ActivityIndicator } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../../lib/apiClient";
import { API_ROUTES } from "@shared/constants";
import type { VIPOverview } from "@shared/types";

const SEVERITY_COLOR = { critical: "#EF4444", warning: "#F59E0B", info: "#3B82F6" };

export default function VIPScreen() {
  const { data, isLoading } = useQuery<VIPOverview>({
    queryKey: ["vip-overview"],
    queryFn: () => apiClient.get(API_ROUTES.VIP_OVERVIEW),
  });

  if (isLoading) return (
    <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0A0A0F" }}>
      <ActivityIndicator color="#F59E0B" />
    </View>
  );

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>⚡ VIP Panel</Text>
      <Text style={styles.subtitle}>Vue synthétique de ton système</Text>

      {/* KPIs */}
      <Text style={styles.sectionTitle}>KPIs</Text>
      <View style={styles.kpiGrid}>
        {data?.kpis.map((kpi) => (
          <View key={kpi.key} style={styles.kpiCard}>
            <Text style={styles.kpiLabel}>{kpi.label}</Text>
            <Text style={styles.kpiValue}>{kpi.value}{kpi.unit ? ` ${kpi.unit}` : ""}</Text>
          </View>
        ))}
      </View>

      {/* Alerts */}
      {(data?.alerts?.length ?? 0) > 0 && (
        <>
          <Text style={styles.sectionTitle}>Alertes</Text>
          {data?.alerts.map((a) => (
            <View key={a.id} style={[styles.alertCard, { borderColor: SEVERITY_COLOR[a.severity] }]}>
              <Text style={[styles.alertSeverity, { color: SEVERITY_COLOR[a.severity] }]}>
                {a.severity.toUpperCase()}
              </Text>
              <Text style={styles.alertMsg}>{a.message}</Text>
            </View>
          ))}
        </>
      )}

      <Text style={styles.updatedAt}>
        Mis à jour : {data?.last_updated ? new Date(data.last_updated).toLocaleTimeString("fr-CA") : "—"}
      </Text>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0A0F" },
  content: { padding: 20, paddingTop: 60 },
  pageTitle: { color: "#F59E0B", fontSize: 24, fontWeight: "800" },
  subtitle: { color: "#666", fontSize: 13, marginTop: 4, marginBottom: 24 },
  sectionTitle: { color: "#FFF", fontSize: 16, fontWeight: "700", marginBottom: 10 },
  kpiGrid: { flexDirection: "row", flexWrap: "wrap", gap: 10, marginBottom: 24 },
  kpiCard: { backgroundColor: "#1A1A2E", borderRadius: 12, padding: 16, flex: 1, minWidth: "45%" },
  kpiLabel: { color: "#888", fontSize: 11, fontWeight: "600" },
  kpiValue: { color: "#FFF", fontSize: 22, fontWeight: "800", marginTop: 4 },
  alertCard: { backgroundColor: "#1A1A2E", borderRadius: 10, padding: 14, marginBottom: 8, borderLeftWidth: 3 },
  alertSeverity: { fontWeight: "700", fontSize: 11 },
  alertMsg: { color: "#DDD", fontSize: 13, marginTop: 4 },
  updatedAt: { color: "#444", fontSize: 11, textAlign: "center", marginTop: 20 },
});

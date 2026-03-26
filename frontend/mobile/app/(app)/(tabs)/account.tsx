/**
 * app/(app)/(tabs)/account.tsx — Profil + sécurité + logout
 */
import { ScrollView, View, Text, StyleSheet, TouchableOpacity, Alert } from "react-native";
import { useAuth } from "../../../store/authStore";
import { useQuery } from "@tanstack/react-query";
import { apiClient } from "../../../lib/apiClient";
import { API_ROUTES } from "@shared/constants";
import type { UserSession } from "@shared/types";

export default function AccountScreen() {
  const { user, logout } = useAuth();

  const { data: sessions } = useQuery<UserSession[]>({
    queryKey: ["sessions"],
    queryFn: () => apiClient.get(API_ROUTES.USERS_SESSIONS),
  });

  const handleLogout = () => {
    Alert.alert("Déconnexion", "Tu veux vraiment te déconnecter ?", [
      { text: "Annuler", style: "cancel" },
      { text: "Déconnexion", style: "destructive", onPress: logout },
    ]);
  };

  const revokeSession = (id: string) => {
    Alert.alert("Révoquer", "Déconnecter cet appareil ?", [
      { text: "Annuler", style: "cancel" },
      {
        text: "Révoquer",
        style: "destructive",
        onPress: () => apiClient.delete(API_ROUTES.USERS_SESSION_DELETE(id)),
      },
    ]);
  };

  return (
    <ScrollView style={styles.container} contentContainerStyle={styles.content}>
      <Text style={styles.pageTitle}>Mon Compte</Text>

      {/* Profile card */}
      <View style={styles.card}>
        <Text style={styles.label}>Nom</Text>
        <Text style={styles.value}>{user?.full_name}</Text>
        <Text style={styles.label}>Email</Text>
        <Text style={styles.value}>{user?.email}</Text>
        <View style={styles.planRow}>
          <Text style={styles.label}>Plan</Text>
          <View style={styles.planBadge}>
            <Text style={styles.planText}>{user?.plan?.toUpperCase()}</Text>
          </View>
        </View>
      </View>

      {/* Sessions */}
      <Text style={styles.sectionTitle}>Sessions actives</Text>
      {sessions?.map((s) => (
        <View key={s.id} style={styles.sessionCard}>
          <View style={{ flex: 1 }}>
            <Text style={styles.sessionName}>{s.device_name}</Text>
            <Text style={styles.sessionMeta}>{s.ip_address} · {new Date(s.last_seen).toLocaleDateString("fr-CA")}</Text>
          </View>
          {!s.is_current && (
            <TouchableOpacity onPress={() => revokeSession(s.id)}>
              <Text style={styles.revokeText}>Révoquer</Text>
            </TouchableOpacity>
          )}
          {s.is_current && <Text style={styles.currentBadge}>Actuel</Text>}
        </View>
      ))}

      {/* Logout */}
      <TouchableOpacity style={styles.logoutButton} onPress={handleLogout}>
        <Text style={styles.logoutText}>Se déconnecter</Text>
      </TouchableOpacity>
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: "#0A0A0F" },
  content: { padding: 20, paddingTop: 60 },
  pageTitle: { color: "#FFF", fontSize: 24, fontWeight: "800", marginBottom: 24 },
  card: { backgroundColor: "#1A1A2E", borderRadius: 16, padding: 20, marginBottom: 24 },
  label: { color: "#666", fontSize: 11, fontWeight: "600", marginTop: 12 },
  value: { color: "#FFF", fontSize: 15, marginTop: 2 },
  planRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "center" },
  planBadge: { backgroundColor: "#7C3AED33", paddingHorizontal: 10, paddingVertical: 4, borderRadius: 20 },
  planText: { color: "#7C3AED", fontWeight: "700", fontSize: 12 },
  sectionTitle: { color: "#FFF", fontSize: 16, fontWeight: "700", marginBottom: 10 },
  sessionCard: { backgroundColor: "#1A1A2E", borderRadius: 10, padding: 14, marginBottom: 8, flexDirection: "row", alignItems: "center" },
  sessionName: { color: "#FFF", fontWeight: "600" },
  sessionMeta: { color: "#666", fontSize: 11, marginTop: 2 },
  revokeText: { color: "#EF4444", fontWeight: "600", fontSize: 13 },
  currentBadge: { color: "#22C55E", fontWeight: "600", fontSize: 12 },
  logoutButton: { backgroundColor: "#1A1A2E", borderRadius: 12, padding: 16, alignItems: "center", marginTop: 24, borderWidth: 1, borderColor: "#EF444433" },
  logoutText: { color: "#EF4444", fontWeight: "700", fontSize: 15 },
});

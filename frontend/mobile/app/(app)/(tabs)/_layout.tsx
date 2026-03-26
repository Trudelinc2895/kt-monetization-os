/**
 * app/(app)/(tabs)/_layout.tsx — Tab navigation principale
 */
import { Tabs } from "expo-router";
import { useAuth } from "../../../store/authStore";

export default function TabLayout() {
  const { user } = useAuth();
  const isVIP = user?.plan === "pro" || user?.plan === "business";

  return (
    <Tabs
      screenOptions={{
        headerShown: false,
        tabBarStyle: {
          backgroundColor: "#0A0A0F",
          borderTopColor: "#1A1A2E",
          paddingBottom: 8,
          height: 64,
        },
        tabBarActiveTintColor: "#7C3AED",
        tabBarInactiveTintColor: "#444",
        tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
      }}
    >
      <Tabs.Screen name="home" options={{ title: "Home", tabBarIcon: () => null }} />
      <Tabs.Screen name="modules" options={{ title: "Modules", tabBarIcon: () => null }} />
      <Tabs.Screen name="activity" options={{ title: "Activité", tabBarIcon: () => null }} />
      <Tabs.Screen name="account" options={{ title: "Compte", tabBarIcon: () => null }} />
      {isVIP && (
        <Tabs.Screen name="vip" options={{ title: "VIP", tabBarIcon: () => null }} />
      )}
    </Tabs>
  );
}

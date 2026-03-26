/**
 * app/(app)/_layout.tsx — Guard auth pour toute l'app protégée
 */
import { Redirect, Stack } from "expo-router";
import { useAuth } from "../../store/authStore";
import { ActivityIndicator, View } from "react-native";

export default function AppLayout() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0A0A0F" }}>
        <ActivityIndicator color="#7C3AED" size="large" />
      </View>
    );
  }

  if (!isAuthenticated) return <Redirect href="/(auth)/login" />;

  return <Stack screenOptions={{ headerShown: false }} />;
}

/**
 * app/index.tsx — Route guard : redirect to (auth)/login or (app)/
 */
import { Redirect } from "expo-router";
import { useAuth } from "../store/authStore";
import { ActivityIndicator, View } from "react-native";

export default function Index() {
  const { isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return (
      <View style={{ flex: 1, justifyContent: "center", alignItems: "center", backgroundColor: "#0A0A0F" }}>
        <ActivityIndicator color="#7C3AED" size="large" />
      </View>
    );
  }

  return <Redirect href={isAuthenticated ? "/(app)/(tabs)/home" : "/(auth)/login"} />;
}

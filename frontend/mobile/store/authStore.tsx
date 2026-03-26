/**
 * store/authStore.ts
 * État auth global — access token en mémoire, refresh dans SecureStore
 * Pas de Redux — state minimal avec hooks React
 */
import { createContext, useContext, useState, useEffect, useCallback } from "react";
import * as SecureStore from "expo-secure-store";
import { apiClient, setAccessToken } from "../lib/apiClient";
import { TOKEN_CONFIG } from "@shared/constants";
import { API_ROUTES } from "@shared/constants";
import type { User, TokenPair, AuthState } from "@shared/types";

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

import React from "react";
export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AuthState>({
    user: null,
    accessToken: null,
    isAuthenticated: false,
    isLoading: true,
  });

  // Try to restore session on mount
  useEffect(() => {
    (async () => {
      try {
        const refreshToken = await SecureStore.getItemAsync(TOKEN_CONFIG.SECURE_STORE_KEY);
        if (!refreshToken) return setState(s => ({ ...s, isLoading: false }));

        const tokens = await apiClient.post<TokenPair>(API_ROUTES.AUTH_REFRESH, {
          refresh_token: refreshToken,
        });
        setAccessToken(tokens.access_token);
        await SecureStore.setItemAsync(TOKEN_CONFIG.SECURE_STORE_KEY, tokens.refresh_token);

        const user = await apiClient.get<User>(API_ROUTES.USERS_ME);
        setState({ user, accessToken: tokens.access_token, isAuthenticated: true, isLoading: false });
      } catch {
        await SecureStore.deleteItemAsync(TOKEN_CONFIG.SECURE_STORE_KEY);
        setState(s => ({ ...s, isLoading: false }));
      }
    })();
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    const tokens = await apiClient.post<TokenPair>(API_ROUTES.AUTH_LOGIN, { email, password });
    setAccessToken(tokens.access_token);
    await SecureStore.setItemAsync(TOKEN_CONFIG.SECURE_STORE_KEY, tokens.refresh_token);
    const user = await apiClient.get<User>(API_ROUTES.USERS_ME);
    setState({ user, accessToken: tokens.access_token, isAuthenticated: true, isLoading: false });
  }, []);

  const logout = useCallback(async () => {
    try { await apiClient.post(API_ROUTES.AUTH_LOGOUT); } catch {}
    setAccessToken(null);
    await SecureStore.deleteItemAsync(TOKEN_CONFIG.SECURE_STORE_KEY);
    setState({ user: null, accessToken: null, isAuthenticated: false, isLoading: false });
  }, []);

  const refreshUser = useCallback(async () => {
    const user = await apiClient.get<User>(API_ROUTES.USERS_ME);
    setState(s => ({ ...s, user }));
  }, []);

  return (
    <AuthContext.Provider value={{ ...state, login, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

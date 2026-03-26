/**
 * shared/api/client.ts
 * API client universel — utilisé par web, admin et mobile
 * Gère : auth headers, refresh automatique, erreurs typées
 */
import type { TokenPair, APIError } from "../types";
import { API_ROUTES } from "../constants";

export interface APIClientConfig {
  baseURL: string;
  getAccessToken: () => string | null;
  onTokenRefresh: (tokens: TokenPair) => Promise<void>;
  onAuthFailure: () => Promise<void>;
  getRefreshToken: () => Promise<string | null>;
}

export class APIClient {
  private config: APIClientConfig;
  private refreshPromise: Promise<TokenPair | null> | null = null;

  constructor(config: APIClientConfig) {
    this.config = config;
  }

  private async refreshTokens(): Promise<TokenPair | null> {
    // Deduplicate concurrent refresh calls
    if (this.refreshPromise) return this.refreshPromise;

    this.refreshPromise = (async () => {
      const refreshToken = await this.config.getRefreshToken();
      if (!refreshToken) return null;

      try {
        const res = await fetch(`${this.config.baseURL}${API_ROUTES.AUTH_REFRESH}`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ refresh_token: refreshToken }),
        });
        if (!res.ok) return null;
        const tokens: TokenPair = await res.json();
        await this.config.onTokenRefresh(tokens);
        return tokens;
      } catch {
        return null;
      } finally {
        this.refreshPromise = null;
      }
    })();

    return this.refreshPromise;
  }

  async request<T>(
    path: string,
    options: RequestInit = {},
    retry = true
  ): Promise<T> {
    const accessToken = this.config.getAccessToken();

    const headers: Record<string, string> = {
      "Content-Type": "application/json",
      ...(options.headers as Record<string, string>),
    };
    if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;

    const res = await fetch(`${this.config.baseURL}${path}`, {
      ...options,
      headers,
    });

    // Auto-refresh on 401
    if (res.status === 401 && retry) {
      const newTokens = await this.refreshTokens();
      if (!newTokens) {
        await this.config.onAuthFailure();
        throw { detail: "Session expired. Please log in again.", status_code: 401 } as APIError;
      }
      return this.request<T>(path, options, false);
    }

    if (!res.ok) {
      let error: APIError = { detail: "Unknown error", status_code: res.status };
      try {
        error = await res.json();
        error.status_code = res.status;
      } catch {}
      throw error;
    }

    // 204 No Content
    if (res.status === 204) return null as T;

    return res.json() as Promise<T>;
  }

  get<T>(path: string, options?: RequestInit) {
    return this.request<T>(path, { ...options, method: "GET" });
  }

  post<T>(path: string, body?: unknown, options?: RequestInit) {
    return this.request<T>(path, {
      ...options,
      method: "POST",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  patch<T>(path: string, body?: unknown, options?: RequestInit) {
    return this.request<T>(path, {
      ...options,
      method: "PATCH",
      body: body ? JSON.stringify(body) : undefined,
    });
  }

  delete<T>(path: string, options?: RequestInit) {
    return this.request<T>(path, { ...options, method: "DELETE" });
  }
}

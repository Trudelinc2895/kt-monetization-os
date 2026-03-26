/**
 * shared/auth/helpers.ts
 * Helpers auth partagés — décodage JWT, expiration, device ID
 * RÈGLE : jamais de stockage ici — délégué à la plateforme (web/mobile)
 */

interface JWTPayload {
  sub: string;
  exp: number;
  iat: number;
  role?: string;
  plan?: string;
}

/** Décode le payload JWT sans vérifier la signature (vérif = backend only) */
export function decodeJWT(token: string): JWTPayload | null {
  try {
    const [, payload] = token.split(".");
    const decoded = atob(payload.replace(/-/g, "+").replace(/_/g, "/"));
    return JSON.parse(decoded) as JWTPayload;
  } catch {
    return null;
  }
}

/** Retourne true si le token expire dans moins de `bufferSeconds` secondes */
export function isTokenExpiringSoon(token: string, bufferSeconds = 60): boolean {
  const payload = decodeJWT(token);
  if (!payload) return true;
  return payload.exp - bufferSeconds < Math.floor(Date.now() / 1000);
}

/** Retourne true si le token est expiré */
export function isTokenExpired(token: string): boolean {
  return isTokenExpiringSoon(token, 0);
}

/** Génère un device ID unique (UUID v4) */
export function generateDeviceId(): string {
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, (c) => {
    const r = (Math.random() * 16) | 0;
    return (c === "x" ? r : (r & 0x3) | 0x8).toString(16);
  });
}

/** Retourne un nom lisible pour l'appareil */
export function getDeviceName(platform: "ios" | "android" | "web"): string {
  const ts = new Date().toLocaleDateString("fr-CA");
  return `${platform.charAt(0).toUpperCase() + platform.slice(1)} — ${ts}`;
}

export function getApiBaseUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? process.env.NEXT_PUBLIC_API_URL;
  if (configuredUrl) return configuredUrl;
  if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
    return "https://astonachikw-production.up.railway.app";
  }
  return "http://127.0.0.1:8000";
}

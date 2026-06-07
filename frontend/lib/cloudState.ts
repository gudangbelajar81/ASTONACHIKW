import { exportUserData, importUserData } from "./userData";

function getApiUrl() {
  const configuredUrl = process.env.NEXT_PUBLIC_API_URL || process.env.NEXT_PUBLIC_BACKEND_URL;
  if (configuredUrl) return configuredUrl;
  if (typeof window !== "undefined" && window.location.hostname.endsWith(".up.railway.app")) {
    return "https://astonachikw-production.up.railway.app";
  }
  return "http://127.0.0.1:8000";
}

export function readStoredToken() {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("astrocycle_token") ?? "";
}

export async function loadCloudState() {
  const token = readStoredToken();
  if (!token) return null;

  const response = await fetch(`${getApiUrl()}/v1/app-state/me`, {
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!response.ok) return null;
  return response.json() as Promise<{ payload: ReturnType<typeof exportUserData> } | null>;
}

export async function saveCloudState() {
  const token = readStoredToken();
  if (!token) return false;

  const response = await fetch(`${getApiUrl()}/v1/app-state/me`, {
    method: "PUT",
    headers: {
      Authorization: `Bearer ${token}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ payload: exportUserData() }),
  });

  return response.ok;
}

export async function syncFromCloud() {
  const cloud = await loadCloudState();
  if (!cloud?.payload) return false;
  importUserData(cloud.payload);
  return true;
}

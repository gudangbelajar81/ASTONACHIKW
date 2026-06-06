export type ApiProviderId = "gemini" | "deepseek" | "xai" | "openai";

export type ApiKeyEntry = {
  id: string;
  label: string;
  key: string;
  status: "unknown" | "live" | "dead";
  lastChecked?: string;
};

export type ApiProviderConfig = {
  id: ApiProviderId;
  name: string;
  model: string;
  keys: ApiKeyEntry[];
};

export const API_KEYS_STORAGE_KEY = "astrocycle_api_provider_settings";

export const DEFAULT_API_PROVIDERS: ApiProviderConfig[] = [
  { id: "gemini", name: "Gemini", model: "gemini-2.5-flash", keys: [] },
  { id: "deepseek", name: "DeepSeek", model: "deepseek-chat", keys: [] },
  { id: "xai", name: "Grok / xAI", model: "grok-4.3", keys: [] },
  { id: "openai", name: "OpenAI", model: "gpt-4o-mini", keys: [] },
];

export function maskKey(key: string) {
  if (key.length <= 12) return key;
  return `${key.slice(0, 6)}...${key.slice(-4)}`;
}

export function readApiProviders(): ApiProviderConfig[] {
  if (typeof window === "undefined") return DEFAULT_API_PROVIDERS;

  try {
    const saved = JSON.parse(localStorage.getItem(API_KEYS_STORAGE_KEY) ?? "[]") as ApiProviderConfig[];
    return DEFAULT_API_PROVIDERS.map((provider) => {
      const existing = saved.find((item) => item.id === provider.id);
      return existing ? { ...provider, ...existing } : provider;
    });
  } catch {
    return DEFAULT_API_PROVIDERS;
  }
}

export function writeApiProviders(providers: ApiProviderConfig[]) {
  localStorage.setItem(API_KEYS_STORAGE_KEY, JSON.stringify(providers));
}

export function buildAiRequestConfig(providers: ApiProviderConfig[]) {
  const activeProviders = providers.filter((provider) => provider.keys.length > 0);
  return {
    ai_provider_order: activeProviders.map((provider) => provider.id),
    ai_models: Object.fromEntries(activeProviders.map((provider) => [provider.id, provider.model])),
    ai_api_keys: Object.fromEntries(
      activeProviders.map((provider) => [
        provider.id,
        provider.keys.filter((entry) => entry.status !== "dead").map((entry) => entry.key),
      ])
    ),
  };
}

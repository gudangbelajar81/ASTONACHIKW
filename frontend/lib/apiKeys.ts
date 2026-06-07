export type ApiProviderId = "kie" | "gemini" | "deepseek" | "xai" | "openai";

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

export type MarketProviderId = "idx_broker" | "foreign_flow" | "orderbook" | "custom";

export type MarketProviderConfig = {
  id: MarketProviderId;
  name: string;
  endpoint: string;
  apiKey: string;
  status: "unknown" | "live" | "dead";
  notes: string;
  enabled: boolean;
  lastChecked?: string;
};

export const API_KEYS_STORAGE_KEY = "astrocycle_api_provider_settings";
export const MARKET_PROVIDER_STORAGE_KEY = "astrocycle_market_provider_settings";

export const DEFAULT_API_PROVIDERS: ApiProviderConfig[] = [
  { id: "kie", name: "Kie.ai / Claude", model: "claude-opus-4-6", keys: [] },
  { id: "gemini", name: "Gemini", model: "gemini-2.5-flash", keys: [] },
  { id: "deepseek", name: "DeepSeek", model: "deepseek-chat", keys: [] },
  { id: "xai", name: "Grok / xAI", model: "grok-4.3", keys: [] },
  { id: "openai", name: "OpenAI", model: "gpt-4o-mini", keys: [] },
];

export const DEFAULT_MARKET_PROVIDERS: MarketProviderConfig[] = [
  {
    id: "idx_broker",
    name: "IDX Broker Summary",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Untuk broker net buy/sell, akumulasi bandar, dan distribusi.",
    enabled: false,
  },
  {
    id: "foreign_flow",
    name: "Foreign Flow",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Untuk foreign net buy/sell dan aliran dana asing.",
    enabled: false,
  },
  {
    id: "orderbook",
    name: "Order Book / Running Trade",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Untuk order book imbalance, big lot, dan running trade.",
    enabled: false,
  },
  {
    id: "custom",
    name: "Custom Provider",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Untuk provider data lain yang formatnya nanti bisa dipetakan.",
    enabled: false,
  },
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

export function readMarketProviders(): MarketProviderConfig[] {
  if (typeof window === "undefined") return DEFAULT_MARKET_PROVIDERS;

  try {
    const saved = JSON.parse(localStorage.getItem(MARKET_PROVIDER_STORAGE_KEY) ?? "[]") as MarketProviderConfig[];
    return DEFAULT_MARKET_PROVIDERS.map((provider) => {
      const existing = saved.find((item) => item.id === provider.id);
      return existing ? { ...provider, ...existing } : provider;
    });
  } catch {
    return DEFAULT_MARKET_PROVIDERS;
  }
}

export function writeMarketProviders(providers: MarketProviderConfig[]) {
  localStorage.setItem(MARKET_PROVIDER_STORAGE_KEY, JSON.stringify(providers));
}

export function buildMarketProviderConfig(providers: MarketProviderConfig[]) {
  return {
    market_data_providers: providers
      .filter((provider) => provider.enabled && provider.endpoint && provider.apiKey)
      .map((provider) => ({
        id: provider.id,
        endpoint: provider.endpoint,
        api_key: provider.apiKey,
      })),
  };
}

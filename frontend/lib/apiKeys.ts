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

export type MarketProviderId = 
  | "idx_bandar_accumulation" 
  | "idx_foreign_flow" 
  | "idx_orderbook" 
  | "idx_broker_summary"
  | "marketflow_global"
  | "macro_calendar"
  | "macro_bi_rate"
  | "news_rss"
  | "custom";

export type ProviderCategory = "idx" | "macro" | "news" | "global" | "custom";

export type MarketProviderConfig = {
  id: MarketProviderId;
  name: string;
  category: ProviderCategory;
  endpoint: string;
  apiKey: string;
  status: "unknown" | "live" | "dead";
  notes: string;
  enabled: boolean;
  lastChecked?: string;
  placeholderEndpoint?: string;
};

export type MediaProviderId = "kie_image" | "kie_video";

export type MediaProviderConfig = {
  id: MediaProviderId;
  name: string;
  apiKey: string;
  model: string;
  status: "unknown" | "live" | "dead";
  notes: string;
  enabled: boolean;
  lastChecked?: string;
  lastCheckDetail?: string;
};

export const API_KEYS_STORAGE_KEY = "astrocycle_api_provider_settings";
export const MARKET_PROVIDER_STORAGE_KEY = "astrocycle_market_provider_settings";
export const MEDIA_PROVIDER_STORAGE_KEY = "astrocycle_media_provider_settings";

export const DEFAULT_API_PROVIDERS: ApiProviderConfig[] = [
  { id: "kie", name: "Kie.ai / Claude", model: "claude-opus-4-6", keys: [] },
  { id: "gemini", name: "Gemini", model: "gemini-2.5-flash", keys: [] },
  { id: "deepseek", name: "DeepSeek", model: "deepseek-chat", keys: [] },
  { id: "xai", name: "Grok / xAI", model: "grok-4.3", keys: [] },
  { id: "openai", name: "OpenAI", model: "gpt-4o-mini", keys: [] },
];

export const DEFAULT_MARKET_PROVIDERS: MarketProviderConfig[] = [
  // IDX Providers
  {
    id: "idx_bandar_accumulation",
    name: "IDX Bandar Accumulation",
    category: "idx",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Analisis akumulasi dan distribusi bandar untuk saham IDX.",
    placeholderEndpoint: "https://indonesia-stock-exchange-idx.p.rapidapi.com/api/analysis/bandar/accumulation/{ticker}?days={days}",
    enabled: false,
  },
  {
    id: "idx_broker_summary",
    name: "IDX Broker Summary",
    category: "idx",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Broker net buy/sell dan top broker activity.",
    placeholderEndpoint: "https://indonesia-stock-exchange-idx.p.rapidapi.com/api/broker/summary/{ticker}",
    enabled: false,
  },
  {
    id: "idx_foreign_flow",
    name: "IDX Foreign Flow",
    category: "idx",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Foreign net buy/sell dan aliran dana asing di IDX.",
    placeholderEndpoint: "https://indonesia-stock-exchange-idx.p.rapidapi.com/api/foreign/flow/{ticker}",
    enabled: false,
  },
  {
    id: "idx_orderbook",
    name: "IDX Order Book / Running Trade",
    category: "idx",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Order book imbalance, big lot, dan running trade realtime.",
    placeholderEndpoint: "https://indonesia-stock-exchange-idx.p.rapidapi.com/api/orderbook/{ticker}",
    enabled: false,
  },
  // Global Market Providers
  {
    id: "marketflow_global",
    name: "MarketFlow Global Data",
    category: "global",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Data pasar global dari MarketFlow API (US, Asia, Europe).",
    placeholderEndpoint: "https://marketflow.p.rapidapi.com/api/market/{symbol}",
    enabled: false,
  },
  // Macro Providers
  {
    id: "macro_calendar",
    name: "Kalender Ekonomi",
    category: "macro",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Kalender ekonomi global dan Indonesia (GDP, inflasi, suku bunga).",
    placeholderEndpoint: "https://economic-calendar.p.rapidapi.com/api/events",
    enabled: false,
  },
  {
    id: "macro_bi_rate",
    name: "BI Rate & Macro Indonesia",
    category: "macro",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "BI Rate, inflasi, USD/IDR, dan indikator makro Indonesia.",
    placeholderEndpoint: "https://indonesia-macro.p.rapidapi.com/api/indicators",
    enabled: false,
  },
  // News Providers
  {
    id: "news_rss",
    name: "Berita Ekonomi RSS",
    category: "news",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Feed berita ekonomi dan pasar dari berbagai sumber RSS.",
    placeholderEndpoint: "https://news-api.p.rapidapi.com/api/rss/finance",
    enabled: false,
  },
  // Custom Provider
  {
    id: "custom",
    name: "Custom Provider",
    category: "custom",
    endpoint: "",
    apiKey: "",
    status: "unknown",
    notes: "Provider data custom yang formatnya bisa dipetakan sesuai kebutuhan.",
    enabled: false,
  },
];

export const DEFAULT_MEDIA_PROVIDERS: MediaProviderConfig[] = [
  {
    id: "kie_image",
    name: "Kie Image Studio",
    apiKey: "",
    model: "gpt4o-image",
    status: "unknown",
    notes: "Text-to-image dan image editing lewat Kie.ai.",
    enabled: false,
  },
  {
    id: "kie_video",
    name: "Kie Video Studio",
    apiKey: "",
    model: "runway-duration-5-generate",
    status: "unknown",
    notes: "Text-to-video dan image-to-video lewat Kie.ai.",
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

export function readMediaProviders(): MediaProviderConfig[] {
  if (typeof window === "undefined") return DEFAULT_MEDIA_PROVIDERS;

  try {
    const saved = JSON.parse(localStorage.getItem(MEDIA_PROVIDER_STORAGE_KEY) ?? "[]") as MediaProviderConfig[];
    return DEFAULT_MEDIA_PROVIDERS.map((provider) => {
      const existing = saved.find((item) => item.id === provider.id);
      return existing ? { ...provider, ...existing } : provider;
    });
  } catch {
    return DEFAULT_MEDIA_PROVIDERS;
  }
}

export function writeMediaProviders(providers: MediaProviderConfig[]) {
  localStorage.setItem(MEDIA_PROVIDER_STORAGE_KEY, JSON.stringify(providers));
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

export function buildMediaProviderConfig(providers: MediaProviderConfig[]) {
  return {
    media_providers: providers
      .filter((provider) => provider.enabled && provider.apiKey && provider.model)
      .map((provider) => ({
        id: provider.id,
        model: provider.model,
        api_key: provider.apiKey,
      })),
  };
}

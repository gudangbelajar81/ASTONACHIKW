"""
AI Provider Manager with Key Rotation
Handles multiple AI providers with automatic key rotation based on availability.
"""

import json
import time
import urllib.error
import urllib.request
from typing import Dict, List, Optional, Tuple
from openai import OpenAI, APIError
from backend.app.core.config import settings


class AIProvider:
    """Base class for AI providers."""
    
    def __init__(self, name: str, api_keys: List[str], model: str):
        self.name = name
        self.api_keys = api_keys
        self.model = model
        self.current_key_index = 0
        self.key_status = {key: True for key in api_keys}  # True = working, False = dead
        self.last_used = {key: 0 for key in api_keys}
    
    def get_next_key(self) -> Optional[str]:
        """Get the next available API key with rotation."""
        if not self.api_keys:
            return None
        
        # Try to find a working key
        for _ in range(len(self.api_keys)):
            key = self.api_keys[self.current_key_index]
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            
            if self.key_status.get(key, True):
                self.last_used[key] = time.time()
                return key
        
        # If no working keys found, try all keys
        for key in self.api_keys:
            if self.test_key(key):
                self.key_status[key] = True
                self.last_used[key] = time.time()
                return key
        
        return None
    
    def mark_key_dead(self, key: str):
        """Mark an API key as dead."""
        self.key_status[key] = False
    
    def test_key(self, key: str) -> bool:
        """Test if an API key is valid."""
        raise NotImplementedError("Subclasses must implement test_key")
    
    def generate(self, prompt: str, system_message: str) -> str:
        """Generate a response using the provider."""
        raise NotImplementedError("Subclasses must implement generate")


class KIEProvider(AIProvider):
    """KIE AI provider."""
    
    def test_key(self, key: str) -> bool:
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.kie.ai/api/v1/chat/credit",
                    headers={"Authorization": f"Bearer {key}"},
                    method="GET",
                ),
                timeout=45,
            )
            body = json.loads(response.read().decode("utf-8"))
            return response.status == 200 and body.get("code") == 200
        except Exception:
            return False
    
    def generate(self, prompt: str, system_message: str) -> str:
        key = self.get_next_key()
        if not key:
            raise ValueError(f"No working API keys for {self.name}")
        
        try:
            response = urllib.request.urlopen(
                urllib.request.Request(
                    "https://api.kie.ai/api/v1/chat/completions",
                    data=json.dumps({
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_message},
                            {"role": "user", "content": prompt}
                        ],
                        "temperature": 0.7,
                        "max_tokens": 4000,
                        "stream": False
                    }).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {key}",
                        "Content-Type": "application/json"
                    },
                    method="POST",
                ),
                timeout=45,
            )
            body = json.loads(response.read().decode("utf-8"))
            if response.status != 200 or body.get("code") != 200:
                self.mark_key_dead(key)
                raise ValueError(body.get("msg") or f"{self.name} API error")
            
            return body["choices"][0]["message"]["content"]
        except Exception as e:
            self.mark_key_dead(key)
            raise ValueError(f"{self.name} API call failed: {e}")


class OpenAIProvider(AIProvider):
    """OpenAI compatible provider."""
    
    def __init__(self, name: str, api_keys: List[str], model: str, base_url: str = "https://api.openai.com/v1"):
        super().__init__(name, api_keys, model)
        self.base_url = base_url
    
    def test_key(self, key: str) -> bool:
        try:
            client = OpenAI(api_key=key, base_url=self.base_url)
            client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": "Test"}],
                max_tokens=5
            )
            return True
        except Exception:
            return False
    
    def generate(self, prompt: str, system_message: str) -> str:
        key = self.get_next_key()
        if not key:
            raise ValueError(f"No working API keys for {self.name}")
        
        try:
            client = OpenAI(api_key=key, base_url=self.base_url)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=4000
            )
            return response.choices[0].message.content
        except Exception as e:
            self.mark_key_dead(key)
            raise ValueError(f"{self.name} API call failed: {e}")


class GeminiProvider(AIProvider):
    """Google Gemini provider."""
    
    def test_key(self, key: str) -> bool:
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.model)
            response = model.generate_content("Test")
            return response.text is not None
        except Exception:
            return False
    
    def generate(self, prompt: str, system_message: str) -> str:
        key = self.get_next_key()
        if not key:
            raise ValueError(f"No working API keys for {self.name}")
        
        try:
            import google.generativeai as genai
            genai.configure(api_key=key)
            model = genai.GenerativeModel(self.model)
            full_prompt = f"{system_message}\n\n{prompt}"
            response = model.generate_content(full_prompt)
            return response.text
        except Exception as e:
            self.mark_key_dead(key)
            raise ValueError(f"{self.name} API call failed: {e}")


class AIProviderManager:
    """Manages multiple AI providers with automatic rotation."""
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self.provider_order = []
        self.system_message = (
            "Anda adalah narator data pasar untuk trader ritel di Asia. "
            "Anda tidak boleh menebak, mengarang harga, atau membuat prediksi tanpa data. "
            "Gunakan hanya data yang diberikan: OHLCV, indikator teknikal, bandarmology, macro, sentiment, "
            "backtest result, dan score components. Jika data tidak cukup, katakan data tidak cukup. "
            "Selalu jawab dalam Bahasa Indonesia yang jelas, ringkas, dan dapat ditindaklanjuti."
        )
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Initialize all configured providers."""
        # Parse provider order
        self.provider_order = [p.strip().lower() for p in settings.AI_PROVIDER_ORDER.split(",") if p.strip()]
        
        # Initialize each provider
        provider_configs = [
            # KIE AI
            ("kie", settings.KIE_API_KEY, settings.KIE_MODEL, KIEProvider),
            
            # OpenAI
            ("openai", settings.OPENAI_API_KEY, settings.OPENAI_MODEL, 
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.openai.com/v1")),
            
            # Gemini
            ("gemini", settings.GEMINI_API_KEY, settings.GEMINI_MODEL, GeminiProvider),
            
            # DeepSeek
            ("deepseek", settings.DEEPSEEK_API_KEY, settings.DEEPSEEK_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.deepseek.com")),
            
            # DeepSeek V3
            ("deepseek_v3", settings.DEEPSEEK_V3_API_KEY, settings.DEEPSEEK_V3_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.deepseek.com")),
            
            # xAI (Grok)
            ("xai", settings.XAI_API_KEY, settings.XAI_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.x.ai/v1")),
            
            # Qwen Coder
            ("qwen_coder", settings.QWEN_CODER_API_KEY, settings.QWEN_CODER_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://dashscope.aliyuncs.com/compatible-mode/v1")),
            
            # Mistral
            ("mistral", settings.MISTRAL_API_KEY, settings.MISTRAL_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.mistral.ai/v1")),
            
            # Claude Sonnet
            ("claude_sonnet", settings.CLAUDE_SONNET_API_KEY, settings.CLAUDE_SONNET_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.anthropic.com/v1")),
            
            # GPT-5
            ("gpt5", settings.GPT5_API_KEY, settings.GPT5_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.openai.com/v1")),
            
            # Kimi
            ("kimi", settings.KIMI_API_KEY, settings.KIMI_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.moonshot.cn/v1")),
            
            # Kimi Free
            ("kimi_free", settings.KIMI_FREE_API_KEY, settings.KIMI_FREE_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.moonshot.cn/v1")),
            
            # Qwen Coder Free
            ("qwen_coder_free", settings.QWEN_CODER_FREE_API_KEY, settings.QWEN_CODER_FREE_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://dashscope.aliyuncs.com/compatible-mode/v1")),
            
            # Gemma
            ("gemma", settings.GEMMA_API_KEY, settings.GEMMA_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.gemini.google.com/v1")),
            
            # GPT-5 o3
            ("gpt5_o3", settings.GPT5_O3_API_KEY, settings.GPT5_O3_MODEL,
             lambda n, k, m: OpenAIProvider(n, k, m, "https://api.openai.com/v1")),
        ]
        
        for name, api_key_str, model, provider_class in provider_configs:
            api_keys = [k.strip() for k in api_key_str.split(",") if k.strip()]
            if api_keys:
                if callable(provider_class):
                    provider = provider_class(name, api_keys, model)
                else:
                    provider = provider_class(name, api_keys, model)
                self.providers[name] = provider
    
    def generate_with_providers(self, prompt: str, provider_order: Optional[List[str]] = None) -> Tuple[str, str]:
        """
        Generate a response using providers in order.
        Returns (provider_name, response_text)
        """
        order = provider_order or self.provider_order
        
        for provider_name in order:
            provider = self.providers.get(provider_name)
            if not provider:
                continue
            
            try:
                response = provider.generate(prompt, self.system_message)
                return provider_name, response
            except ValueError as e:
                print(f"Provider {provider_name} failed: {e}")
                continue
        
        raise ValueError("All AI providers failed. Please check API keys and connectivity.")
    
    def test_all_providers(self) -> Dict[str, List[Dict[str, str]]]:
        """Test all providers and return status."""
        results = {}
        
        for name, provider in self.providers.items():
            provider_results = []
            for key in provider.api_keys:
                status = "working" if provider.test_key(key) else "dead"
                provider_results.append({
                    "key": f"{key[:10]}...{key[-4:]}" if len(key) > 20 else key,
                    "status": status,
                    "last_used": provider.last_used.get(key, 0)
                })
            results[name] = provider_results
        
        return results


# Global instance
provider_manager = AIProviderManager()
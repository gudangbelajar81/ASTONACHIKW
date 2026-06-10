import asyncio
from backend.app.services.ai_analyst import test_provider_key

def test():
    try:
        test_provider_key("openai_compatible", "invalid-key", "gpt-3.5-turbo", "https://api.openai.com/v1")
        print("Success openai")
    except Exception as e:
        print(f"Error openai: {e}")

    try:
        test_provider_key("kie", "invalid-key", "claude-opus-4-6", "https://api.kie.ai/v1")
        print("Success kie")
    except Exception as e:
        print(f"Error kie: {e}")

if __name__ == "__main__":
    test()

import json
import urllib.error
import urllib.request
from typing import Dict, Any, List, Optional
from openai import OpenAI, APIError
from backend.app.core.config import settings

AI_SYSTEM_MESSAGE = (
    "Anda adalah narator data pasar untuk trader ritel di Asia. "
    "Anda tidak boleh menebak, mengarang harga, atau membuat prediksi tanpa data. "
    "Gunakan hanya data yang diberikan: OHLCV, indikator teknikal, bandarmology, macro, sentiment, "
    "backtest result, dan score components. Jika data tidak cukup, katakan data tidak cukup. "
    "Selalu jawab dalam Bahasa Indonesia yang jelas, ringkas, dan dapat ditindaklanjuti."
)


class AnalystInput:
    def __init__(
        self,
        ticker: str,
        composite_cycle_data: List[Dict[str, Any]],
        turning_points: List[Dict[str, Any]],
        scanner_results: Optional[List[Dict[str, Any]]] = None,
        ai_provider_order: Optional[List[str]] = None,
        ai_api_keys: Optional[Dict[str, List[str]]] = None,
        ai_models: Optional[Dict[str, str]] = None,
        ai_base_urls: Optional[Dict[str, str]] = None,
        data_context: Optional[Dict[str, Any]] = None,
    ):
        self.ticker = ticker
        self.composite_cycle_data = composite_cycle_data
        self.turning_points = turning_points
        self.scanner_results = scanner_results or []
        self.ai_provider_order = ai_provider_order or []
        self.ai_api_keys = ai_api_keys or {}
        self.ai_models = ai_models or {}
        self.ai_base_urls = ai_base_urls or {}
        self.data_context = data_context or {}


class AnalystOutput:
    def __init__(
        self,
        ticker: str,
        summary: str,
        cycle_explanation: str,
        turning_points_explanation: str,
        scan_explanation: str,
        outlook: str,
    ):
        self.ticker = ticker
        self.summary = summary
        self.cycle_explanation = cycle_explanation
        self.turning_points_explanation = turning_points_explanation
        self.scan_explanation = scan_explanation
        self.outlook = outlook

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ticker": self.ticker,
            "summary": self.summary,
            "cycle_explanation": self.cycle_explanation,
            "turning_points_explanation": self.turning_points_explanation,
            "scan_explanation": self.scan_explanation,
            "outlook": self.outlook,
        }


def format_analyst_prompt(analyst_input: AnalystInput) -> str:
    """
    Format input data into a structured prompt for OpenAI.

    Args:
        analyst_input: AnalystInput object with market data

    Returns:
        Formatted prompt string
    """
    # Extract recent cycle data
    recent_cycle = analyst_input.composite_cycle_data[-30:] if analyst_input.composite_cycle_data else []
    cycle_values = [d.get("value", 0) for d in recent_cycle]
    cycle_dates = [d.get("date", "") for d in recent_cycle]
    current_trend = "Netral"
    if cycle_values:
        current_trend = "Positif" if cycle_values[-1] > 0 else "Negatif"

    # Format turning points
    turning_points_str = ""
    if analyst_input.turning_points:
        turning_points_str = "\n".join(
            [
                f"- {tp['date']}: {tp['type']} (Kekuatan: {tp['strength']}/100)"
                for tp in sorted(
                    analyst_input.turning_points, key=lambda x: x.get("date", "")
                )[-5:]
            ]
        )

    # Format scanner results
    scanner_str = ""
    if analyst_input.scanner_results:
        scanner_str = "\n".join(
            [
                f"- {r['cycle']}: Korelasi {r['correlation']:.2f}, "
                f"Jeda {r['lag_days']} hari, Akurasi {r['accuracy']:.0%}, Skor {r['score']:.3f}"
                for r in analyst_input.scanner_results[:5]
            ]
        )

    context_json = json.dumps(analyst_input.data_context, ensure_ascii=False, indent=2, default=str)
    has_structured_context = bool(analyst_input.data_context)

    prompt = f"""Anda adalah NARATOR DATA, bukan peramal dan bukan penebak.

ATURAN WAJIB:
- Jangan membuat prediksi tanpa data.
- Gunakan hanya data yang diberikan di bagian DATA TERSTRUKTUR dan DATA SIKLUS.
- Data yang boleh dipakai hanya: OHLCV, indikator teknikal, bandarmology, macro, sentiment, backtest result, dan score components.
- Jangan menambah harga, target, stop loss, probabilitas, alasan, atau risiko yang tidak ada di data.
- Jelaskan alasan sinyal, risiko, invalidation, dan skenario hanya jika data tersedia.
- Jika data tidak cukup, tulis dengan jelas: "Data tidak cukup untuk membuat analisis yang bertanggung jawab."
- AI Analyst harus menjadi narator data, bukan penebak.

Analisis data pasar berikut dan berikan penjelasan yang mudah dipahami dalam Bahasa Indonesia:

MARKET TICKER: {analyst_input.ticker}

DATA TERSTRUKTUR TERSEDIA: {"YA" if has_structured_context else "TIDAK"}
DATA TERSTRUKTUR:
{context_json if has_structured_context else "{}"}

COMPOSITE CYCLE DATA (Last 30 days):
Dates: {', '.join(str(d) for d in cycle_dates[-10:])}
Values: {', '.join(f'{v:.2f}' for v in cycle_values[-10:])}
Tren Saat Ini: {current_trend}

RECENT TURNING POINTS:
{turning_points_str if turning_points_str else "Tidak ada titik balik terdeteksi"}

TOP PLANETARY COMBINATIONS:
{scanner_str if scanner_str else "Tidak ada hasil scanner tersedia"}

Berikan analisis dalam format berikut. Gunakan judul bagian persis seperti ini agar sistem bisa membacanya:

1. **Summary** (1-2 kalimat): Ringkasan singkat kondisi siklus saat ini
2. **Cycle Explanation** (2-3 kalimat): Jelaskan tren siklus komposit dan maknanya untuk pasar
3. **Turning Points Explanation** (2-3 kalimat): Analisis puncak/dasar terbaru dan signifikansinya
4. **Scanner Insights** (2-3 kalimat): Sorot kombinasi planet terkuat dan nilai prediktifnya
5. **Market Outlook** (2-3 kalimat): Jelaskan skenario, risiko, dan invalidation berdasarkan data. Jika data tidak cukup, katakan data tidak cukup.

Wajib jawab dalam Bahasa Indonesia.
Tetap spesifik tentang data yang tersedia.
Jangan memberikan rekomendasi beli/jual jika data pendukung tidak tersedia."""

    return prompt


def split_keys(raw_keys: str | list[str]) -> list[str]:
    if isinstance(raw_keys, list):
        return [key.strip() for key in raw_keys if key and key.strip()]
    return [key.strip() for key in raw_keys.split(",") if key.strip()]


def provider_order(override: Optional[List[str]] = None) -> list[str]:
    if override:
        return [provider.strip().lower() for provider in override if provider.strip()]
    return [provider.strip().lower() for provider in settings.AI_PROVIDER_ORDER.split(",") if provider.strip()]


def parse_generated_analysis(ticker: str, response_text: str) -> AnalystOutput:
    sections = parse_analysis_response(response_text)
    if not any(value.strip() for value in sections.values()):
        clean_text = response_text.strip()
        return AnalystOutput(
            ticker=ticker,
            summary=clean_text,
            cycle_explanation="Analisis model diterima, tetapi format bagian tidak lengkap.",
            turning_points_explanation="Gunakan titik balik pada dashboard sebagai zona perhatian tambahan.",
            scan_explanation="Gunakan daftar scanner sebagai konfirmasi pendukung.",
            outlook="Tetap kombinasikan pembacaan AI dengan manajemen risiko.",
        )
    return AnalystOutput(
        ticker=ticker,
        summary=sections.get("summary", ""),
        cycle_explanation=sections.get("cycle_explanation", ""),
        turning_points_explanation=sections.get("turning_points_explanation", ""),
        scan_explanation=sections.get("scan_explanation", ""),
        outlook=sections.get("outlook", ""),
    )


def call_openai_compatible(
    *,
    api_key: str,
    model: str,
    prompt: str,
    base_url: str | None = None,
) -> str:
    client_kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url:
        client_kwargs["base_url"] = base_url
    client = OpenAI(**client_kwargs)
    message = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": AI_SYSTEM_MESSAGE},
            {"role": "user", "content": prompt},
        ],
        temperature=0.1,
        max_tokens=1500,
    )
    return message.choices[0].message.content or ""


def call_gemini(*, api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": AI_SYSTEM_MESSAGE}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.1, "maxOutputTokens": 1500},
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))

    candidates = body.get("candidates") or []
    if not candidates:
        raise ValueError("Gemini tidak mengembalikan kandidat jawaban.")
    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    if not text.strip():
        raise ValueError("Gemini mengembalikan jawaban kosong.")
    return text


def call_kie_claude(*, api_key: str, model: str, prompt: str) -> str:
    url = "https://api.kie.ai/claude/v1/messages"
    payload = {
        "model": model,
        "max_tokens": 1500,
        "temperature": 0.1,
        "system": AI_SYSTEM_MESSAGE,
        "messages": [
            {
                "role": "user",
                "content": prompt,
            }
        ],
    }
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "X-Api-Key": api_key,
            "anthropic-version": "2023-06-01",
        },
        method="POST",
    )

    with urllib.request.urlopen(request, timeout=45) as response:
        body = json.loads(response.read().decode("utf-8"))

    content = body.get("content") or []
    text = "".join(block.get("text", "") for block in content if isinstance(block, dict))
    if not text.strip():
        raise ValueError("Kie.ai Claude mengembalikan jawaban kosong.")
    return text


def local_analysis(analyst_input: AnalystInput) -> AnalystOutput:
    context = analyst_input.data_context or {}
    score_components = context.get("score_components") or context.get("score_breakdown") or {}
    backtest = context.get("backtest_result") or context.get("backtest") or {}
    scenario = context.get("scenario") or {}
    data_quality = context.get("data_quality") or {}
    has_enough_data = bool(context) and (bool(score_components) or bool(backtest) or bool(scenario))

    if not has_enough_data:
        message = (
            "Data tidak cukup untuk membuat analisis yang bertanggung jawab. "
            "AI Analyst membutuhkan OHLCV/indikator teknikal, bandarmology, macro, sentiment, backtest result, "
            "atau score components sebelum menarasikan sinyal."
        )
        return AnalystOutput(
            ticker=analyst_input.ticker,
            summary=message,
            cycle_explanation="Data siklus saja tidak cukup untuk membuat narasi prediksi harga.",
            turning_points_explanation="Titik balik hanya boleh dipakai sebagai konteks tambahan jika didukung data harga dan risiko.",
            scan_explanation="Scanner tidak boleh menjadi dasar tunggal keputusan tanpa validasi backtest dan komponen skor.",
            outlook="Data tidak cukup. Tidak ada skenario, risiko, atau invalidation yang dapat dinarasikan secara bertanggung jawab.",
        )

    signal = context.get("signal") or context.get("recommended_action") or "belum ada sinyal eksplisit"
    confidence = context.get("confidence", "tidak tersedia")
    risks = context.get("main_risks") or context.get("risks") or []
    reasons = context.get("main_reasons") or context.get("reasons") or []
    invalidation = scenario.get("invalidation_level") or context.get("stop_loss")
    target = scenario.get("bullish_target") or context.get("target_1")
    entry = scenario.get("entry_zone_low") or context.get("entry_zone")

    if isinstance(entry, list):
        entry_text = " - ".join(str(value) for value in entry[:2])
    else:
        entry_text = str(entry) if entry is not None else "tidak tersedia"

    risk_text = "; ".join(str(item) for item in risks[:3]) if risks else "Risiko spesifik belum tersedia di data."
    reason_text = "; ".join(str(item) for item in reasons[:3]) if reasons else "Alasan sinyal belum tersedia di data."
    sample_count = backtest.get("sample_count") or context.get("validation", {}).get("sample_size")

    return AnalystOutput(
        ticker=analyst_input.ticker,
        summary=(
            f"Sinyal data untuk {analyst_input.ticker}: {signal}, dengan confidence {confidence}. "
            f"Ringkasan ini hanya menarasikan komponen data yang tersedia."
        ),
        cycle_explanation=(
            f"Alasan utama dari score components: {reason_text} "
            f"Kualitas data: {json.dumps(data_quality, ensure_ascii=False) if data_quality else 'belum lengkap'}."
        ),
        turning_points_explanation=(
            f"Invalidation/stop loss yang tersedia: {invalidation if invalidation is not None else 'belum tersedia'}. "
            "Jika level ini ditembus, skenario harus dianggap batal atau perlu dihitung ulang."
        ),
        scan_explanation=(
            f"Backtest sample: {sample_count if sample_count is not None else 'belum tersedia'}. "
            "Komponen skor dan backtest dipakai sebagai bukti pendukung, bukan jaminan hasil."
        ),
        outlook=(
            f"Skenario data: entry {entry_text}, target {target if target is not None else 'belum tersedia'}, "
            f"risiko utama: {risk_text}"
        ),
    )


def legacy_cycle_analysis(analyst_input: AnalystInput) -> AnalystOutput:
    recent_cycle = analyst_input.composite_cycle_data[-30:] if analyst_input.composite_cycle_data else []
    latest_value = recent_cycle[-1].get("value", 0) if recent_cycle else 0
    previous_value = recent_cycle[-7].get("value", latest_value) if len(recent_cycle) >= 7 else latest_value
    direction = "menguat" if latest_value >= previous_value else "melemah"
    bias = "positif" if latest_value > 0 else "negatif" if latest_value < 0 else "netral"
    top_scanner = analyst_input.scanner_results[0] if analyst_input.scanner_results else None
    top_turning = analyst_input.turning_points[0] if analyst_input.turning_points else None

    return AnalystOutput(
        ticker=analyst_input.ticker,
        summary=(
            f"{analyst_input.ticker} menunjukkan bias siklus {bias} dengan nilai terbaru "
            f"{latest_value:.3f}. Dalam beberapa sesi terakhir, siklus tampak {direction}."
        ),
        cycle_explanation=(
            "Siklus komposit membaca gabungan beberapa pasangan planet untuk melihat tekanan momentum. "
            "Nilai di atas nol cenderung mendukung bias konstruktif, sedangkan nilai di bawah nol menandakan area yang lebih defensif."
        ),
        turning_points_explanation=(
            f"Titik balik terdekat berada pada {top_turning.get('date')} dengan tipe {top_turning.get('type')} "
            f"dan kekuatan {top_turning.get('strength')}/100. Gunakan tanggal ini sebagai zona perhatian, bukan sinyal masuk tunggal."
            if top_turning
            else "Belum ada titik balik kuat yang terdeteksi dari data saat ini. Fokus utama tetap pada perubahan arah garis komposit."
        ),
        scan_explanation=(
            f"Kombinasi teratas saat ini adalah {top_scanner.get('cycle')} dengan skor {top_scanner.get('score', 0):.3f}. "
            "Semakin tinggi skor, semakin layak kombinasi itu dipantau sebagai konfirmasi tambahan."
            if top_scanner
            else "Scanner belum mengembalikan kombinasi dominan, sehingga pembacaan utama memakai siklus komposit."
        ),
        outlook=(
            "Prospek masih perlu dibaca bertahap: tunggu konfirmasi dari arah siklus, area titik balik, "
            "dan disiplin risiko sebelum mengambil keputusan trading."
        ),
    )


def get_provider_keys(provider: str, overrides: Optional[Dict[str, List[str]]] = None) -> list[str]:
    if overrides and provider in overrides:
        return split_keys(overrides[provider])
    if provider == "kie":
        return split_keys(settings.KIE_API_KEY)
    if provider == "openai":
        return split_keys(settings.OPENAI_API_KEY)
    if provider == "gemini":
        return split_keys(settings.GEMINI_API_KEY)
    if provider in {"deepseek", "deepseek-ai"}:
        return split_keys(settings.DEEPSEEK_API_KEY)
    if provider in {"xai", "grok"}:
        return split_keys(settings.XAI_API_KEY)
    return []


def get_provider_model(provider: str, overrides: Optional[Dict[str, str]] = None) -> str:
    if overrides and overrides.get(provider):
        return overrides[provider]
    if provider == "kie":
        return settings.KIE_MODEL
    if provider == "openai":
        return settings.OPENAI_MODEL
    if provider == "gemini":
        return settings.GEMINI_MODEL
    if provider in {"deepseek", "deepseek-ai"}:
        return settings.DEEPSEEK_MODEL
    if provider in {"xai", "grok"}:
        return settings.XAI_MODEL
    return ""


def generate_with_provider(
    provider: str,
    prompt: str,
    key_overrides: Optional[Dict[str, List[str]]] = None,
    model_overrides: Optional[Dict[str, str]] = None,
    base_url_overrides: Optional[Dict[str, str]] = None,
) -> str:
    """Generate using provider with automatic key rotation."""
    normalized_provider = provider.strip().lower()
    keys = get_provider_keys(normalized_provider, key_overrides)
    model = get_provider_model(normalized_provider, model_overrides)
    base_url = base_url_overrides.get(normalized_provider) if base_url_overrides else None
    
    if not keys:
        raise ValueError(f"No API keys available for provider: {provider}")
    
    # Try each key
    for key in keys:
        try:
            if normalized_provider == "kie":
                return call_kie_claude(api_key=key, model=model, prompt=prompt)
            elif normalized_provider == "gemini":
                return call_gemini(api_key=key, model=model, prompt=prompt)
            elif normalized_provider in {"openai", "openai_compatible"} or base_url:
                # Use custom base_url if provided
                return call_openai_compatible(
                    api_key=key,
                    model=model,
                    prompt=prompt,
                    base_url=base_url if base_url else ("https://api.openai.com/v1" if normalized_provider == "openai" else None),
                )
            elif normalized_provider in {"deepseek", "deepseek-ai"}:
                return call_openai_compatible(
                    api_key=key,
                    model=model,
                    prompt=prompt,
                    base_url="https://api.deepseek.com",
                )
            elif normalized_provider in {"xai", "grok"}:
                return call_openai_compatible(
                    api_key=key,
                    model=model,
                    prompt=prompt,
                    base_url="https://api.x.ai/v1",
                )
            else:
                raise ValueError(f"Unknown provider: {provider}")
        except Exception as e:
            print(f"Key failed for {provider}: {e}")
            continue
    
    raise ValueError(f"All keys failed for provider: {provider}")


async def analyze_market(analyst_input: AnalystInput) -> AnalystOutput:
    """
    Generate AI-powered market analysis using OpenAI.

    Args:
        analyst_input: AnalystInput object with composite cycle, turning points, and scanner results

    Returns:
        AnalystOutput with structured analysis

    Falls back to local analysis when no provider is configured or all providers fail.
    """
    context = analyst_input.data_context or {}
    if not context or not (
        context.get("score_components")
        or context.get("score_breakdown")
        or context.get("backtest_result")
        or context.get("backtest")
        or context.get("scenario")
    ):
        return local_analysis(analyst_input)

    prompt = format_analyst_prompt(analyst_input)
    errors = []

    for provider in provider_order(analyst_input.ai_provider_order):
        try:
            response_text = generate_with_provider(
                provider,
                prompt,
                analyst_input.ai_api_keys,
                analyst_input.ai_models,
                analyst_input.ai_base_urls,
            )
            if response_text.strip():
                return parse_generated_analysis(analyst_input.ticker, response_text)
        except (APIError, urllib.error.URLError, urllib.error.HTTPError, ValueError, Exception) as exc:
            errors.append(f"{provider}: {exc}")
            continue

    return local_analysis(analyst_input)


def test_provider_key(provider: str, api_key: str, model: Optional[str] = None, base_url: Optional[str] = None) -> None:
    normalized_provider = provider.strip().lower()

    if normalized_provider == "kie":
        response = urllib.request.urlopen(
            urllib.request.Request(
                "https://api.kie.ai/api/v1/chat/credit",
                headers={"Authorization": f"Bearer {api_key}"},
                method="GET",
            ),
            timeout=45,
        )
        body = json.loads(response.read().decode("utf-8"))
        if response.status != 200 or body.get("code") != 200:
            raise ValueError(body.get("msg") or "KIE_API_KEY tidak valid")
        return

    selected_model = model or get_provider_model(normalized_provider)
    prompt = "Jawab hanya dengan kata OK. Ini adalah tes koneksi API untuk AstroCycle."

    # For OpenAI Compatible providers, use custom base_url if provided
    if normalized_provider == "openai_compatible" or base_url:
        call_openai_compatible(
            api_key=api_key,
            model=selected_model or "gpt-3.5-turbo",
            prompt=prompt,
            base_url=base_url or "https://api.openai.com/v1",
        )
        return
    if normalized_provider == "openai":
        call_openai_compatible(api_key=api_key, model=selected_model, prompt=prompt)
        return
    if normalized_provider == "gemini":
        call_gemini(api_key=api_key, model=selected_model, prompt=prompt)
        return
    if normalized_provider in {"deepseek", "deepseek-ai"}:
        call_openai_compatible(
            api_key=api_key,
            model=selected_model,
            prompt=prompt,
            base_url="https://api.deepseek.com",
        )
        return
    if normalized_provider in {"xai", "grok"}:
        call_openai_compatible(
            api_key=api_key,
            model=selected_model,
            prompt=prompt,
            base_url="https://api.x.ai/v1",
        )
        return
    raise ValueError(f"Provider AI tidak dikenal: {provider}")


def parse_analysis_response(response_text: str) -> Dict[str, str]:
    """
    Parse AI response into structured sections.

    Args:
        response_text: Raw response from OpenAI

    Returns:
        Dictionary with parsed sections
    """
    sections = {
        "summary": "",
        "cycle_explanation": "",
        "turning_points_explanation": "",
        "scan_explanation": "",
        "outlook": "",
    }

    lines = response_text.split("\n")
    current_section = None
    current_text = []

    section_mapping = {
        "summary": "summary",
        "cycle": "cycle_explanation",
        "turning": "turning_points_explanation",
        "scanner": "scan_explanation",
        "outlook": "outlook",
    }

    for line in lines:
        line_lower = line.lower()

        # Check if this line starts a new section
        matched_section = None
        for keyword, section_key in section_mapping.items():
            if keyword in line_lower and ("**" in line or ":" in line):
                matched_section = section_key
                break

        if matched_section:
            # Save previous section
            if current_section and current_text:
                sections[current_section] = " ".join(current_text).strip()
            current_section = matched_section
            current_text = []
            # Extract content after ** or :
            content = line.split("**")[-1].split(":")[-1].strip()
            if content:
                current_text.append(content)
        elif current_section and line.strip():
            current_text.append(line.strip())

    # Save last section
    if current_section and current_text:
        sections[current_section] = " ".join(current_text).strip()

    return sections

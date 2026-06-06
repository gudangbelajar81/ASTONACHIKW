import json
import urllib.error
import urllib.request
from typing import Dict, Any, List, Optional
from openai import OpenAI, APIError
from backend.app.core.config import settings

AI_SYSTEM_MESSAGE = (
    "Anda adalah analis pasar ahli untuk trader ritel di Asia. "
    "Selalu jawab dalam Bahasa Indonesia yang jelas, ringkas, dan dapat ditindaklanjuti."
)


class AnalystInput:
    def __init__(
        self,
        ticker: str,
        composite_cycle_data: List[Dict[str, Any]],
        turning_points: List[Dict[str, Any]],
        scanner_results: Optional[List[Dict[str, Any]]] = None,
    ):
        self.ticker = ticker
        self.composite_cycle_data = composite_cycle_data
        self.turning_points = turning_points
        self.scanner_results = scanner_results or []


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

    prompt = f"""Anda adalah analis pasar ahli yang berfokus pada analisis siklus astrologi.

Analisis data pasar berikut dan berikan penjelasan yang mudah dipahami dalam Bahasa Indonesia:

MARKET TICKER: {analyst_input.ticker}

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
5. **Market Outlook** (2-3 kalimat): Berikan pandangan ke depan berdasarkan semua sinyal

Wajib jawab dalam Bahasa Indonesia.
Tetap spesifik tentang tanggal, nama siklus (misalnya "Venus-Jupiter"), dan potensi pergerakan harga.
Gunakan bahasa yang mudah dipahami trader ritel berpengalaman."""

    return prompt


def split_keys(raw_keys: str) -> list[str]:
    return [key.strip() for key in raw_keys.split(",") if key.strip()]


def provider_order() -> list[str]:
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
        temperature=0.7,
        max_tokens=1500,
    )
    return message.choices[0].message.content or ""


def call_gemini(*, api_key: str, model: str, prompt: str) -> str:
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "systemInstruction": {"parts": [{"text": AI_SYSTEM_MESSAGE}]},
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1500},
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


def local_analysis(analyst_input: AnalystInput) -> AnalystOutput:
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


def generate_with_provider(provider: str, prompt: str) -> str:
    errors = []
    if provider == "openai":
        for key in split_keys(settings.OPENAI_API_KEY):
            try:
                return call_openai_compatible(api_key=key, model=settings.OPENAI_MODEL, prompt=prompt)
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError("; ".join(errors) or "OPENAI_API_KEY kosong")
    if provider == "gemini":
        for key in split_keys(settings.GEMINI_API_KEY):
            try:
                return call_gemini(api_key=key, model=settings.GEMINI_MODEL, prompt=prompt)
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError("; ".join(errors) or "GEMINI_API_KEY kosong")
    if provider in {"deepseek", "deepseek-ai"}:
        for key in split_keys(settings.DEEPSEEK_API_KEY):
            try:
                return call_openai_compatible(
                    api_key=key,
                    model=settings.DEEPSEEK_MODEL,
                    prompt=prompt,
                    base_url="https://api.deepseek.com",
                )
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError("; ".join(errors) or "DEEPSEEK_API_KEY kosong")
    if provider in {"xai", "grok"}:
        for key in split_keys(settings.XAI_API_KEY):
            try:
                return call_openai_compatible(
                    api_key=key,
                    model=settings.XAI_MODEL,
                    prompt=prompt,
                    base_url="https://api.x.ai/v1",
                )
            except Exception as exc:
                errors.append(str(exc))
        raise ValueError("; ".join(errors) or "XAI_API_KEY kosong")
    raise ValueError(f"Provider AI tidak dikenal: {provider}")


async def analyze_market(analyst_input: AnalystInput) -> AnalystOutput:
    """
    Generate AI-powered market analysis using OpenAI.

    Args:
        analyst_input: AnalystInput object with composite cycle, turning points, and scanner results

    Returns:
        AnalystOutput with structured analysis

    Falls back to local analysis when no provider is configured or all providers fail.
    """
    prompt = format_analyst_prompt(analyst_input)
    errors = []

    for provider in provider_order():
        try:
            response_text = generate_with_provider(provider, prompt)
            if response_text.strip():
                return parse_generated_analysis(analyst_input.ticker, response_text)
        except (APIError, urllib.error.URLError, urllib.error.HTTPError, ValueError, Exception) as exc:
            errors.append(f"{provider}: {exc}")
            continue

    return local_analysis(analyst_input)


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

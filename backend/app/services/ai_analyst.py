from typing import Dict, Any, List, Optional
from datetime import date
from openai import OpenAI, APIError
from backend.app.core.config import settings


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


async def analyze_market(analyst_input: AnalystInput) -> AnalystOutput:
    """
    Generate AI-powered market analysis using OpenAI.

    Args:
        analyst_input: AnalystInput object with composite cycle, turning points, and scanner results

    Returns:
        AnalystOutput with structured analysis

    Raises:
        ValueError: If OpenAI API key is missing or API call fails
    """
    if not settings.OPENAI_API_KEY:
        raise ValueError("OpenAI API key not configured. Set OPENAI_API_KEY in .env")

    try:
        client = OpenAI(api_key=settings.OPENAI_API_KEY)
        prompt = format_analyst_prompt(analyst_input)

        message = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Anda adalah analis pasar ahli untuk trader ritel di Asia. Selalu jawab dalam Bahasa Indonesia yang jelas, ringkas, dan dapat ditindaklanjuti.",
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=1500,
        )

        response_text = message.choices[0].message.content

        # Parse response sections
        sections = parse_analysis_response(response_text)

        return AnalystOutput(
            ticker=analyst_input.ticker,
            summary=sections.get("summary", ""),
            cycle_explanation=sections.get("cycle_explanation", ""),
            turning_points_explanation=sections.get("turning_points_explanation", ""),
            scan_explanation=sections.get("scan_explanation", ""),
            outlook=sections.get("outlook", ""),
        )

    except APIError as e:
        raise ValueError(f"OpenAI API error: {str(e)}")
    except Exception as e:
        raise ValueError(f"Error generating analysis: {str(e)}")


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

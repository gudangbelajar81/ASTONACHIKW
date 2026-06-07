from datetime import date, datetime
from typing import Any


def normalize_symbol(symbol: str) -> str:
    return symbol.strip().upper()


def infer_market(symbol: str) -> str:
    return "IDX" if normalize_symbol(symbol).endswith(".JK") else "US"


def parse_date(value: Any) -> str:
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, (int, float)):
        return datetime.utcfromtimestamp(value).date().isoformat()
    if isinstance(value, str) and value.strip():
        text = value.strip()
        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00")).date().isoformat()
        except ValueError:
            return text[:10]
    return date.today().isoformat()


def number_value(value: Any, fallback: float = 0.0) -> float:
    if isinstance(value, bool):
        return fallback
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        cleaned = value.replace(",", "").replace("%", "").replace("x", "").strip()
        try:
            return float(cleaned)
        except ValueError:
            return fallback
    return fallback


def integer_value(value: Any, fallback: int = 0) -> int:
    return int(round(number_value(value, float(fallback))))


def list_value(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [item.strip() for item in value.split(",") if item.strip()]
    return []


def pick(payload: dict[str, Any], keys: list[str], fallback: Any = None) -> Any:
    for key in keys:
        if key in payload and payload[key] not in (None, ""):
            return payload[key]
    return fallback


def unwrap_payload(payload: Any) -> Any:
    candidate = payload
    if isinstance(payload, dict):
        for key in ("data", "result", "payload", "output", "bandarmology", "analysis"):
            value = payload.get(key)
            if value:
                candidate = value
                break
    return candidate


def normalize_ohlcv_record(payload: dict[str, Any], symbol: str, source: str = "unknown") -> dict[str, Any]:
    normalized_symbol = normalize_symbol(str(pick(payload, ["symbol", "ticker", "code"], symbol)))
    close = number_value(pick(payload, ["close", "c", "last", "price"]))
    open_ = number_value(pick(payload, ["open", "o"], close), close)
    high = number_value(pick(payload, ["high", "h"], close), close)
    low = number_value(pick(payload, ["low", "l"], close), close)
    return {
        "symbol": normalized_symbol,
        "market": str(pick(payload, ["market", "exchange"], infer_market(normalized_symbol))).upper(),
        "date": parse_date(pick(payload, ["date", "time", "timestamp", "datetime"], date.today())),
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": integer_value(pick(payload, ["volume", "v"], 0)),
        "source": str(pick(payload, ["source", "provider"], source)),
    }


def normalize_bandarmology_record(payload: Any, symbol: str, source: str = "unknown") -> dict[str, Any]:
    candidate = unwrap_payload(payload)
    if isinstance(candidate, list):
        candidate = candidate[0] if candidate else {}
    if not isinstance(candidate, dict):
        candidate = {}

    normalized_symbol = normalize_symbol(str(pick(candidate, ["symbol", "ticker", "code"], symbol)))
    broker_score = number_value(
        pick(
            candidate,
            [
                "broker_accumulation_score",
                "accumulation_score",
                "accumulationScore",
                "smart_money_score",
                "smartMoneyScore",
                "score",
            ],
            0,
        )
    )
    if -1 <= broker_score <= 1:
        broker_score = round((broker_score + 1) * 50, 2)

    return {
        "symbol": normalized_symbol,
        "date": parse_date(pick(candidate, ["date", "as_of_date", "time", "timestamp"], date.today())),
        "broker_accumulation_score": broker_score,
        "net_buy_value": number_value(
            pick(candidate, ["net_buy_value", "netBuyValue", "foreign_net_buy", "foreignNetBuy", "net_buy"], 0)
        ),
        "net_buy_volume": integer_value(
            pick(candidate, ["net_buy_volume", "netBuyVolume", "foreign_net_buy_volume", "volume"], 0)
        ),
        "top_buyer_brokers": list_value(
            pick(candidate, ["top_buyer_brokers", "topBuyerBrokers", "buyers", "top_buyers"], [])
        ),
        "top_seller_brokers": list_value(
            pick(candidate, ["top_seller_brokers", "topSellerBrokers", "sellers", "top_sellers"], [])
        ),
        "source": str(pick(candidate, ["source", "provider"], source)),
        "raw": candidate,
    }

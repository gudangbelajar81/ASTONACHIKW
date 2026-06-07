import json
import urllib.error
import urllib.request
from typing import Any

from fastapi import APIRouter, HTTPException

from backend.app.schemas.media import (
    KieImageGenerateRequest,
    KieImageStatusRequest,
    KieMediaKeyTestRequest,
    KieMediaKeyTestResponse,
    KieVideoGenerateRequest,
    KieVideoStatusRequest,
)

router = APIRouter()


def _request_json(method: str, url: str, api_key: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    headers = {"Authorization": f"Bearer {api_key}"}
    data = None
    if payload is not None:
        headers["Content-Type"] = "application/json"
        data = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(url, data=data, headers=headers, method=method)

    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        try:
            payload = json.loads(body)
            detail = payload.get("msg") or payload.get("message") or body
        except json.JSONDecodeError:
            detail = body or str(exc)
        raise HTTPException(status_code=exc.code, detail=detail) from exc
    except urllib.error.URLError as exc:
        raise HTTPException(status_code=502, detail=f"Gagal menghubungi Kie.ai: {exc.reason}") from exc


def _media_model_family(model: str) -> str:
    normalized = (model or "").strip().lower()
    if "flux" in normalized:
        return "flux"
    return "gpt4o"


@router.post("/kie/media/test-key", response_model=KieMediaKeyTestResponse)
async def test_media_key(request: KieMediaKeyTestRequest) -> KieMediaKeyTestResponse:
    try:
        response = _request_json("GET", "https://api.kie.ai/api/v1/chat/credit", request.api_key)
        credit_value = response.get("data")
        detail = "Key aktif dan bisa dipakai."
        if credit_value is not None:
            detail = f"Key aktif. Credit tersisa: {credit_value}"
        return KieMediaKeyTestResponse(provider=request.provider, status="live", detail=detail)
    except HTTPException as exc:
        return KieMediaKeyTestResponse(provider=request.provider, status="dead", detail=str(exc.detail))
    except Exception as exc:
        return KieMediaKeyTestResponse(provider=request.provider, status="dead", detail=str(exc))


@router.post("/kie/media/image/generate")
async def generate_image(request: KieImageGenerateRequest) -> dict[str, Any]:
    family = _media_model_family(request.model)
    if family == "flux":
        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "model": request.model,
            "enableTranslation": True,
            "aspectRatio": request.aspect_ratio or "16:9",
            "outputFormat": request.output_format or "jpeg",
            "promptUpsampling": request.prompt_upsampling,
        }
        if request.input_image_url:
            payload["inputImage"] = request.input_image_url
        response = _request_json(
            "POST",
            "https://api.kie.ai/api/v1/flux/kontext/generate",
            request.api_key,
            payload,
        )
        return {"engine": "flux", "provider": "kie_image", **response}

    payload = {
        "prompt": request.prompt,
        "size": request.size or "1:1",
        "isEnhance": request.enhance,
        "uploadCn": False,
        "enableFallback": False,
    }
    if request.input_image_url:
        payload["filesUrl"] = [request.input_image_url]
    response = _request_json(
        "POST",
        "https://api.kie.ai/api/v1/gpt4o-image/generate",
        request.api_key,
        payload,
    )
    return {"engine": "gpt4o", "provider": "kie_image", **response}


@router.post("/kie/media/image/record-info")
async def get_image_details(request: KieImageStatusRequest) -> dict[str, Any]:
    task_id = request.task_id
    api_key = request.api_key
    model = request.model
    family = _media_model_family(model)
    if family == "flux":
        response = _request_json(
            "GET",
            f"https://api.kie.ai/api/v1/flux/kontext/record-info?taskId={task_id}",
            api_key,
        )
        return {"engine": "flux", **response}

    response = _request_json(
        "GET",
        f"https://api.kie.ai/api/v1/gpt4o-image/record-info?taskId={task_id}",
        api_key,
    )
    return {"engine": "gpt4o", **response}


@router.post("/kie/media/video/generate")
async def generate_video(request: KieVideoGenerateRequest) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "prompt": request.prompt,
        "model": request.model,
        "waterMark": request.water_mark or "",
    }
    if request.image_url:
        payload["imageUrl"] = request.image_url
    if request.aspect_ratio:
        payload["aspectRatio"] = request.aspect_ratio
    if request.duration is not None:
        payload["duration"] = request.duration
    if request.quality:
        payload["quality"] = request.quality
    response = _request_json(
        "POST",
        "https://api.kie.ai/api/v1/runway/generate",
        request.api_key,
        payload,
    )
    return {"provider": "kie_video", **response}


@router.post("/kie/media/video/record-detail")
async def get_video_details(request: KieVideoStatusRequest) -> dict[str, Any]:
    response = _request_json(
        "GET",
        f"https://api.kie.ai/api/v1/runway/record-detail?taskId={request.task_id}",
        request.api_key,
    )
    return response

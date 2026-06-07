from pydantic import BaseModel, Field
from typing import Optional


class KieMediaKeyTestRequest(BaseModel):
    provider: str = Field(..., description="Provider identifier")
    api_key: str = Field(..., description="Kie.ai API key")


class KieMediaKeyTestResponse(BaseModel):
    provider: str
    status: str
    detail: str


class KieImageGenerateRequest(BaseModel):
    api_key: str = Field(..., description="Kie.ai API key")
    model: str = Field(..., description="Image model identifier")
    prompt: str = Field(..., description="Image prompt")
    aspect_ratio: Optional[str] = Field(default=None, description="Aspect ratio such as 1:1 or 16:9")
    input_image_url: Optional[str] = Field(default=None, description="Optional source image for editing")
    output_format: Optional[str] = Field(default="jpeg", description="Output image format")
    prompt_upsampling: Optional[bool] = Field(default=False, description="Whether to upsample the prompt")
    enhance: Optional[bool] = Field(default=False, description="Whether to enable enhancement")
    size: Optional[str] = Field(default="1:1", description="GPT 4o image size")


class KieImageStatusRequest(BaseModel):
    api_key: str = Field(..., description="Kie.ai API key")
    task_id: str = Field(..., description="Image generation task id")
    model: str = Field(default="gpt4o-image", description="Image model identifier")


class KieVideoGenerateRequest(BaseModel):
    api_key: str = Field(..., description="Kie.ai API key")
    model: str = Field(..., description="Video model identifier")
    prompt: str = Field(..., description="Video prompt")
    image_url: Optional[str] = Field(default=None, description="Optional reference image URL")
    aspect_ratio: Optional[str] = Field(default="16:9", description="Aspect ratio for the video")
    duration: Optional[int] = Field(default=5, description="Duration in seconds")
    quality: Optional[str] = Field(default="720p", description="Video quality")
    water_mark: Optional[str] = Field(default="kie.ai", description="Video watermark text")


class KieVideoStatusRequest(BaseModel):
    api_key: str = Field(..., description="Kie.ai API key")
    task_id: str = Field(..., description="Video generation task id")

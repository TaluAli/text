from typing import List, Optional
from pydantic import BaseModel, Field


class TokenRequest(BaseModel):
    token: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    ok: bool


class GenerateRequest(BaseModel):
    model_name: Optional[str]
    base_prompt: Optional[str] = ""
    char1: Optional[str] = ""
    char2: Optional[str] = ""
    negative_prompt: Optional[str] = ""
    guidance: float = 4.0
    rescale: float = 0.3
    width: int = 832
    height: int = 1216
    seed: int = 1234567890
    project: str = "default"


class ImageMeta(BaseModel):
    id: str
    project: str
    created_at: float
    seed: int
    model_name: str
    base_prompt: str
    char1: str
    char2: str
    negative_prompt: str
    guidance: float
    rescale: float
    width: int
    height: int
    image_url: str
    thumb_url: str


class ArchiveItem(BaseModel):
    id: str
    thumb_url: str
    image_url: str
    created_at: float
    seed: int
    prompts: str
    project: str
    filename: str
    relpath: str


class ArchiveResponse(BaseModel):
    items: List[ArchiveItem]
    page: int
    page_size: int
    total: int


class ProjectSummary(BaseModel):
    name: str
    count: int


class ProjectsResponse(BaseModel):
    projects: List[ProjectSummary]


class GenerateResponse(BaseModel):
    id: str
    image_url: str
    meta: ImageMeta

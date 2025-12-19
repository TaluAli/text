from typing import List, Optional, Literal
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
    seed_base: Optional[int] = None
    seed_used: Optional[int] = None


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


class SweepRange(BaseModel):
    start: float
    end: float
    step: float


class GenerateSweepRequest(BaseModel):
    model_name: Optional[str]
    base_prompt: Optional[str] = ""
    char1: Optional[str] = ""
    char2: Optional[str] = ""
    negative_prompt: Optional[str] = ""
    guidance: SweepRange
    rescale: SweepRange
    width: int = 832
    height: int = 1216
    seed: int = 1234567890
    project: str = "default"
    seed_mode: Literal["fixed", "increment", "random"] = "fixed"


class GenerateSweepResponse(BaseModel):
    job_id: str
    total: int


class JobStatus(BaseModel):
    status: str
    done: int
    total: int
    current_g: Optional[float] = None
    current_r: Optional[float] = None
    current_filename: Optional[str] = None
    error: Optional[str] = None
    current_seed: Optional[int] = None

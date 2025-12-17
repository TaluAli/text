from pathlib import Path
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.models import (
    ArchiveResponse,
    GenerateRequest,
    GenerateResponse,
    GenerateSweepRequest,
    GenerateSweepResponse,
    ImageMeta,
    JobStatus,
    ProjectsResponse,
    TokenRequest,
    TokenResponse,
)
from app.services import archive as archive_service
from app.services import jobs as job_service
from app.services.novelai import generate_image

app = FastAPI(title="NAI Studio Web")

origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory token storage (default). Not logged or exposed.
_TOKEN: Optional[str] = None


@app.post("/api/token", response_model=TokenResponse)
def set_token(req: TokenRequest):
    global _TOKEN
    _TOKEN = req.token.strip()
    return TokenResponse(ok=True)


def _require_token() -> str:
    if not _TOKEN:
        raise HTTPException(status_code=401, detail="Token not set")
    return _TOKEN


@app.post("/api/generate", response_model=GenerateResponse)
def generate(req: GenerateRequest, token: str = Depends(_require_token)):
    img = generate_image(
        token=token,
        model_name=req.model_name,
        base_prompt=req.base_prompt or "",
        char1=req.char1 or "",
        char2=req.char2 or "",
        negative_prompt=req.negative_prompt or "",
        guidance=req.guidance,
        rescale=req.rescale,
        width=req.width,
        height=req.height,
        seed=req.seed,
    )

    if img is None:
        raise HTTPException(status_code=502, detail="Generation failed")

    payload_meta = {
        "model": req.model_name,
        "input": req.base_prompt or "",
        "char1": req.char1 or "",
        "char2": req.char2 or "",
        "negative_prompt": req.negative_prompt or "",
        "guidance": req.guidance,
        "rescale": req.rescale,
        "width": req.width,
        "height": req.height,
    }

    meta: ImageMeta = archive_service.save_image_and_meta(
        image=img,
        project=req.project,
        seed=req.seed,
        payload=payload_meta,
    )

    return GenerateResponse(
        id=meta.id,
        image_url=meta.image_url,
        meta=meta,
    )


@app.post("/api/generate_sweep", response_model=GenerateSweepResponse)
def generate_sweep(req: GenerateSweepRequest, token: str = Depends(_require_token)):
    try:
        job = job_service.create_sweep_job(req, token)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return GenerateSweepResponse(job_id=job.id, total=job.total)


@app.get("/api/jobs/{job_id}", response_model=JobStatus)
def job_status(job_id: str):
    status = job_service.get_job(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.post("/api/jobs/{job_id}/cancel", response_model=JobStatus)
def cancel_job(job_id: str):
    status = job_service.cancel_job(job_id)
    if not status:
        raise HTTPException(status_code=404, detail="Job not found")
    return status


@app.get("/api/archives", response_model=ArchiveResponse)
def archives(
    project: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(30, ge=1, le=200),
    q: Optional[str] = Query(None),
):
    items, total = archive_service.list_archives(project, page, page_size, q)
    return ArchiveResponse(items=items, page=page, page_size=page_size, total=total)


@app.get("/api/projects", response_model=ProjectsResponse)
def projects():
    projects = archive_service.list_projects()
    return ProjectsResponse(projects=projects)


@app.get("/api/images/{image_id}")
def get_image(image_id: str):
    path = archive_service.get_image_path(image_id)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/api/thumbs/{image_id}")
def get_thumb(image_id: str):
    thumb = archive_service.generate_thumb(image_id)
    if thumb:
        return FileResponse(thumb)
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/raw/{image_id}")
def get_raw_image(image_id: str):
    path = archive_service.get_image_path(image_id)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/api/raw_path/{relpath:path}")
def get_raw_image_by_path(relpath: str):
    path = archive_service.get_path_from_relpath(relpath)
    if not path:
        raise HTTPException(status_code=404, detail="Image not found")
    return FileResponse(path)


@app.get("/api/thumb/{image_id}")
def get_thumb_single(image_id: str):
    thumb = archive_service.generate_thumb(image_id)
    if thumb:
        return FileResponse(thumb)
    raise HTTPException(status_code=404, detail="Thumbnail not found")


@app.get("/api/thumb_path/{relpath:path}")
def get_thumb_by_path(relpath: str):
    thumb = archive_service.generate_thumb_for_relpath(relpath)
    if thumb:
        return FileResponse(thumb)
    raise HTTPException(status_code=404, detail="Thumbnail not found")


static_root = (Path(__file__).resolve().parent / "static").resolve()
static_root.mkdir(parents=True, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_root), name="static")

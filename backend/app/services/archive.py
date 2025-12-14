import json
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from app.models import ArchiveItem, ImageMeta

BASE_DIR = Path(__file__).resolve().parent.parent
ARCHIVE_ROOT = BASE_DIR / "data" / "archives"
THUMB_ROOT = BASE_DIR / "data" / "thumbs"


def sanitize_project(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name or "")
    return cleaned or "default"


def ensure_dirs(project: str):
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    THUMB_ROOT.mkdir(parents=True, exist_ok=True)
    project_dir = ARCHIVE_ROOT / project
    thumb_dir = THUMB_ROOT / project
    project_dir.mkdir(parents=True, exist_ok=True)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    return project_dir, thumb_dir


def build_ids(project: str, seed: int) -> Tuple[str, str]:
    ts = int(time.time() * 1000)
    file_name = f"{ts}_{seed}.png"
    image_id = f"{project}--{file_name}"
    return image_id, file_name


def save_image_and_meta(image: Image.Image, project: str, seed: int, payload: Dict) -> ImageMeta:
    project = sanitize_project(project)
    project_dir, thumb_dir = ensure_dirs(project)

    image_id, file_name = build_ids(project, seed)
    img_path = project_dir / file_name
    meta_path = project_dir / f"{file_name}.json"

    image.save(img_path)

    created_at = time.time()
    meta = ImageMeta(
        id=image_id,
        project=project,
        created_at=created_at,
        seed=seed,
        model_name=str(payload.get("model")),
        base_prompt=str(payload.get("input", "")),
        char1=str(payload.get("char1", "")),
        char2=str(payload.get("char2", "")),
        negative_prompt=str(payload.get("negative_prompt", "")),
        guidance=float(payload.get("guidance", 0)),
        rescale=float(payload.get("rescale", 0)),
        width=int(payload.get("width", 0)),
        height=int(payload.get("height", 0)),
        image_url=f"/api/images/{image_id}",
        thumb_url=f"/api/thumbs/{image_id}",
    )

    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta.dict(), f, ensure_ascii=False, indent=2)

    return meta


def _load_meta_from_file(meta_path: Path) -> Optional[Dict]:
    try:
        with open(meta_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _image_id_from_path(project: str, file_name: str) -> str:
    return f"{project}--{file_name}"


def list_archives(project: Optional[str], page: int, page_size: int) -> Tuple[List[ArchiveItem], int]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    projects = [sanitize_project(project)] if project else [p.name for p in ARCHIVE_ROOT.iterdir() if p.is_dir()]

    entries: List[ArchiveItem] = []
    for proj in projects:
        proj_dir = ARCHIVE_ROOT / proj
        if not proj_dir.exists():
            continue
        for file in proj_dir.glob("*.png"):
            meta_path = proj_dir / f"{file.name}.json"
            meta_json = _load_meta_from_file(meta_path)
            created = file.stat().st_mtime
            seed_val = None
            base_prompt = ""
            neg_prompt = ""
            if meta_json:
                created = meta_json.get("created_at", created)
                seed_val = meta_json.get("seed")
                base_prompt = meta_json.get("base_prompt", "")
                neg_prompt = meta_json.get("negative_prompt", "")
            image_id = _image_id_from_path(proj, file.name)
            prompts = base_prompt
            if neg_prompt:
                prompts = f"{prompts} | NEG: {neg_prompt}" if prompts else f"NEG: {neg_prompt}"
            entries.append(
                ArchiveItem(
                    id=image_id,
                    thumb_url=f"/api/thumbs/{image_id}",
                    image_url=f"/api/images/{image_id}",
                    created_at=created,
                    seed=int(seed_val) if seed_val is not None else 0,
                    prompts=prompts,
                    project=proj,
                )
            )

    entries.sort(key=lambda x: x.created_at, reverse=True)
    total = len(entries)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    return entries[start:end], total


def parse_image_id(image_id: str) -> Optional[Path]:
    if "--" not in image_id:
        return None
    project, file_name = image_id.split("--", 1)
    project = sanitize_project(project)
    path = ARCHIVE_ROOT / project / file_name
    if path.suffix.lower() != ".png":
        path = path.with_suffix(".png")
    if path.exists():
        return path
    return None


def get_image_path(image_id: str) -> Optional[Path]:
    return parse_image_id(image_id)


def get_thumb_path(image_id: str) -> Optional[Path]:
    img_path = parse_image_id(image_id)
    if not img_path:
        return None
    project, file_name = image_id.split("--", 1)
    thumb_dir = THUMB_ROOT / sanitize_project(project)
    thumb_dir.mkdir(parents=True, exist_ok=True)
    thumb_path = thumb_dir / file_name
    if thumb_path.suffix.lower() != ".png":
        thumb_path = thumb_path.with_suffix(".png")
    return thumb_path


def generate_thumb(image_id: str) -> Optional[Path]:
    img_path = get_image_path(image_id)
    if not img_path:
        return None
    thumb_path = get_thumb_path(image_id)
    if not thumb_path:
        return None
    if thumb_path.exists():
        return thumb_path
    try:
        with Image.open(img_path) as img:
            img.thumbnail((512, 512))
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb_path)
        return thumb_path
    except Exception as e:
        print(f"[Archive] failed to build thumbnail: {e}")
        return None

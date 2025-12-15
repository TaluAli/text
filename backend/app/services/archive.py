import hashlib
import json
import os
import re
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PIL import Image

from app.models import ArchiveItem, ImageMeta, ProjectSummary

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_ARCHIVE_ROOT = os.getenv("NAI_ARCHIVE_ROOT")
ARCHIVE_ROOT = Path(ENV_ARCHIVE_ROOT).expanduser() if ENV_ARCHIVE_ROOT else BASE_DIR / "data" / "archives"
ARCHIVE_ROOT = ARCHIVE_ROOT.resolve()
THUMB_CACHE = BASE_DIR / "data" / "thumb_cache"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_RAW_INDEX: Dict[str, Path] = {}


def sanitize_project(name: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_-]+", "_", name or "")
    return cleaned or "default"


def _normalize_path_str(path: Path) -> str:
    return str(path.resolve()).replace("\\", "/")


def _is_under_archive(path: Path) -> bool:
    try:
        path.resolve().relative_to(ARCHIVE_ROOT)
        return True
    except ValueError:
        return False


def _safe_relpath(relpath: str) -> Optional[Path]:
    candidate = (ARCHIVE_ROOT / relpath).resolve()
    if not candidate.exists() or not candidate.is_file():
        return None
    if not _is_under_archive(candidate):
        return None
    if candidate.suffix.lower() not in IMAGE_EXTS:
        return None
    return candidate


def _path_thumb_url(relpath: str) -> str:
    return f"/api/thumb_path/{relpath}"


def _path_image_url(relpath: str) -> str:
    return f"/api/raw_path/{relpath}"


def _build_raw_id(path: Path) -> str:
    norm = _normalize_path_str(path).lower()
    return hashlib.sha1(norm.encode("utf-8")).hexdigest()


def ensure_dirs(project: str):
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    project_dir = ARCHIVE_ROOT / project
    project_dir.mkdir(parents=True, exist_ok=True)
    THUMB_CACHE.mkdir(parents=True, exist_ok=True)
    return project_dir


def build_ids(project: str, seed: int) -> Tuple[str, str]:
    ts = int(time.time() * 1000)
    file_name = f"{ts}_{seed}.png"
    image_id = f"{project}--{file_name}"
    return image_id, file_name


def save_image_and_meta(image: Image.Image, project: str, seed: int, payload: Dict) -> ImageMeta:
    project = sanitize_project(project)
    project_dir = ensure_dirs(project)

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
        thumb_url=f"/api/thumb/{image_id}",
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


def _meta_entry(project: str, file: Path, relpath: str, meta_json: Optional[Dict]) -> ArchiveItem:
    created = file.stat().st_mtime
    seed_val = None
    base_prompt = ""
    neg_prompt = ""
    if meta_json:
        created = meta_json.get("created_at", created)
        seed_val = meta_json.get("seed")
        base_prompt = meta_json.get("base_prompt", "")
        neg_prompt = meta_json.get("negative_prompt", "")
    image_id = _image_id_from_path(project, file.name)
    prompts = base_prompt
    if neg_prompt:
        prompts = f"{prompts} | NEG: {neg_prompt}" if prompts else f"NEG: {neg_prompt}"
    return ArchiveItem(
        id=image_id,
        thumb_url=_path_thumb_url(relpath),
        image_url=_path_image_url(relpath),
        created_at=created,
        seed=int(seed_val) if seed_val is not None else 0,
        prompts=prompts,
        project=project,
        filename=file.name,
        relpath=relpath,
    )


def _raw_entry(path: Path, relpath: str, project: str) -> ArchiveItem:
    raw_id = _build_raw_id(path)
    _RAW_INDEX[raw_id] = path
    created = path.stat().st_mtime
    return ArchiveItem(
        id=raw_id,
        thumb_url=_path_thumb_url(relpath),
        image_url=_path_image_url(relpath),
        created_at=created,
        seed=0,
        prompts="",
        project=project,
        filename=path.name,
        relpath=relpath,
    )


def _matches_query(relpath: str, filename: str, query: Optional[str]) -> bool:
    if not query:
        return True
    q = query.lower()
    return q in relpath.lower() or q in filename.lower()


def list_archives(project: Optional[str], page: int, page_size: int, query: Optional[str]) -> Tuple[List[ArchiveItem], int]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    if project:
        projects = [project]
    else:
        projects = [p.name for p in ARCHIVE_ROOT.iterdir() if p.is_dir()]
        if ARCHIVE_ROOT.exists() and not projects:
            projects = ["default"] if any(ARCHIVE_ROOT.glob("*")) else []

    entries: List[ArchiveItem] = []
    seen_paths = set()

    for proj in projects:
        proj_dir = ARCHIVE_ROOT / proj
        if proj_dir.exists():
            for file in proj_dir.glob("*.png"):
                relpath = str(file.relative_to(ARCHIVE_ROOT).as_posix())
                if not _matches_query(relpath, file.name, query):
                    continue
                meta_path = proj_dir / f"{file.name}.json"
                meta_json = _load_meta_from_file(meta_path)
                entry = _meta_entry(proj, file, relpath, meta_json)
                entries.append(entry)
                seen_paths.add(_normalize_path_str(file))

    for path in ARCHIVE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        if not _is_under_archive(path):
            continue
        normalized = _normalize_path_str(path)
        if normalized in seen_paths:
            continue
        rel = path.relative_to(ARCHIVE_ROOT)
        relpath = str(rel.as_posix())
        top_level = rel.parts[0] if len(rel.parts) > 1 else "default"
        if project and top_level != project:
            continue
        if not _matches_query(relpath, path.name, query):
            continue
        entries.append(_raw_entry(path, relpath, top_level))

    entries.sort(key=lambda x: x.created_at, reverse=True)
    total = len(entries)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    return entries[start:end], total


def list_projects() -> List[ProjectSummary]:
    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
    counts: Dict[str, int] = {}

    for path in ARCHIVE_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in IMAGE_EXTS:
            continue
        if not _is_under_archive(path):
            continue
        rel = path.relative_to(ARCHIVE_ROOT)
        top_level = rel.parts[0] if len(rel.parts) > 1 else "default"
        counts[top_level] = counts.get(top_level, 0) + 1

    return [ProjectSummary(name=k, count=v) for k, v in sorted(counts.items())]


def parse_image_id(image_id: str) -> Optional[Path]:
    if "--" not in image_id:
        return None
    project, file_name = image_id.split("--", 1)
    project = sanitize_project(project)
    path = ARCHIVE_ROOT / project / file_name
    if path.suffix.lower() != ".png":
        path = path.with_suffix(".png")
    if path.exists() and _is_under_archive(path):
        return path
    return None


def _legacy_thumb_path(image_id: str) -> Optional[Path]:
    if "--" not in image_id:
        return None
    project, file_name = image_id.split("--", 1)
    legacy_dir = BASE_DIR / "data" / "thumbs" / sanitize_project(project)
    legacy_path = legacy_dir / file_name
    if legacy_path.suffix.lower() != ".png":
        legacy_path = legacy_path.with_suffix(".png")
    if legacy_path.exists():
        return legacy_path
    return None


def _thumb_cache_path(image_id: str) -> Path:
    THUMB_CACHE.mkdir(parents=True, exist_ok=True)
    return THUMB_CACHE / f"{image_id}.jpg"


def _resolve_raw_path(image_id: str) -> Optional[Path]:
    if image_id in _RAW_INDEX:
        path = _RAW_INDEX[image_id]
        if path.exists() and _is_under_archive(path):
            return path
    for path in ARCHIVE_ROOT.rglob("*"):
        if path.is_file() and path.suffix.lower() in IMAGE_EXTS:
            candidate_id = _build_raw_id(path)
            _RAW_INDEX[candidate_id] = path
            if candidate_id == image_id and _is_under_archive(path):
                return path
    return None


def get_image_path(image_id: str) -> Optional[Path]:
    meta_path = parse_image_id(image_id)
    if meta_path:
        return meta_path
    return _resolve_raw_path(image_id)


def get_path_from_relpath(relpath: str) -> Optional[Path]:
    return _safe_relpath(relpath)


def generate_thumb(image_id: str) -> Optional[Path]:
    img_path = get_image_path(image_id)
    if not img_path:
        return None
    thumb_path = _thumb_cache_path(image_id)
    if thumb_path.exists():
        return thumb_path
    legacy = _legacy_thumb_path(image_id)
    if legacy and legacy.exists():
        return legacy
    try:
        with Image.open(img_path) as img:
            img.thumbnail((512, 512))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb_path, format="JPEG")
        return thumb_path
    except Exception:
        return None


def generate_thumb_for_relpath(relpath: str) -> Optional[Path]:
    img_path = _safe_relpath(relpath)
    if not img_path:
        return None
    thumb_id = _build_raw_id(img_path)
    thumb_path = _thumb_cache_path(thumb_id)
    if thumb_path.exists():
        return thumb_path
    try:
        with Image.open(img_path) as img:
            img.thumbnail((512, 512))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb_path, format="JPEG")
        return thumb_path
    except Exception:
        return None

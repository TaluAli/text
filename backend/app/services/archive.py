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
THUMB_CACHE = BASE_DIR / ".cache" / "thumbs"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
_RAW_INDEX: Dict[str, Path] = {}
_INDEX_CACHE = {
    "ts": 0.0,
    "sig": 0.0,
    "projects": {},
    "counts": {},
}
_INDEX_TTL_SECONDS = 180.0


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


def _format_param(value: float, digits: int = 1) -> str:
    try:
        return f"{float(value):.{digits}f}"
    except Exception:
        return "0.0"


def build_ids(project: str, seed: int, guidance: float, rescale: float) -> Tuple[str, str]:
    ts = int(time.time() * 1000)
    g_token = _format_param(guidance, 1)
    r_token = _format_param(rescale, 1)
    file_name = f"{ts}_{seed}_G{g_token}_R{r_token}.png"
    image_id = f"{project}--{file_name}"
    return image_id, file_name


def _latest_mtime(path: Path) -> float:
    try:
        return path.stat().st_mtime
    except FileNotFoundError:
        return 0.0


def save_image_and_meta(
    image: Image.Image,
    project: str,
    seed: int,
    payload: Dict,
    seed_base: Optional[int] = None,
    seed_used: Optional[int] = None,
) -> ImageMeta:
    project = sanitize_project(project)
    project_dir = ensure_dirs(project)

    effective_seed = seed_used if seed_used is not None else seed
    base_seed = seed_base if seed_base is not None else seed
    image_id, file_name = build_ids(
        project,
        effective_seed,
        float(payload.get("guidance", 0)),
        float(payload.get("rescale", 0)),
    )
    img_path = project_dir / file_name
    meta_path = project_dir / f"{file_name}.json"

    image.save(img_path)

    created_at = time.time()
    meta = ImageMeta(
        id=image_id,
        project=project,
        created_at=created_at,
        seed=effective_seed,
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
        seed_base=base_seed,
        seed_used=effective_seed,
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
        seed_val = meta_json.get("seed_used") if meta_json.get("seed_used") is not None else meta_json.get("seed")
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


def refresh_index(force: bool = False) -> Dict:
    global _INDEX_CACHE, _RAW_INDEX
    now = time.time()
    root_sig = _latest_mtime(ARCHIVE_ROOT)
    if (
        not force
        and _INDEX_CACHE.get("ts")
        and (now - _INDEX_CACHE["ts"] < _INDEX_TTL_SECONDS)
        and _INDEX_CACHE.get("sig") == root_sig
    ):
        return _INDEX_CACHE

    entries_by_project: Dict[str, List[ArchiveItem]] = {}
    counts: Dict[str, int] = {}
    _RAW_INDEX.clear()

    ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)

    for dirpath, _, filenames in os.walk(ARCHIVE_ROOT):
        for fname in filenames:
            suffix = Path(fname).suffix.lower()
            if suffix not in IMAGE_EXTS:
                continue
            path = Path(dirpath) / fname
            relpath = path.relative_to(ARCHIVE_ROOT).as_posix()
            project = relpath.split("/", 1)[0] if "/" in relpath else "default"
            meta_path = path.parent / f"{path.name}.json"
            meta_json = _load_meta_from_file(meta_path) if meta_path.exists() else None
            if meta_json:
                entry = _meta_entry(project, path, relpath, meta_json)
            else:
                entry = _raw_entry(path, relpath, project)
            entries_by_project.setdefault(project, []).append(entry)

    for proj, items in entries_by_project.items():
        items.sort(key=lambda x: x.created_at, reverse=True)
        counts[proj] = len(items)

    _INDEX_CACHE = {
        "ts": now,
        "sig": root_sig,
        "projects": entries_by_project,
        "counts": counts,
    }
    return _INDEX_CACHE


def _matches_query(relpath: str, filename: str, query: Optional[str]) -> bool:
    if not query:
        return True
    q = query.lower()
    return q in relpath.lower() or q in filename.lower()


def list_archives(project: Optional[str], page: int, page_size: int, query: Optional[str]) -> Tuple[List[ArchiveItem], int]:
    refresh_index()
    available_projects = _INDEX_CACHE.get("projects", {})
    selected = [project] if project else list(available_projects.keys())
    entries: List[ArchiveItem] = []

    for proj in selected:
        if proj in available_projects:
            entries.extend(available_projects[proj])

    if query:
        entries = [e for e in entries if _matches_query(e.relpath, e.filename, query)]

    entries.sort(key=lambda x: x.created_at, reverse=True)
    total = len(entries)
    start = max(0, (page - 1) * page_size)
    end = start + page_size
    return entries[start:end], total


def list_projects() -> List[ProjectSummary]:
    refresh_index()
    counts: Dict[str, int] = _INDEX_CACHE.get("counts", {})
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


def _thumb_cache_key(path: Path, relpath: str) -> str:
    mtime = int(_latest_mtime(path))
    payload = f"{relpath}|{mtime}"
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def _resolve_raw_path(image_id: str) -> Optional[Path]:
    refresh_index()
    if image_id in _RAW_INDEX:
        path = _RAW_INDEX[image_id]
        if path.exists() and _is_under_archive(path):
            return path
    return None


def get_image_path(image_id: str) -> Optional[Path]:
    refresh_index()
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
    rel = img_path.relative_to(ARCHIVE_ROOT)
    cache_key = _thumb_cache_key(img_path, str(rel.as_posix()))
    thumb_path = _thumb_cache_path(cache_key)
    if thumb_path.exists():
        return thumb_path
    legacy = _legacy_thumb_path(image_id)
    if legacy and legacy.exists():
        return legacy
    try:
        with Image.open(img_path) as img:
            img.thumbnail((384, 384))
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
    cache_key = _thumb_cache_key(img_path, relpath)
    thumb_path = _thumb_cache_path(cache_key)
    if thumb_path.exists():
        return thumb_path
    try:
        with Image.open(img_path) as img:
            img.thumbnail((384, 384))
            if img.mode not in ("RGB", "L"):
                img = img.convert("RGB")
            thumb_path.parent.mkdir(parents=True, exist_ok=True)
            img.save(thumb_path, format="JPEG")
        return thumb_path
    except Exception:
        return None

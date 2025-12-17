import threading
import time
import uuid
from dataclasses import dataclass, field
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict, List, Optional

from app.models import GenerateSweepRequest, JobStatus
from app.services import archive as archive_service
from app.services.novelai import generate_image

MAX_IMAGES = 500


def _float_range(start: float, end: float, step: float, digits: int = 1) -> List[float]:
    if step <= 0:
        return []
    vals: List[float] = []
    current = Decimal(str(start))
    end_d = Decimal(str(end))
    step_d = Decimal(str(step))
    quant = Decimal(f"0.{''.join(['0' for _ in range(digits - 1)])}1") if digits > 0 else Decimal("1")
    tolerance = step_d / Decimal("10")
    while current <= end_d + tolerance:
        vals.append(float(current.quantize(quant, rounding=ROUND_HALF_UP)))
        current += step_d
    return vals


@dataclass
class SweepJob:
    request: GenerateSweepRequest
    token: str
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    status: str = "queued"
    done: int = 0
    total: int = 0
    current_g: Optional[float] = None
    current_r: Optional[float] = None
    current_filename: Optional[str] = None
    error: Optional[str] = None
    cancel_event: threading.Event = field(default_factory=threading.Event)

    def to_status(self) -> JobStatus:
        return JobStatus(
            status=self.status,
            done=self.done,
            total=self.total,
            current_g=self.current_g,
            current_r=self.current_r,
            current_filename=self.current_filename,
            error=self.error,
        )


_JOBS: Dict[str, SweepJob] = {}


def _run_job(job: SweepJob):
    job.status = "running"
    req = job.request
    g_values = _float_range(req.guidance.start, req.guidance.end, req.guidance.step, digits=1)
    r_values = _float_range(req.rescale.start, req.rescale.end, req.rescale.step, digits=1)
    job.total = len(g_values) * len(r_values)
    if job.total == 0:
        job.status = "error"
        job.error = "No values to generate"
        return

    seq = 0
    for g in g_values:
        if job.cancel_event.is_set():
            job.status = "cancelled"
            return
        for r in r_values:
            if job.cancel_event.is_set():
                job.status = "cancelled"
                return
            job.current_g = g
            job.current_r = r
            seed_val = int(req.seed) + seq
            img = generate_image(
                token=job.token,
                model_name=req.model_name,
                base_prompt=req.base_prompt or "",
                char1=req.char1 or "",
                char2=req.char2 or "",
                negative_prompt=req.negative_prompt or "",
                guidance=float(g),
                rescale=float(r),
                width=req.width,
                height=req.height,
                seed=seed_val,
            )
            if img is None:
                job.status = "error"
                job.error = "Generation failed"
                return

            payload_meta = {
                "model": req.model_name,
                "input": req.base_prompt or "",
                "char1": req.char1 or "",
                "char2": req.char2 or "",
                "negative_prompt": req.negative_prompt or "",
                "guidance": float(g),
                "rescale": float(r),
                "width": req.width,
                "height": req.height,
            }

            meta = archive_service.save_image_and_meta(
                image=img,
                project=req.project,
                seed=seed_val,
                payload=payload_meta,
            )
            job.done += 1
            job.current_filename = meta.image_url
            seq += 1
    job.status = "done"


def create_sweep_job(req: GenerateSweepRequest, token: str) -> SweepJob:
    g_values = _float_range(req.guidance.start, req.guidance.end, req.guidance.step, digits=1)
    r_values = _float_range(req.rescale.start, req.rescale.end, req.rescale.step, digits=1)
    total = len(g_values) * len(r_values)
    if total == 0:
        raise ValueError("No values to generate")
    if total > MAX_IMAGES:
        raise ValueError(f"Requested {total} images exceeds cap of {MAX_IMAGES}")

    job = SweepJob(request=req, token=token, total=total)
    _JOBS[job.id] = job
    thread = threading.Thread(target=_run_job, args=(job,), daemon=True)
    thread.start()
    return job


def get_job(job_id: str) -> Optional[JobStatus]:
    job = _JOBS.get(job_id)
    return job.to_status() if job else None


def cancel_job(job_id: str) -> Optional[JobStatus]:
    job = _JOBS.get(job_id)
    if not job:
        return None
    job.cancel_event.set()
    return job.to_status()


__all__ = [
    "create_sweep_job",
    "get_job",
    "cancel_job",
    "MAX_IMAGES",
]

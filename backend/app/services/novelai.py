import io
import os
import time
import zipfile
from typing import List, Optional

import requests
from PIL import Image

DEFAULT_MODEL = "nai-diffusion-4-5-full"
IMG_W, IMG_H = 832, 1216
DEFAULT_SEED = 1234567890


def _prepare_prompts(base_prompt: str, char1: str, char2: str, negative_prompt: str):
    main_prompt = (base_prompt or "").strip()
    neg_prompt = (negative_prompt or "").strip()
    char_prompts: List[str] = []
    for cp in [char1, char2]:
        cp = (cp or "").strip()
        if cp:
            char_prompts.append(cp)
    return main_prompt, neg_prompt, char_prompts


def build_payload(model_name: Optional[str], base_prompt: str, char1: str, char2: str,
                  negative_prompt: str, guidance: float, rescale: float,
                  width: int, height: int, seed: int):
    if not model_name or not model_name.strip():
        model_name = DEFAULT_MODEL
    model_name = model_name.strip()

    main_prompt, neg_prompt, char_prompts = _prepare_prompts(base_prompt, char1, char2, negative_prompt)

    params = {
        "width": width,
        "height": height,
        "scale": float(guidance),
        "sampler": "k_euler_ancestral",
        "steps": 28,
        "n_samples": 1,
        "ucPreset": 0,
        "cfg_rescale": float(rescale),
        "dynamic_thresholding": False,
        "params_version": 3,
        "legacy": False,
        "legacy_uc": False,
        "legacy_v3_extend": False,
        "negative_prompt": neg_prompt,
        "noise_schedule": "karras",
        "qualityToggle": True,
        "seed": int(seed),
        "extra_noise_seed": int(seed),
        "skip_cfg_above_sigma": None,
        "sm": False,
        "sm_dyn": False,
        "add_original_image": True,
        "use_coords": False,
        "deliberate_euler_ancestral_bug": False,
        "prefer_brownian": True,
    }

    if model_name.startswith("nai-diffusion-4"):
        params["v4_prompt"] = {
            "caption": {
                "base_caption": main_prompt,
                "char_captions": []
            },
            "use_coords": False,
            "use_order": True
        }
        params["v4_negative_prompt"] = {
            "caption": {
                "base_caption": neg_prompt,
                "char_captions": []
            },
            "legacy_uc": False
        }
        for cp in char_prompts:
            char_v4_prompt = {
                "char_caption": cp,
                "centers": [{"x": 0.5, "y": 0.5}]
            }
            char_v4_uc = {
                "char_caption": "",
                "centers": [{"x": 0.5, "y": 0.5}]
            }
            params["v4_prompt"]["caption"]["char_captions"].append(char_v4_prompt)
            params["v4_negative_prompt"]["caption"]["char_captions"].append(char_v4_uc)

    payload = {
        "action": "generate",
        "input": main_prompt,
        "model": model_name,
        "parameters": params
    }
    return payload


def generate_image(token: str, model_name: Optional[str], base_prompt: str, char1: str, char2: str,
                   negative_prompt: str, guidance: float, rescale: float, width: int,
                   height: int, seed: int) -> Optional[Image.Image]:
    payload = build_payload(model_name, base_prompt, char1, char2, negative_prompt,
                            guidance, rescale, width, height, seed)

    url = "https://image.novelai.net/ai/generate-image"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://novelai.net",
        "Referer": "https://novelai.net/",
    }

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=180)
    except Exception as e:
        print(f"[NovelAI ERROR] request failed: {e}")
        return None

    if res.status_code != 200:
        try:
            print(f"[NovelAI ERROR] HTTP {res.status_code}: {res.text}")
        except Exception:
            print(f"[NovelAI ERROR] HTTP {res.status_code}")
        return None

    try:
        z = zipfile.ZipFile(io.BytesIO(res.content))
        name_list = z.namelist()
        if not name_list:
            return None
        img_bytes = z.read(name_list[0])
        return Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        print(f"[NovelAI ERROR] response parse failed: {e}")
        return None


__all__ = [
    "generate_image",
    "build_payload",
    "DEFAULT_MODEL",
    "IMG_W",
    "IMG_H",
    "DEFAULT_SEED",
]

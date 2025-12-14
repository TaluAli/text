#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import gradio as gr
import requests
import zipfile
import io
import os
import time
import re
from PIL import Image

# ==========================================
# [전역 설정]
# ==========================================
DEFAULT_MODEL = "nai-diffusion-4-5-full"
IMG_W, IMG_H = 832, 1216
DEFAULT_SEED = 1234567890
is_running = False

# ==========================================
# [UI STYLE PATCH - Dark Glassmorphism]
# ==========================================
UI_STYLE_PATCH = """
<style>
    #app_root {
        position: relative;
        min-height: 100vh;
        padding: 18px;
        background: radial-gradient(circle at 20% 20%, rgba(90,120,200,0.12), rgba(15,18,24,0.75) 34%, rgba(8,8,10,0.9) 76%),
                    radial-gradient(circle at 80% 10%, rgba(140,90,200,0.12), rgba(10,10,14,0.82) 32%, rgba(6,6,8,0.9) 72%),
                    linear-gradient(135deg, #0d0d11 0%, #0a0a0f 50%, #08080b 100%);
        color: rgba(255,255,255,0.9);
        font-family: "Inter", "SF Pro Display", system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        overflow: hidden;
    }

    #app_root::before,
    #app_root::after {
        content: "";
        position: fixed;
        inset: -140px;
        pointer-events: none;
        filter: blur(120px);
        z-index: 0;
        animation: auroraDrift 28s ease-in-out infinite alternate;
    }

    #app_root::before {
        background: radial-gradient(circle at 18% 22%, rgba(120,200,255,0.22), transparent 42%),
                    radial-gradient(circle at 78% 18%, rgba(200,140,255,0.18), transparent 40%),
                    radial-gradient(circle at 36% 80%, rgba(90,220,200,0.18), transparent 36%);
    }

    #app_root::after {
        background: radial-gradient(circle at 64% 68%, rgba(120,90,255,0.16), transparent 44%),
                    radial-gradient(circle at 32% 62%, rgba(255,140,120,0.12), transparent 40%),
                    radial-gradient(circle at 82% 74%, rgba(90,180,255,0.16), transparent 42%);
        animation-direction: alternate-reverse;
    }

    #app_root > * {
        position: relative;
        z-index: 1;
    }

    #glass_app {
        position: relative;
        background: rgba(18,18,22,0.34);
        border: 1px solid rgba(255,255,255,0.12);
        border-radius: 20px;
        padding: 18px;
        box-shadow: 0 22px 60px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255,0.06);
        backdrop-filter: blur(20px) saturate(160%);
        -webkit-backdrop-filter: blur(20px) saturate(160%);
    }

    #glass_app::before {
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        mix-blend-mode: screen;
        pointer-events: none;
    }

    #glass_app * {
        color: rgba(255,255,255,0.92);
        text-shadow: 0 1px 4px rgba(0,0,0,0.55);
    }

    #glass_app .nai-header-title {
        text-align: center;
        margin: 12px 0 10px 0;
    }

    #glass_app .nai-header-title h1 {
        font-weight: 500;
        letter-spacing: 0.26em;
        font-size: 1.6rem;
        text-transform: uppercase;
        color: rgba(255,255,255,0.92);
        text-shadow: 0 18px 48px rgba(0,0,0,0.55), 0 0 26px rgba(255,255,255,0.18);
    }

    #glass_app .nai-header-title span.version {
        font-weight: 800;
        color: #9fd8ff;
        text-shadow: 0 0 26px rgba(111,190,255,0.68);
    }

    #glass_app .section-title {
        font-size: 0.94rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.94);
        display: inline-flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 8px;
        padding: 8px 12px;
        border-radius: 12px;
        background: linear-gradient(160deg, rgba(4,4,6,0.78), rgba(12,12,16,0.8));
        border: 1px solid rgba(255,255,255,0.12);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 18px rgba(0,0,0,0.4);
    }

    #glass_app .section-title::before {
        content: "";
        width: 6px;
        height: 6px;
        border-radius: 999px;
        background: radial-gradient(circle, rgba(255,255,255,0.9) 0, rgba(159,216,255,0.65) 100%);
        box-shadow: 0 0 14px rgba(159,216,255,0.6);
    }

    #glass_app label span {
        color: rgba(255,255,255,0.92) !important;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        text-shadow: 0 1px 4px rgba(0,0,0,0.55);
    }

    #glass_app .glass-box {
        background: linear-gradient(175deg, rgba(6,6,10,0.82), rgba(16,16,22,0.78));
        border-radius: 16px;
        border: 1px solid rgba(255,255,255,0.14);
        box-shadow: 0 18px 42px rgba(0,0,0,0.55), inset 0 1px 0 rgba(255,255,255,0.08);
        padding: 14px 16px;
        backdrop-filter: blur(16px) saturate(150%);
        -webkit-backdrop-filter: blur(16px) saturate(150%);
    }

    #glass_app .glass-box p,
    #glass_app .glass-box span,
    #glass_app .glass-box label,
    #glass_app .glass-box h1,
    #glass_app .glass-box h2,
    #glass_app .glass-box h3,
    #glass_app .glass-box h4,
    #glass_app .glass-box h5,
    #glass_app .glass-box h6,
    #glass_app .glass-box .section-title,
    #glass_app .glass-box .status-label span,
    #glass_app .glass-box .status-label label {
        color: rgba(255,255,255,0.95) !important;
        text-shadow: 0 1px 4px rgba(0,0,0,0.6);
    }

    #glass_app input,
    #glass_app textarea,
    #glass_app select,
    #glass_app button {
        background: rgba(4,4,8,0.75);
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.16);
        color: rgba(255,255,255,0.95);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 8px 26px rgba(0,0,0,0.45);
    }

    #glass_app textarea::placeholder,
    #glass_app input::placeholder {
        color: rgba(207,207,207,0.9);
    }

    #glass_app input:focus,
    #glass_app textarea:focus,
    #glass_app select:focus,
    #glass_app button:focus {
        outline: none;
        border-color: rgba(159,216,255,0.5);
        box-shadow: 0 0 24px rgba(159,216,255,0.35), inset 0 1px 0 rgba(255,255,255,0.12);
    }

    #glass_app button {
        cursor: pointer;
        transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
    }

    #glass_app button:hover {
        transform: translateY(-1px);
        box-shadow: 0 14px 32px rgba(0,0,0,0.45), 0 0 18px rgba(159,216,255,0.28);
    }

    #glass_tabs [role="tab"] {
        background: rgba(18,18,24,0.7);
        border-radius: 12px;
        border: 1px solid rgba(255,255,255,0.12);
        color: rgba(255,255,255,0.85);
        padding: 8px 16px;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.05), 0 8px 20px rgba(0,0,0,0.35);
    }

    #glass_tabs [role="tab"].selected {
        background: linear-gradient(135deg, rgba(90,140,255,0.35), rgba(90,90,130,0.45));
        border-color: rgba(255,255,255,0.18);
        box-shadow: 0 0 18px rgba(159,216,255,0.35), inset 0 1px 0 rgba(255,255,255,0.18);
        color: rgba(255,255,255,0.95);
    }

    #btn-run button, #btn-stop button, #btn-refresh button, #btn-prev button, #btn-next button {
        background: rgba(10,10,14,0.58);
        border-radius: 14px;
        border: 1px solid rgba(255,255,255,0.18);
        color: rgba(255,255,255,0.9);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 12px 28px rgba(0,0,0,0.5);
    }

    #btn-run button {
        background: linear-gradient(135deg, rgba(120,180,255,0.9), rgba(80,200,255,0.85));
        color: #0b1323;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700;
    }

    #btn-stop button {
        background: linear-gradient(135deg, rgba(255,120,140,0.9), rgba(140,40,60,0.9));
        color: #ffecec;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700;
    }

    #btn-refresh button {
        background: linear-gradient(135deg, rgba(80,200,160,0.85), rgba(90,190,255,0.82));
        color: #052f2f;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        font-weight: 700;
    }

    #btn-prev button, #btn-next button {
        border-radius: 999px;
        letter-spacing: 0.08em;
        font-weight: 800;
        background: linear-gradient(135deg, rgba(120,150,255,0.9), rgba(200,160,255,0.88));
        color: #0c0f18;
    }

    #glass_app .status-label span, #glass_app .status-label label {
        font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Courier New", monospace !important;
        font-size: 0.78rem !important;
        color: rgba(230,233,240,0.95) !important;
    }

    #glass_app .glass-gallery img {
        border-radius: 10px;
        border: 1px solid rgba(255,255,255,0.08);
        box-shadow: 0 10px 24px rgba(0,0,0,0.35);
    }

    #glass_app .glass-gallery button.selected,
    #glass_app .glass-gallery button.selected img,
    #glass_app .glass-gallery img.selected {
        outline: 3px solid rgba(159,216,255,0.8) !important;
        outline-offset: -2px !important;
        box-shadow: 0 0 0 2px rgba(159,216,255,0.5) !important;
    }

    @keyframes auroraDrift {
        0% { transform: translate3d(-8%, -6%, 0) scale(1.02); }
        50% { transform: translate3d(6%, 4%, 0) scale(1.05); }
        100% { transform: translate3d(10%, 8%, 0) scale(1.08); }
    }
</style>
"""

KEYBIND_JS = """
() => {
  if (window.__nai_arrow_bound) return;
  window.__nai_arrow_bound = true;

  function handler(e) {
    const tag = (e.target && e.target.tagName || "").toLowerCase();
    if (tag === "input" || tag === "textarea") return;
    if (e.key !== "ArrowLeft" && e.key !== "ArrowRight") return;

    const app = document.querySelector("gradio-app");
    const root = app && app.shadowRoot ? app.shadowRoot : document;

    const prevRoot = root.getElementById("btn-prev");
    const nextRoot = root.getElementById("btn-next");
    if (!prevRoot || !nextRoot) return;

    const prevBtn = prevRoot.querySelector("button") || prevRoot;
    const nextBtn = nextRoot.querySelector("button") || nextRoot;

    if (e.key === "ArrowLeft") {
      e.preventDefault();
      prevBtn.click();
    } else if (e.key === "ArrowRight") {
      e.preventDefault();
      nextBtn.click();
    }
  }

  window.addEventListener("keydown", handler, true);
}
"""

# ==========================================
# [NovelAI 이미지 생성 로직 - V0 버전 그대로 사용]
# ==========================================
def generate_image(token, model_name, base_prompt, char1, char2, negative_prompt,
                   guidance, rescale, width, height, seed):
    """
    NovelAI v4.5 구조 (V0에서 사용하던 안정적인 버전):
    - base_prompt -> 긍정 프롬프트
    - char1, char2 -> 캐릭터 프롬프트(v4_prompt.char_captions)
    - negative_prompt -> 부정 프롬프트 & v4_negative_prompt
    - sampler -> k_euler_ancestral
    """

    if not model_name or not model_name.strip():
        model_name = DEFAULT_MODEL
    model_name = model_name.strip()

    # 메인 / 캐릭터 / 부정 정리
    main_prompt = (base_prompt or "").strip()
    neg_prompt = (negative_prompt or "").strip()
    char_prompts = []
    for cp in [char1, char2]:
        cp = (cp or "").strip()
        if cp:
            char_prompts.append(cp)

    url = "https://image.novelai.net/ai/generate-image"
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Origin": "https://novelai.net",
        "Referer": "https://novelai.net/"
    }

    try:
        seed_int = int(seed)
    except Exception:
        seed_int = DEFAULT_SEED

    # V0에서 쓰던 기본 파라미터
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
        "seed": seed_int,
        "extra_noise_seed": seed_int,
        "skip_cfg_above_sigma": None,
        "sm": False,
        "sm_dyn": False,
        "add_original_image": True,
        "use_coords": False,
        "deliberate_euler_ancestral_bug": False,
        "prefer_brownian": True,
    }

    # v4.0+용 caption 구조
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

        # 캐릭터 프롬프트 채워넣기
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

    try:
        res = requests.post(url, json=payload, headers=headers, timeout=180)
    except Exception as e:
        print(f"[NovelAI ERROR] 요청 실패: {e}")
        return None

    if res.status_code != 200:
        try:
            print(f"[NovelAI ERROR] HTTP {res.status_code}: {res.text}")
        except Exception:
            print(f"[NovelAI ERROR] HTTP {res.status_code}")
        return None

    # ZIP -> PNG 추출
    try:
        z = zipfile.ZipFile(io.BytesIO(res.content))
        name_list = z.namelist()
        if not name_list:
            return None
        img_bytes = z.read(name_list[0])
        return Image.open(io.BytesIO(img_bytes))
    except Exception as e:
        print(f"[NovelAI ERROR] 응답 처리 실패: {e}")
        return None

# ==========================================
# [GENERATOR: V0의 run_generator 사용]
# ==========================================
def run_generator(token, model_name, root_path, folder_name,
                  base, c1, c2, neg, seed,
                  g_s, g_e, g_stp, r_s, r_e, r_stp):
    """
    Prompt Guidance (X축), Guidance Rescale(Y축) 을 모두 스캔하면서
    동일 seed로 이미지 그리드를 자동 생성.
    (V0에서 사용하던 검증된 버전)
    """
    global is_running
    is_running = True

    if not token:
        yield None, "⚠️ TOKEN REQUIRED", "IDLE"
        return

    if not root_path or not root_path.strip():
        root_path = "C:\\NAI_Artworks"
    if not folder_name or not folder_name.strip():
        folder_name = time.strftime("%Y%m%d_%H%M%S")

    save_path = os.path.join(root_path, folder_name)
    os.makedirs(save_path, exist_ok=True)

    # Seed 고정
    try:
        seed_int = int(seed)
    except Exception:
        seed_int = DEFAULT_SEED

    # Guidance / Rescale 리스트 계산
    g_list = [x / 10.0 for x in range(int(g_s * 10), int(g_e * 10) + 1, int(max(1, g_stp * 10)))]
    r_list = [x / 10.0 for x in range(int(r_s * 10), int(r_e * 10) + 1, int(max(1, r_stp * 10)))]

    total = len(g_list) * len(r_list)
    count = 0

    yield None, f"🚀 STARTING... ({total} IMAGES)", f"0 / {total}"

    for g in g_list:
        for r in r_list:
            if not is_running:
                yield None, "🛑 ABORTED", f"{count} / {total}"
                return

            count += 1
            fname = f"G{g:.1f}_R{r:.1f}.png"
            fpath = os.path.join(save_path, fname)
            status_msg = f"Generating... G:{g:.1f} / R:{r:.1f} | Seed:{seed_int}"
            yield None, status_msg, f"{count} / {total}"

            if os.path.exists(fpath):
                # 이미 만들어진 경우 스킵
                continue

            img = generate_image(
                token=token,
                model_name=model_name,
                base_prompt=base,
                char1=c1,
                char2=c2,
                negative_prompt=neg,
                guidance=g,
                rescale=r,
                width=IMG_W,
                height=IMG_H,
                seed=seed_int,
            )

            if img:
                img.save(fpath)
                # 한 번씩 프리뷰도 보여주고 싶으면 여기서 img를 넘김
                yield img, f"✅ SAVED: {fname}", f"{count} / {total}"
                time.sleep(1.0)
            else:
                yield None, f"❌ ERROR at G:{g:.1f} R:{r:.1f}", f"{count} / {total}"
                time.sleep(1.0)

    yield None, "🎉 COMPLETED", f"{count} / {total}"

def stop_gen():
    """
    V0의 stop_gen을 조금 확장해서
    - SYSTEM LOG
    - STATUS
    둘 다 갱신
    """
    global is_running
    is_running = False
    return "🛑 STOPPING...", "STOP"

# ==========================================
# [아카이브 뷰어 유틸 - V0.1 코드 그대로]
# ==========================================
def get_subfolders(root_path):
    if not os.path.exists(root_path):
        return []
    folders = [f for f in os.listdir(root_path) if os.path.isdir(os.path.join(root_path, f))]
    folders.sort(reverse=True)
    return folders

def get_images_in_project(root_path, folder):
    folder_path = os.path.join(root_path, folder)
    if not os.path.isdir(folder_path):
        return []
    files = [
        os.path.join(folder_path, f)
        for f in os.listdir(folder_path)
        if f.lower().endswith(".png")
    ]
    files.sort()
    return files

def parse_gr_from_filename(filename):
    """파일명 예: G4.0_R0.3.png -> (4.0, 0.3)"""
    m = re.search(r"G(\d+(?:\.\d)?)_R(\d+(?:\.\d)?)", filename)
    if not m:
        return None, None
    return float(m.group(1)), float(m.group(2))

def infer_grid_shape(image_paths):
    """
    파일명에서 서로 다른 G / R 값을 세어서
    - Guidance = Y축 (rows)
    - Rescale = X축 (columns)
    """
    g_vals = set()
    r_vals = set()
    for p in image_paths:
        g, r = parse_gr_from_filename(os.path.basename(p))
        if g is not None:
            g_vals.add(g)
        if r is not None:
            r_vals.add(r)
    if not g_vals or not r_vals:
        return None, None
    cols = len(sorted(r_vals))  # x축: Rescale
    rows = len(sorted(g_vals))  # y축: Guidance
    return cols, rows

def make_status(idx, total, path):
    basename = os.path.basename(path)
    g_val, r_val = parse_gr_from_filename(basename)
    if total <= 0:
        return "No images", None, None
    prefix = f"[{idx+1}/{total}] "
    mid = f"G={g_val:.1f}  R={r_val:.1f}" if g_val is not None else "G/R unknown"
    return f"{prefix}{mid} | {basename}", g_val, r_val

def refresh_archives(root_path):
    folders = get_subfolders(root_path)
    if not folders:
        dropdown = gr.Dropdown(choices=[], value=None)
        gallery_upd = gr.update(value=[], label="GRID (0 images)")
        status = "No projects"
        images = []
        idx = -1
        view_upd = gr.update(value=None, visible=False)
        g_upd = gr.update(value=0.0)
        r_upd = gr.update(value=0.0)
        return dropdown, status, gallery_upd, images, idx, view_upd, g_upd, r_upd

    first = folders[0]
    images = get_images_in_project(root_path, first)
    cols, rows = infer_grid_shape(images)
    if cols is None:
        cols, rows = 6, 3
    gallery_upd = gr.update(
        value=images,
        label=f"{first} ({len(images)} images)",
        columns=cols,
        rows=rows
    )
    status = f"{first}: {len(images)} images"
    idx = -1
    view_upd = gr.update(value=None, visible=False)
    g_upd = gr.update(value=0.0)
    r_upd = gr.update(value=0.0)
    dropdown = gr.Dropdown(choices=folders, value=first)
    return dropdown, status, gallery_upd, images, idx, view_upd, g_upd, r_upd

def load_project(root_path, folder):
    if not folder:
        gallery_upd = gr.update(value=[], label="GRID (0 images)")
        images = []
        idx = -1
        view_upd = gr.update(value=None, visible=False)
        status = "No project selected"
        g_upd = gr.update(value=0.0)
        r_upd = gr.update(value=0.0)
        return gallery_upd, images, idx, view_upd, status, g_upd, r_upd

    images = get_images_in_project(root_path, folder)
    cols, rows = infer_grid_shape(images)
    if cols is None:
        cols, rows = 6, 3
    gallery_upd = gr.update(
        value=images,
        label=f"{folder} ({len(images)} images)",
        columns=cols,
        rows=rows
    )
    status = f"{folder}: {len(images)} images"
    idx = -1
    view_upd = gr.update(value=None, visible=False)
    g_upd = gr.update(value=0.0)
    r_upd = gr.update(value=0.0)
    if not images:
        status = "No images"
    return gallery_upd, images, idx, view_upd, status, g_upd, r_upd

def on_gallery_select(evt: gr.SelectData, images, current_index):
    """
    썸네일 클릭 시:
    - DISPLAY 이미지
    - index_state / G / R / FILE INFO 갱신
    """
    if not images:
        return gr.update(value=None, visible=False), -1, "No images", gr.update(), gr.update()

    total = len(images)

    idx = None
    if evt is not None:
        val = getattr(evt, "value", None)
        if isinstance(val, str) and val in images:
            idx = images.index(val)
        else:
            raw_idx = getattr(evt, "index", None)
            if isinstance(raw_idx, int):
                idx = raw_idx

    if idx is None or idx < 0 or idx >= total:
        idx = 0

    path = images[idx]
    status, g_val, r_val = make_status(idx, total, path)

    g_upd = gr.update(value=g_val) if g_val is not None else gr.update()
    r_upd = gr.update(value=r_val) if r_val is not None else gr.update()

    return gr.update(value=path, visible=True), idx, status, g_upd, r_upd

def _navigate(images, current_index, step):
    """
    PREV / NEXT 버튼(그리고 키보드)에서 사용:
    - DISPLAY + G/R + FILE INFO 갱신
    - Gallery 선택 썸네일도 함께 이동
    """
    if not images:
        return gr.update(value=None, visible=False), current_index, "No images", gr.update(), gr.update(), gr.update()

    total = len(images)
    if total == 0:
        return gr.update(value=None, visible=False), current_index, "No images", gr.update(), gr.update(), gr.update()

    if current_index is None or current_index < 0:
        idx = 0 if step > 0 else total - 1
    else:
        idx = (current_index + step) % total

    path = images[idx]
    status, g_val, r_val = make_status(idx, total, path)

    g_upd = gr.update(value=g_val) if g_val is not None else gr.update()
    r_upd = gr.update(value=r_val) if r_val is not None else gr.update()

    gallery_upd = gr.update(selected_index=idx)

    return gr.update(value=path, visible=True), idx, status, g_upd, r_upd, gallery_upd

def nav_prev(images, current_index):
    return _navigate(images, current_index, step=-1)

def nav_next(images, current_index):
    return _navigate(images, current_index, step=+1)

# ==========================================
# [UI 구성]
# ==========================================
with gr.Blocks(title="NAI Studio V4.5 Lab", elem_id="app_root") as demo:
    gr.HTML(UI_STYLE_PATCH)

    with gr.Group(elem_id="glass_app"):
        with gr.Row():
            gr.HTML(
                """
                <div class="nai-header-title">
                    <h1>NAI STUDIO <span class="version">V4.5 LAB</span></h1>
                </div>
                """
            )

        # 키보드 바인딩용 더미 컴포넌트 (실제 화면에는 안 보임)
        keybind_dummy = gr.HTML("", visible=False)

        default_root = "C:\\NAI_Artworks"

        # 아카이브용 상태
        images_state = gr.State([])
        index_state = gr.State(-1)

        with gr.Tabs(elem_id="glass_tabs"):
            # ------------------ [GENERATOR] ------------------
            with gr.TabItem("GENERATOR"):
                with gr.Row():
                    with gr.Column(scale=4):
                        with gr.Group(elem_classes="glass-box"):
                            gr.Markdown("<div class='section-title'>01. SYSTEM ACCESS</div>")
                            token_in = gr.Textbox(label="ACCESS TOKEN", type="password")
                            model_in = gr.Textbox(
                                label="MODEL",
                                value=DEFAULT_MODEL,
                                info="예: nai-diffusion-4-5-full / nai-diffusion-4-5-curated / nai-diffusion-4-full"
                            )
                            root_in = gr.Textbox(label="ROOT PATH", value=default_root)
                            folder_name_in = gr.Textbox(label="PROJECT NAME", placeholder="20251123_000000")

                        with gr.Group(elem_classes="glass-box"):
                            gr.Markdown("<div class='section-title'>02. PROMPTS</div>")
                            base_in = gr.TextArea(
                                label="BASE PROMPT",
                                value="1girl, solo, best quality, masterpiece",
                                lines=2
                            )
                            with gr.Row():
                                c1_in = gr.Textbox(label="CHARACTER 1")
                                c2_in = gr.Textbox(label="CHARACTER 2")
                            neg_in = gr.TextArea(
                                label="NEGATIVE PROMPT",
                                value="lowres, worst quality, bad anatomy, extra limbs",
                                lines=2
                            )

                        with gr.Group(elem_classes="glass-box"):
                            gr.Markdown("<div class='section-title'>03. PARAMETERS</div>")
                            seed_in = gr.Number(
                                label="SEED",
                                value=DEFAULT_SEED,
                                precision=0,
                                info="동일 Seed 로 Guidance / Rescale 만 변경",
                            )

                            gr.Markdown("**PROMPT GUIDANCE (scale, X축)**")
                            with gr.Row():
                                g_s = gr.Number(label="START", value=0.0)
                                g_e = gr.Number(label="END", value=8.0)
                                g_step = gr.Number(label="STEP", value=0.5)

                            gr.Markdown("**GUIDANCE RESCALE (cfg_rescale, Y축)**")
                            with gr.Row():
                                r_s = gr.Number(label="START", value=0.0)
                                r_e = gr.Number(label="END", value=1.0)
                                r_stp = gr.Number(label="STEP", value=0.1)

                        with gr.Row():
                            btn_run = gr.Button("INITIALIZE RUN", elem_id="btn-run", scale=2)
                            btn_stop = gr.Button("ABORT", elem_id="btn-stop", scale=1)

                    with gr.Column(scale=5):
                        with gr.Group(elem_classes="glass-box"):
                            gr.Markdown("<div class='section-title'>LIVE FEED</div>")
                            lbl_prog = gr.Label(value="READY", label="STATUS", elem_classes=["status-label"])
                            img_preview = gr.Image(label="PREVIEW", height=600, interactive=False, type="pil")
                            txt_log = gr.Textbox(label="SYSTEM LOG", lines=4, interactive=False)

            # ------------------ [ARCHIVE VIEWER] ------------------
            with gr.TabItem("ARCHIVE VIEWER"):
                with gr.Row():
                    with gr.Column(scale=2):
                        with gr.Group(elem_classes="glass-box", elem_id="grp-archive-select"):
                            gr.Markdown("<div class='section-title'>ARCHIVE SELECT</div>")
                            view_root_in = gr.Textbox(label="ROOT PATH", value=default_root)
                            btn_refresh = gr.Button("REFRESH LIST", elem_id="btn-refresh")
                            folder_dropdown = gr.Dropdown(label="SELECT PROJECT", choices=[], interactive=True)
                            status_view = gr.Label(label="FILE INFO")

                        with gr.Group(elem_classes="glass-box", elem_id="grp-current-gr"):
                            gr.Markdown("<div class='section-title'>CURRENT G / R</div>")
                            slider_g = gr.Slider(0, 20, value=0.0, step=0.1, label="GUIDANCE", interactive=False)
                            slider_r = gr.Slider(0, 1, value=0.0, step=0.1, label="RESCALE", interactive=False)

                    with gr.Column(scale=6):
                        with gr.Group(elem_classes="glass-box"):
                            gr.Markdown("<div class='section-title'>ARCHIVE GRID & VIEWER</div>")
                            gallery = gr.Gallery(
                                label="GRID",
                                show_label=True,
                                columns=6,  # 실제 열/행은 refresh/load 에서 동적으로 설정
                                rows=3,
                                height=420,
                                allow_preview=False,
                                preview=False,
                                interactive=True,
                                type="filepath",
                                elem_classes=["glass-gallery"],
                            )
                            view_display = gr.Image(
                                label="DISPLAY",
                                interactive=False,
                                type="filepath",
                                height=760,
                                visible=False,
                            )
                            with gr.Row():
                                btn_prev = gr.Button("◀ PREV", scale=1, elem_id="btn-prev")
                                btn_next = gr.Button("NEXT ▶", scale=1, elem_id="btn-next")

    # ==== GENERATOR 이벤트 (V0 run_generator 사용) ====
    btn_run.click(
        run_generator,
        inputs=[
            token_in,
            model_in,
            root_in,
            folder_name_in,
            base_in,
            c1_in,
            c2_in,
            neg_in,
            seed_in,
            g_s,
            g_e,
            g_step,
            r_s,
            r_e,
            r_stp
        ],
        outputs=[img_preview, txt_log, lbl_prog]
    )

    btn_stop.click(
        stop_gen,
        inputs=[],
        outputs=[txt_log, lbl_prog]
    )

    # ==== ARCHIVE 이벤트 (V0.1 그대로) ====
    btn_refresh.click(
        refresh_archives,
        inputs=[view_root_in],
        outputs=[
            folder_dropdown,
            status_view,
            gallery,
            images_state,
            index_state,
            view_display,
            slider_g,
            slider_r
        ]
    )

    folder_dropdown.change(
        load_project,
        inputs=[view_root_in, folder_dropdown],
        outputs=[
            gallery,
            images_state,
            index_state,
            view_display,
            status_view,
            slider_g,
            slider_r
        ]
    )

    gallery.select(
        on_gallery_select,
        inputs=[images_state, index_state],
        outputs=[view_display, index_state, status_view, slider_g, slider_r]
    )

    btn_prev.click(
        nav_prev,
        inputs=[images_state, index_state],
        outputs=[view_display, index_state, status_view, slider_g, slider_r, gallery]
    )

    btn_next.click(
        nav_next,
        inputs=[images_state, index_state],
        outputs=[view_display, index_state, status_view, slider_g, slider_r, gallery]
    )

    # ==== 키보드 화살표 핸들러 JS 등록 ====
    keybind_dummy.load(
        lambda: None,
        inputs=[],
        outputs=[],
        js=KEYBIND_JS,
        queue=False,
    )

if __name__ == "__main__":
    print("==================================================")
    print(" [NAI Studio V4.5 Lab Started] ")
    print(" 브라우저가 열리지 않으면 아래 주소를 클릭하세요:")
    print(" http://127.0.0.1:7860 ")
    print("==================================================")
    demo.launch(
        inbrowser=True,
        show_error=True,
        allowed_paths=["C:\\NAI_Artworks"]
    )

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

## === GLASS SLIDER + AURORA BG PATCH START ===
# ==========================================
# [UI STYLE PATCH - Dark Glassmorphism]
# ==========================================
GLASS_DEFAULTS = {
    "blur": 20,
    "alpha": 0.32,
    "border_alpha": 0.16,
    "depth": 0.72,
    "inset": 0.8,
    "saturation": 160,
}

UI_STYLE_PATCH = f"""
<style>
    :root {{
        --glass-blur: {GLASS_DEFAULTS["blur"]}px;
        --glass-alpha: {GLASS_DEFAULTS["alpha"]};
        --glass-border-alpha: {GLASS_DEFAULTS["border_alpha"]};
        --glass-depth: {GLASS_DEFAULTS["depth"]};
        --glass-inset: {GLASS_DEFAULTS["inset"]};
        --glass-sat: {GLASS_DEFAULTS["saturation"]}%;
    }}

    #app_root {{
        position: relative;
        min-height: 100vh;
        padding: 18px;
        background: linear-gradient(180deg, #0b0d12 0%, #090b10 48%, #07080d 100%);
        color: rgba(255,255,255,0.9);
        font-family: "Inter", "SF Pro Display", system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        overflow: hidden;
    }}

    #app_root::before,
    #app_root::after {{
        content: "";
        position: fixed;
        inset: -160px;
        pointer-events: none;
        filter: blur(120px) saturate(120%);
        z-index: 0;
        animation: auroraDrift 22s ease-in-out infinite alternate;
        opacity: 0.9;
    }}

    #app_root::before {{
        background: radial-gradient(circle at 18% 18%, rgba(80,200,255,0.18), transparent 38%),
                    radial-gradient(circle at 74% 22%, rgba(150,110,255,0.16), transparent 42%),
                    radial-gradient(circle at 36% 74%, rgba(70,220,190,0.16), transparent 38%);
    }}

    #app_root::after {{
        background: radial-gradient(circle at 68% 64%, rgba(90,140,255,0.16), transparent 44%),
                    radial-gradient(circle at 28% 62%, rgba(255,140,120,0.12), transparent 42%),
                    radial-gradient(circle at 82% 74%, rgba(120,220,255,0.16), transparent 40%);
        animation-direction: alternate-reverse;
    }}

    #app_root > * {{
        position: relative;
        z-index: 1;
    }}

    #glass_app {{
        position: relative;
        background: rgba(18,18,24,var(--glass-alpha));
        border: 1px solid rgba(255,255,255,var(--glass-border-alpha));
        border-radius: 20px;
        padding: 18px;
        box-shadow:
            0 28px 64px rgba(0,0,0, calc(0.65 * var(--glass-depth))),
            0 12px 32px rgba(0,0,0, calc(0.55 * var(--glass-depth))),
            inset 0 1px 0 rgba(255,255,255, calc(0.12 * var(--glass-inset)));
        backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
        -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
    }}

    #glass_app::before {{
        content: "";
        position: absolute;
        inset: 0;
        border-radius: 20px;
        background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
        mix-blend-mode: screen;
        pointer-events: none;
        box-shadow: inset 0 0 0 1px rgba(255,255,255, calc(0.18 * var(--glass-inset)));
    }}

    #glass_app * {{
        color: rgba(255,255,255,0.92);
        text-shadow: 0 1px 4px rgba(0,0,0,0.55);
    }}

    #glass_app .nai-header-title {{
        text-align: center;
        margin: 12px 0 10px 0;
    }}

    #glass_app .nai-header-title h1 {{
        font-weight: 500;
        letter-spacing: 0.26em;
        font-size: 1.6rem;
        text-transform: uppercase;
        color: rgba(255,255,255,0.92);
        text-shadow: 0 18px 48px rgba(0,0,0,0.55), 0 0 26px rgba(255,255,255,0.18);
    }}

    #glass_app .nai-header-title span.version {{
        font-weight: 800;
        color: #9fd8ff;
        text-shadow: 0 0 26px rgba(111,190,255,0.68);
    }}

    #glass_app .section-title {{
        font-size: 0.94rem;
        font-weight: 700;
        letter-spacing: 0.18em;
        text-transform: uppercase;
        color: rgba(255,255,255,0.94);
        display: inline-flex;
        align-items: center;
        gap: 10px;
        padding: 10px 16px;
        margin: 4px 0 12px;
        border-radius: 999px;
        background: linear-gradient(90deg, rgba(0,0,0,0.55), rgba(26,26,40,0.4));
        border: 1px solid rgba(255,255,255,0.2);
        box-shadow: 0 4px 24px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.18);
    }}

    #glass_app .glass-box {{
        background: linear-gradient(180deg, rgba(10,12,16,0.9), rgba(10,10,14,0.82));
        border: 1px solid rgba(255,255,255,var(--glass-border-alpha));
        border-radius: 14px;
        padding: 14px;
        box-shadow: 0 22px 60px rgba(0,0,0,0.55), 0 1px 0 rgba(255,255,255,0.06), inset 0 1px 0 rgba(255,255,255, calc(0.1 * var(--glass-inset)));
        backdrop-filter: blur(calc(var(--glass-blur) * 0.8)) saturate(var(--glass-sat));
        -webkit-backdrop-filter: blur(calc(var(--glass-blur) * 0.8)) saturate(var(--glass-sat));
        margin-bottom: 12px;
    }}

    #glass_app .glass-box .wrap.svelte-1hlfj9y,
    #glass_app .glass-box .wrap.svelte-1f354aw,
    #glass_app .glass-box .wrap.svelte-w4709d {{
        background: rgba(10,10,14,0.85);
    }}

    #glass_app .glass-box .label.svelte-1f354aw,
    #glass_app .glass-box .label.svelte-1hlfj9y {{
        background: rgba(10,10,14,0.85);
    }}

    #glass_app .glass-box .svelte-1f354aw .slider,
    #glass_app .glass-box .svelte-1hlfj9y .slider {{
        background: rgba(255,255,255,0.04);
    }}

    #glass_tabs > .tab-nav {{
        background: rgba(12,12,18,0.5);
        border: 1px solid rgba(255,255,255,var(--glass-border-alpha));
        border-radius: 14px;
        margin-bottom: 10px;
        box-shadow: 0 8px 28px rgba(0,0,0,0.4), inset 0 1px 0 rgba(255,255,255,0.08);
    }}

    #glass_tabs button {{
        color: rgba(255,255,255,0.86);
        font-weight: 700;
        letter-spacing: 0.08em;
        border-radius: 12px;
        border: none;
        background: transparent;
        padding: 10px 16px;
        transition: all 0.2s ease;
    }}

    #glass_tabs button.selected {{
        background: rgba(255,255,255,0.08);
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 0 0 1px rgba(255,255,255,0.08);
        color: rgba(255,255,255,0.95);
    }}

    #glass_tabs button:hover {{
        background: rgba(255,255,255,0.06);
    }}

    #glass_app label,
    #glass_app .label,
    #glass_app .text-gray-600,
    #glass_app .prose p {{
        color: rgba(255,255,255,0.94) !important;
    }}

    #glass_app .status-label .wrap,
    #glass_app .status-label .wrap label,
    #glass_app .status-label .label-wrap,
    #glass_app .status-label .label-wrap label {{
        color: rgba(255,255,255,0.96) !important;
        background: rgba(0,0,0,0.35) !important;
        border-radius: 12px !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.12), 0 10px 28px rgba(0,0,0,0.35);
    }}

    #glass_app .status-label .value,
    #glass_app .status-label .value .wrap,
    #glass_app .status-label .value .wrap label {{
        color: #9fd8ff !important;
        text-shadow: 0 0 12px rgba(111,190,255,0.5);
    }}

    #glass_app textarea,
    #glass_app input,
    #glass_app select,
    #glass_app .gr-input,
    #glass_app .container.svelte-1pl0bqf,
    #glass_app .input-radio,
    #glass_app .input-checkbox,
    #glass_app .wrap.svelte-1pl0bqf,
    #glass_app .token.svelte-1pl0bqf,
    #glass_app .label-wrap,
    #glass_app .input-dropdown,
    #glass_app .select-input,
    #glass_app .filter-wrap {{
        background: rgba(0,0,0,0.45) !important;
        border: 1px solid rgba(255,255,255,0.14) !important;
        border-radius: 12px !important;
        color: rgba(255,255,255,0.95) !important;
        box-shadow: inset 0 1px 0 rgba(255,255,255,0.08), 0 10px 20px rgba(0,0,0,0.35);
    }}

    #glass_app .input-radio:focus, #glass_app .input-checkbox:focus,
    #glass_app textarea:focus,
    #glass_app input:focus,
    #glass_app select:focus,
    #glass_app .input-dropdown:focus,
    #glass_app .select-input:focus,
    #glass_app .filter-wrap:focus-within {{
        outline: none !important;
        border-color: rgba(111,190,255,0.65) !important;
        box-shadow: 0 0 0 1px rgba(111,190,255,0.4), 0 12px 30px rgba(111,190,255,0.28);
    }}

    #glass_app textarea::placeholder,
    #glass_app input::placeholder,
    #glass_app .prose p,
    #glass_app .secondary {{
        color: rgba(220,220,220,0.76) !important;
    }}

    #glass_app button,
    #glass_app .btn,
    #glass_app .checkbox,
    #glass_app .radio {{
        border-radius: 12px !important;
        background: linear-gradient(145deg, rgba(255,255,255,0.08), rgba(255,255,255,0.04));
        border: 1px solid rgba(255,255,255,0.12);
        color: rgba(255,255,255,0.94) !important;
        box-shadow: 0 12px 32px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.12);
        transition: all 0.2s ease;
    }}

    #glass_app button:hover,
    #glass_app .btn:hover {{
        background: linear-gradient(145deg, rgba(255,255,255,0.12), rgba(255,255,255,0.06));
        box-shadow: 0 14px 34px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.18);
    }}

    #glass_app button:active,
    #glass_app .btn:active {{
        transform: translateY(1px);
        box-shadow: 0 10px 22px rgba(0,0,0,0.38), inset 0 1px 0 rgba(255,255,255,0.14);
    }}

    #btn-run {{
        background: linear-gradient(145deg, rgba(111,190,255,0.18), rgba(111,190,255,0.06));
        border: 1px solid rgba(111,190,255,0.35);
        box-shadow: 0 16px 40px rgba(111,190,255,0.32), inset 0 1px 0 rgba(255,255,255,0.18);
    }}

    #btn-run:hover {{
        box-shadow: 0 18px 46px rgba(111,190,255,0.42), inset 0 1px 0 rgba(255,255,255,0.22);
    }}

    #btn-stop {{
        background: linear-gradient(145deg, rgba(255,120,120,0.12), rgba(255,120,120,0.06));
        border: 1px solid rgba(255,120,120,0.28);
    }}

    #btn-prev,
    #btn-next,
    #btn-refresh {{
        background: linear-gradient(145deg, rgba(120,255,200,0.10), rgba(120,255,200,0.05));
        border: 1px solid rgba(120,255,200,0.24);
    }}

    #btn-prev:hover,
    #btn-next:hover,
    #btn-refresh:hover {{
        box-shadow: 0 14px 36px rgba(120,255,200,0.25), inset 0 1px 0 rgba(255,255,255,0.14);
    }}

    .glass-gallery > div {{
        background: rgba(0,0,0,0.45) !important;
        border-radius: 12px !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        box-shadow: 0 12px 24px rgba(0,0,0,0.35) !important;
    }}

    .glass-gallery img {{
        border-radius: 10px !important;
        object-fit: cover !important;
    }}

    .glass-gallery .selected img {{
        box-shadow: 0 0 0 2px rgba(111,190,255,0.65) !important;
    }}

    textarea:focus, input:focus, select:focus {{
        outline: none !important;
    }}

    #glass-settings .gradio-accordion-content {{ padding-top: 6px; }}
    #glass-settings .glass-settings-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 12px; }}
    #glass-settings .glass-settings-card {{ background: rgba(12,12,18,0.72); border: 1px solid rgba(255,255,255,0.12); border-radius: 12px; padding: 12px; box-shadow: 0 18px 38px rgba(0,0,0,0.45), inset 0 1px 0 rgba(255,255,255,0.08); backdrop-filter: blur(14px) saturate(140%); }}
    #glass-settings .glass-settings-card h4 {{ margin: 0 0 8px; letter-spacing: 0.08em; text-transform: uppercase; font-size: 0.82rem; color: rgba(255,255,255,0.86); }}
    #glass-settings .glass-settings-code {{ border-radius: 12px; overflow: hidden; }}
    #glass-settings .copy-tip {{ color: rgba(255,255,255,0.7); font-size: 0.88rem; margin-top: 6px; text-shadow: none; }}

    @keyframes auroraDrift {{
        0% {{ transform: translate3d(-12px, 14px, 0) scale(1.02); }}
        50% {{ transform: translate3d(22px, -18px, 0) scale(1.05); }}
        100% {{ transform: translate3d(-18px, 12px, 0) scale(1.02); }}
    }}
</style>
"""


def render_glass_var_style(blur, alpha, border_alpha, depth, inset, saturation):
    return (
        "<style id=\"dynamic_glass_vars\">:root{"
        f"--glass-blur:{blur}px;"
        f"--glass-alpha:{alpha};"
        f"--glass-border-alpha:{border_alpha};"
        f"--glass-depth:{depth};"
        f"--glass-inset:{inset};"
        f"--glass-sat:{saturation}%;" "}</style>"
    )


def render_glass_css_snippet(blur, alpha, border_alpha, depth, inset, saturation):
    return (
        ".glass-card {\n"
        f"  background: rgba(18,18,24,{alpha});\n"
        f"  border: 1px solid rgba(255,255,255,{border_alpha});\n"
        "  border-radius: 20px;\n"
        f"  backdrop-filter: blur({blur}px) saturate({saturation}%);\n"
        f"  -webkit-backdrop-filter: blur({blur}px) saturate({saturation}%);\n"
        "  box-shadow: \n"
        f"    0 28px 64px rgba(0,0,0,{0.65 * depth}),\n"
        f"    0 12px 32px rgba(0,0,0,{0.55 * depth}),\n"
        f"    inset 0 1px 0 rgba(255,255,255,{0.12 * inset});\n"
        f"  outline: 1px solid rgba(255,255,255,{0.18 * inset});\n"
        "}\n"
    )


def update_glass_styles(blur, alpha, border_alpha, depth, inset, saturation):
    return render_glass_var_style(blur, alpha, border_alpha, depth, inset, saturation), render_glass_css_snippet(
        blur,
        alpha,
        border_alpha,
        depth,
        inset,
        saturation,
    )


COPY_CSS_JS = "(css) => { if (!css) return; navigator.clipboard.writeText(css); }"


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

## === GLASS SLIDER + AURORA BG PATCH END ===

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

        glass_style_vars = gr.HTML(
            render_glass_var_style(
                GLASS_DEFAULTS["blur"],
                GLASS_DEFAULTS["alpha"],
                GLASS_DEFAULTS["border_alpha"],
                GLASS_DEFAULTS["depth"],
                GLASS_DEFAULTS["inset"],
                GLASS_DEFAULTS["saturation"],
            ),
            elem_id="glass-style-vars",
        )

        with gr.Accordion("Glass Settings", open=False, elem_id="glass-settings"):
            gr.Markdown(
                "<div class='section-title'>Glass Controls</div><p class='copy-tip'>Adjust blur, transparency, border and shadow depth to preview the glassmorphism feel live.</p>",
                elem_classes=["glass-settings-card"],
            )
            with gr.Row():
                with gr.Column():
                    with gr.Group(elem_classes=["glass-settings-card"]):
                        glass_blur = gr.Slider(0, 40, value=GLASS_DEFAULTS["blur"], step=1, label="Blur (px)")
                        glass_alpha = gr.Slider(0.0, 0.5, value=GLASS_DEFAULTS["alpha"], step=0.01, label="Glass Alpha")
                        glass_border = gr.Slider(0.0, 0.6, value=GLASS_DEFAULTS["border_alpha"], step=0.01, label="Border Alpha")
                with gr.Column():
                    with gr.Group(elem_classes=["glass-settings-card"]):
                        glass_depth = gr.Slider(0.0, 1.0, value=GLASS_DEFAULTS["depth"], step=0.01, label="Shadow Depth")
                        glass_inset = gr.Slider(0.0, 2.0, value=GLASS_DEFAULTS["inset"], step=0.05, label="Inset Highlight")
                        glass_sat = gr.Slider(80, 220, value=GLASS_DEFAULTS["saturation"], step=5, label="Saturation (%)")

            glass_css_code = gr.Code(
                value=render_glass_css_snippet(
                    GLASS_DEFAULTS["blur"],
                    GLASS_DEFAULTS["alpha"],
                    GLASS_DEFAULTS["border_alpha"],
                    GLASS_DEFAULTS["depth"],
                    GLASS_DEFAULTS["inset"],
                    GLASS_DEFAULTS["saturation"],
                ),
                language="css",
                label="Generated CSS",
                lines=12,
                elem_classes=["glass-settings-code"],
            )
            copy_btn = gr.Button("Copy CSS", elem_id="btn-copy-css")
            gr.Markdown("<div class='copy-tip'>Uses only custom selectors. Copy to reuse this glass card styling.</div>")

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

    slider_inputs = [glass_blur, glass_alpha, glass_border, glass_depth, glass_inset, glass_sat]
    for _slider in slider_inputs:
        _slider.input(
            update_glass_styles,
            inputs=slider_inputs,
            outputs=[glass_style_vars, glass_css_code],
        )

    copy_btn.click(None, inputs=[glass_css_code], outputs=[], js=COPY_CSS_JS)

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

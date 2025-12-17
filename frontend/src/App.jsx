import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const defaultMatrix = {
  xParam: 'R',
  yParam: 'G',
  xMin: 0,
  xMax: 0.7,
  xStep: 0.1,
  yMin: 3.0,
  yMax: 5.0,
  yStep: 0.2,
  autoX: true,
  autoY: true,
}

const defaultGlass = {
  blur: 22,
  alpha: 0.32,
  borderAlpha: 0.18,
  saturation: 160,
  depth: 0.7,
  inset: 0.9,
}

const MAX_SWEEP_IMAGES = 500
const FORM_STORAGE_KEY = 'generatorFormState'
const JOB_STORAGE_KEY = 'generatorJobState'

function applyGlassVars(settings) {
  const root = document.documentElement
  root.style.setProperty('--glass-blur', `${settings.blur}px`)
  root.style.setProperty('--glass-alpha', `${settings.alpha}`)
  root.style.setProperty('--glass-border-alpha', `${settings.borderAlpha}`)
  root.style.setProperty('--glass-sat', `${settings.saturation}%`)
  root.style.setProperty('--glass-depth', `${settings.depth}`)
  root.style.setProperty('--glass-inset', `${settings.inset}`)
}

function buildCssSnippet(settings) {
  return `:root {
  --glass-blur: ${settings.blur}px;
  --glass-alpha: ${settings.alpha};
  --glass-border-alpha: ${settings.borderAlpha};
  --glass-sat: ${settings.saturation}%;
  --glass-depth: ${settings.depth};
  --glass-inset: ${settings.inset};
}

.glass-card {
  background: rgba(18, 18, 22, var(--glass-alpha));
  backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  -webkit-backdrop-filter: blur(var(--glass-blur)) saturate(var(--glass-sat));
  border: 1px solid rgba(255, 255, 255, var(--glass-border-alpha));
  box-shadow:
    0 30px 80px rgba(0, 0, 0, calc(0.55 * var(--glass-depth))),
    0 16px 48px rgba(0, 0, 0, calc(0.45 * var(--glass-depth))),
    inset 0 1px 0 rgba(255,255,255, calc(0.18 * var(--glass-inset)));
  border-radius: 20px;
}`
}

function encodeRelpath(relpath = '') {
  return relpath
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/')
}

function formatTick(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return ''
  const formatter = new Intl.NumberFormat('en-US', { maximumFractionDigits: 1, minimumFractionDigits: 0 })
  return formatter.format(Number(value))
}

function parseParamsFromName(name = '') {
  const patterns = [
    /G(?<g>\d+(?:\.\d+)?)\D+R(?<r>\d+(?:\.\d+)?)/i,
    /R(?<r>\d+(?:\.\d+)?)\D+G(?<g>\d+(?:\.\d+)?)/i,
  ]
  for (const pattern of patterns) {
    const match = name.match(pattern)
    if (match && match.groups) {
      return {
        g: match.groups.g ? Number(match.groups.g) : null,
        r: match.groups.r ? Number(match.groups.r) : null,
      }
    }
  }
  return { g: null, r: null }
}

function buildTicks(min, max, step) {
  if (step <= 0 || max < min) return []
  const ticks = []
  for (let v = min; v <= max + 1e-9; v += step) {
    ticks.push(Number(v.toFixed(4)))
  }
  return ticks
}

function buildSweepRange(start, end, step) {
  if (step <= 0 || end < start) return []
  const values = []
  for (let v = start; v <= end + 1e-9; v += step) {
    values.push(Number(v.toFixed(1)))
  }
  return values
}

function clamp(value, min, max) {
  return Math.min(max, Math.max(min, value))
}

function nearestTick(value, ticks, step) {
  if (value === null || value === undefined || !ticks.length) return null
  let best = ticks[0]
  let bestDiff = Math.abs(value - best)
  for (const t of ticks.slice(1)) {
    const diff = Math.abs(value - t)
    if (diff < bestDiff) {
      bestDiff = diff
      best = t
    }
  }
  const tolerance = step > 0 ? step / 2 + 1e-6 : 0.0001
  if (bestDiff > tolerance) return null
  return best
}

function uniqueSorted(values = []) {
  return Array.from(new Set(values.filter((v) => v !== null && v !== undefined)))
    .map((v) => Number(v))
    .sort((a, b) => a - b)
}

function LightboxModal({ item, src, onClose, onPrev, onNext }) {
  const containerRef = useRef(null)
  const imgRef = useRef(null)
  const [zoom, setZoom] = useState(1)
  const [baseScale, setBaseScale] = useState(1)
  const [pan, setPan] = useState({ x: 0, y: 0 })
  const [naturalSize, setNaturalSize] = useState({ w: 0, h: 0 })
  const [loadError, setLoadError] = useState('')
  const dragState = useRef({ active: false, startX: 0, startY: 0, panX: 0, panY: 0 })

  const clampPan = useCallback(
    (px, py, scaleFactor) => {
      if (!containerRef.current || !naturalSize.w || !naturalSize.h) return { x: px, y: py }
      const rect = containerRef.current.getBoundingClientRect()
      const scaledW = naturalSize.w * scaleFactor
      const scaledH = naturalSize.h * scaleFactor
      const margin = 32

      const computeBounds = (containerLength, scaledLength, naturalLength) => {
        if (scaledLength <= containerLength) {
          const center = (containerLength - scaledLength) / (2 * scaleFactor)
          return { min: center, max: center }
        }
        const max = margin / scaleFactor
        const min = containerLength / scaleFactor - naturalLength - margin / scaleFactor
        return { min, max }
      }

      const xBounds = computeBounds(rect.width, scaledW, naturalSize.w)
      const yBounds = computeBounds(rect.height, scaledH, naturalSize.h)
      return {
        x: clamp(px, xBounds.min, xBounds.max),
        y: clamp(py, yBounds.min, yBounds.max),
      }
    },
    [naturalSize.h, naturalSize.w],
  )

  const fitImage = useCallback(() => {
    if (!containerRef.current || !imgRef.current || !naturalSize.w || !naturalSize.h) return
    const rect = containerRef.current.getBoundingClientRect()
    const fit = Math.min(rect.width / naturalSize.w, rect.height / naturalSize.h, 1)
    setBaseScale(fit)
    const centered = {
      x: (rect.width - naturalSize.w * fit) / (2 * fit),
      y: (rect.height - naturalSize.h * fit) / (2 * fit),
    }
    setPan(centered)
    setZoom(1)
  }, [naturalSize.h, naturalSize.w])

  useEffect(() => {
    if (!item) return undefined
    const original = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = original
    }
  }, [item])

  useEffect(() => {
    setZoom(1)
    setPan({ x: 0, y: 0 })
    setLoadError('')
  }, [src])

  useEffect(() => {
    if (!containerRef.current) return undefined
    const observer = new ResizeObserver(() => fitImage())
    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [fitImage])

  const applyZoom = (nextZoom, center) => {
    const minZoom = 1
    const maxZoom = 6
    const clampedZoom = clamp(nextZoom, minZoom, maxZoom)
    if (!imgRef.current || !containerRef.current) {
      setZoom(clampedZoom)
      return
    }
    const rect = imgRef.current.getBoundingClientRect()
    const oldScale = baseScale * zoom
    const newScale = baseScale * clampedZoom
    const cx = center ? center.x : rect.width / 2
    const cy = center ? center.y : rect.height / 2
    const nextPanX = pan.x + cx * (1 / newScale - 1 / oldScale)
    const nextPanY = pan.y + cy * (1 / newScale - 1 / oldScale)
    const clampedPan = clampPan(nextPanX, nextPanY, newScale)
    setPan(clampedPan)
    setZoom(clampedZoom)
  }

  const handleWheel = (e) => {
    e.preventDefault()
    const delta = -e.deltaY * 0.0015
    applyZoom(zoom * (1 + delta), { x: e.clientX - (imgRef.current?.getBoundingClientRect().left || 0), y: e.clientY - (imgRef.current?.getBoundingClientRect().top || 0) })
  }

  const handleDoubleClick = (e) => {
    e.preventDefault()
    const targetZoom = zoom > 1.05 ? 1 : 2.2
    applyZoom(targetZoom, { x: e.clientX - (imgRef.current?.getBoundingClientRect().left || 0), y: e.clientY - (imgRef.current?.getBoundingClientRect().top || 0) })
  }

  const endDrag = () => {
    dragState.current.active = false
  }

  const handlePointerDown = (e) => {
    if (!imgRef.current) return
    e.preventDefault()
    imgRef.current.setPointerCapture(e.pointerId)
    dragState.current = {
      active: true,
      startX: e.clientX,
      startY: e.clientY,
      panX: pan.x,
      panY: pan.y,
    }
  }

  const handlePointerMove = (e) => {
    if (!dragState.current.active) return
    const scaleFactor = baseScale * zoom
    const dx = (e.clientX - dragState.current.startX) / scaleFactor
    const dy = (e.clientY - dragState.current.startY) / scaleFactor
    const nextX = dragState.current.panX + dx
    const nextY = dragState.current.panY + dy
    setPan(clampPan(nextX, nextY, scaleFactor))
  }

  const handleKey = useCallback(
    (e) => {
      if (!item) return
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose?.()
      }
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        onPrev?.()
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        onNext?.()
      }
    },
    [item, onClose, onNext, onPrev],
  )

  useEffect(() => {
    window.addEventListener('keydown', handleKey)
    return () => window.removeEventListener('keydown', handleKey)
  }, [handleKey])

  if (!item) return null

  return (
    <div className="lightbox-backdrop" onClick={onClose}>
      <div className="lightbox-shell" onClick={(e) => e.stopPropagation()}>
        <div className="lightbox-header">
          <div className="caption">
            <div className="caption-main">{item.filename || item.relpath || 'Image'}</div>
            {item.relpath ? <div className="caption-sub">{item.relpath}</div> : null}
          </div>
          <div className="lightbox-actions">
            <button className="ghost" onClick={() => applyZoom(zoom * 1.15)} aria-label="Zoom in">+</button>
            <button className="ghost" onClick={() => applyZoom(zoom / 1.15)} aria-label="Zoom out">−</button>
            <button className="ghost" onClick={() => applyZoom(1)} aria-label="Reset zoom">Reset</button>
            <button className="ghost" onClick={onClose} aria-label="Close">×</button>
          </div>
        </div>
        <div
          className="lightbox-viewport"
          ref={containerRef}
          onWheel={handleWheel}
          onPointerDown={handlePointerDown}
          onPointerMove={handlePointerMove}
          onPointerUp={endDrag}
          onPointerCancel={endDrag}
          onDoubleClick={handleDoubleClick}
        >
          <div
            className="lightbox-stage"
            style={{ transform: `translate(${pan.x}px, ${pan.y}px) scale(${baseScale * zoom})` }}
          >
            <img
              ref={imgRef}
              src={src}
              alt={item.filename || 'selected'}
              draggable={false}
              onError={(e) => {
                console.error('Lightbox image failed', e?.target?.src)
                setLoadError('Failed to load image')
              }}
              onLoad={(e) => {
                const naturalW = e.target.naturalWidth || 1
                const naturalH = e.target.naturalHeight || 1
                setNaturalSize({ w: naturalW, h: naturalH })
                fitImage()
              }}
            />
            {loadError ? <div className="lightbox-error">{loadError}</div> : null}
          </div>
        </div>
        <div className="lightbox-footer">
          <div className="subtle">Scroll to zoom, drag to pan, double-click to toggle zoom.</div>
          <div className="lightbox-nav">
            <button className="ghost" onClick={onPrev} aria-label="Previous">← Prev</button>
            <button className="ghost" onClick={onNext} aria-label="Next">Next →</button>
          </div>
        </div>
      </div>
    </div>
  )
}

function GlassSettings({ settings, setSettings }) {
  useEffect(() => {
    applyGlassVars(settings)
  }, [settings])

  const snippet = useMemo(() => buildCssSnippet(settings), [settings])

  const update = (key) => (e) => {
    const value = Number(e.target.value)
    setSettings((s) => ({ ...s, [key]: value }))
  }

  const copyCss = async () => {
    try {
      await navigator.clipboard.writeText(snippet)
    } catch (err) {
      console.error('Copy failed', err)
    }
  }

  return (
    <div className="glass-card settings-panel">
      <div className="panel-header">Glass Settings</div>
      <div className="settings-grid">
        <label>Blur (px)
          <input type="range" min="0" max="40" step="1" value={settings.blur} onChange={update('blur')} />
          <span className="value">{settings.blur}px</span>
        </label>
        <label>Glass Alpha
          <input type="range" min="0" max="0.5" step="0.01" value={settings.alpha} onChange={update('alpha')} />
          <span className="value">{settings.alpha}</span>
        </label>
        <label>Border Alpha
          <input type="range" min="0" max="0.6" step="0.01" value={settings.borderAlpha} onChange={update('borderAlpha')} />
          <span className="value">{settings.borderAlpha}</span>
        </label>
        <label>Saturation (%)
          <input type="range" min="80" max="220" step="5" value={settings.saturation} onChange={update('saturation')} />
          <span className="value">{settings.saturation}%</span>
        </label>
        <label>Shadow Depth
          <input type="range" min="0" max="1" step="0.01" value={settings.depth} onChange={update('depth')} />
          <span className="value">{settings.depth}</span>
        </label>
        <label>Inset Highlight
          <input type="range" min="0" max="2" step="0.05" value={settings.inset} onChange={update('inset')} />
          <span className="value">{settings.inset}</span>
        </label>
      </div>
      <div className="code-block">
        <div className="panel-subheader">Generated CSS</div>
        <textarea readOnly value={snippet} />
        <button className="ghost" onClick={copyCss}>Copy CSS</button>
      </div>
    </div>
  )
}

function GeneratorPanel({ onGenerated }) {
  const [tokenStatus, setTokenStatus] = useState('No token set')
  const [tokenInput, setTokenInput] = useState('')
  const [basePrompt, setBasePrompt] = useState('1girl, solo, best quality, masterpiece')
  const [char1, setChar1] = useState('')
  const [char2, setChar2] = useState('')
  const [negativePrompt, setNegativePrompt] = useState('')
  const [guidance, setGuidance] = useState(4.0)
  const [rescale, setRescale] = useState(0.3)
  const [width, setWidth] = useState(832)
  const [height, setHeight] = useState(1216)
  const [seed, setSeed] = useState(1234567890)
  const [modelName, setModelName] = useState('nai-diffusion-4-5-full')
  const [project, setProject] = useState('default')
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [preview, setPreview] = useState(null)
  const [mode, setMode] = useState('single')
  const [gStart, setGStart] = useState(4.0)
  const [gEnd, setGEnd] = useState(4.5)
  const [gStep, setGStep] = useState(0.1)
  const [rStart, setRStart] = useState(0.0)
  const [rEnd, setREnd] = useState(0.7)
  const [rStep, setRStep] = useState(0.1)
  const [jobInfo, setJobInfo] = useState({ jobId: null, total: 0, done: 0, status: '', current_g: null, current_r: null })
  const pollRef = useRef(null)
  const formSaveRef = useRef(null)
  const restoredRef = useRef(false)

  useEffect(() => {
    if (restoredRef.current) return
    restoredRef.current = true
    try {
      const raw = window.localStorage.getItem(FORM_STORAGE_KEY)
      if (raw) {
        const saved = JSON.parse(raw)
        if (saved.basePrompt !== undefined) setBasePrompt(saved.basePrompt)
        if (saved.char1 !== undefined) setChar1(saved.char1)
        if (saved.char2 !== undefined) setChar2(saved.char2)
        if (saved.negativePrompt !== undefined) setNegativePrompt(saved.negativePrompt)
        if (saved.guidance !== undefined) setGuidance(saved.guidance)
        if (saved.rescale !== undefined) setRescale(saved.rescale)
        if (saved.width !== undefined) setWidth(saved.width)
        if (saved.height !== undefined) setHeight(saved.height)
        if (saved.seed !== undefined) setSeed(saved.seed)
        if (saved.modelName !== undefined) setModelName(saved.modelName)
        if (saved.project !== undefined) setProject(saved.project)
        if (saved.mode !== undefined) setMode(saved.mode)
        if (saved.gStart !== undefined) setGStart(saved.gStart)
        if (saved.gEnd !== undefined) setGEnd(saved.gEnd)
        if (saved.gStep !== undefined) setGStep(saved.gStep)
        if (saved.rStart !== undefined) setRStart(saved.rStart)
        if (saved.rEnd !== undefined) setREnd(saved.rEnd)
        if (saved.rStep !== undefined) setRStep(saved.rStep)
      }
    } catch (err) {
      /* ignore restore errors */
    }
  }, [])

  useEffect(() => {
    if (formSaveRef.current) clearTimeout(formSaveRef.current)
    formSaveRef.current = setTimeout(() => {
      const payload = {
        basePrompt,
        char1,
        char2,
        negativePrompt,
        guidance,
        rescale,
        width,
        height,
        seed,
        modelName,
        project,
        mode,
        gStart,
        gEnd,
        gStep,
        rStart,
        rEnd,
        rStep,
      }
      try {
        window.localStorage.setItem(FORM_STORAGE_KEY, JSON.stringify(payload))
      } catch (err) {
        /* ignore storage errors */
      }
    }, 250)
    return () => {
      if (formSaveRef.current) clearTimeout(formSaveRef.current)
    }
  }, [basePrompt, char1, char2, negativePrompt, guidance, rescale, width, height, seed, modelName, project, mode, gStart, gEnd, gStep, rStart, rEnd, rStep])

  const gValues = useMemo(() => buildSweepRange(Number(gStart), Number(gEnd), Number(gStep)), [gStart, gEnd, gStep])
  const rValues = useMemo(() => buildSweepRange(Number(rStart), Number(rEnd), Number(rStep)), [rStart, rEnd, rStep])
  const totalSweep = gValues.length * rValues.length

  const setToken = async () => {
    if (!tokenInput.trim()) return
    await fetch(`${API_BASE}/api/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: tokenInput }),
    })
    setTokenStatus('Token stored (in-memory)')
  }

  const clearPoll = () => {
    if (pollRef.current) {
      clearTimeout(pollRef.current)
      pollRef.current = null
    }
  }

  const doGenerate = async () => {
    setLoading(true)
    setStatus('Generating...')
    try {
      const res = await fetch(`${API_BASE}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_name: modelName,
          base_prompt: basePrompt,
          char1,
          char2,
          negative_prompt: negativePrompt,
          guidance: Number(guidance),
          rescale: Number(rescale),
          width: Number(width),
          height: Number(height),
          seed: Number(seed),
          project,
        }),
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg)
      }
      const data = await res.json()
      const imageUrl = `${API_BASE}${data.image_url}`
      setPreview(imageUrl)
      onGenerated?.(data)
      setStatus('Generated')
    } catch (err) {
      setStatus('Error generating')
    } finally {
      setLoading(false)
    }
  }

  const pollJob = useCallback(
    async (jobId) => {
      try {
        const res = await fetch(`${API_BASE}/api/jobs/${jobId}`)
        if (!res.ok) {
          setStatus('Job not found')
          clearPoll()
          return
        }
        const data = await res.json()
        setJobInfo((info) => ({ ...info, ...data, jobId, started_at: info.started_at || Date.now() }))
        setStatus(`${data.status} ${data.done}/${data.total}`)
        if (data.status === 'done' || data.status === 'error' || data.status === 'cancelled') {
          setLoading(false)
          clearPoll()
        } else {
          pollRef.current = setTimeout(() => pollJob(jobId), 1000)
        }
      } catch (err) {
        setStatus('Job polling failed')
        clearPoll()
      }
    },
    [],
  )

  useEffect(() => {
    try {
      const raw = window.localStorage.getItem(JOB_STORAGE_KEY)
      if (raw) {
        const saved = JSON.parse(raw)
        if (saved?.jobId) {
          setMode('sweep')
          setJobInfo(saved)
          setStatus('Reattaching job...')
          setLoading(true)
          pollJob(saved.jobId)
        }
      }
    } catch (err) {
      /* ignore */
    }
  }, [pollJob])

  useEffect(() => {
    if (!jobInfo?.jobId) {
      window.localStorage.removeItem(JOB_STORAGE_KEY)
      return
    }
    const terminal = jobInfo.status === 'done' || jobInfo.status === 'error' || jobInfo.status === 'cancelled'
    if (terminal) {
      window.localStorage.removeItem(JOB_STORAGE_KEY)
      return
    }
    try {
      window.localStorage.setItem(
        JOB_STORAGE_KEY,
        JSON.stringify({ ...jobInfo, started_at: jobInfo.started_at || Date.now() }),
      )
    } catch (err) {
      /* ignore */
    }
  }, [jobInfo])

  const startSweep = async () => {
    if (totalSweep === 0) {
      setStatus('No sweep values')
      return
    }
    if (totalSweep > MAX_SWEEP_IMAGES) {
      setStatus(`Too many images (${totalSweep}) - cap is ${MAX_SWEEP_IMAGES}`)
      return
    }
    setLoading(true)
    setStatus('Starting sweep...')
    try {
      const res = await fetch(`${API_BASE}/api/generate_sweep`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          model_name: modelName,
          base_prompt: basePrompt,
          char1,
          char2,
          negative_prompt: negativePrompt,
          guidance: { start: Number(gStart), end: Number(gEnd), step: Number(gStep) },
          rescale: { start: Number(rStart), end: Number(rEnd), step: Number(rStep) },
          width: Number(width),
          height: Number(height),
          seed: Number(seed),
          project,
        }),
      })
      if (!res.ok) {
        const msg = await res.text()
        throw new Error(msg)
      }
      const data = await res.json()
      setJobInfo({
        jobId: data.job_id,
        total: data.total,
        done: 0,
        status: 'queued',
        current_g: null,
        current_r: null,
        started_at: Date.now(),
      })
      pollJob(data.job_id)
    } catch (err) {
      setStatus('Error starting sweep')
      setLoading(false)
    }
  }

  useEffect(() => {
    return () => clearPoll()
  }, [])

  return (
    <div className="glass-card">
      <div className="panel-header">Generator</div>
      <div className="grid-two">
        <div>
          <label>API Token
            <input type="password" value={tokenInput} onChange={(e) => setTokenInput(e.target.value)} placeholder="Enter NovelAI token" />
          </label>
          <button onClick={setToken}>Set Token</button>
          <div className="subtle">{tokenStatus}</div>
          <label>Project
            <input value={project} onChange={(e) => setProject(e.target.value)} />
          </label>
          <label>Model
            <input value={modelName} onChange={(e) => setModelName(e.target.value)} />
          </label>
          <label>Base Prompt
            <textarea rows="2" value={basePrompt} onChange={(e) => setBasePrompt(e.target.value)} />
          </label>
          <label>Char 1
            <textarea
              className="prompt-textarea"
              rows="2"
              value={char1}
              onChange={(e) => setChar1(e.target.value)}
            />
          </label>
          <label>Char 2
            <textarea
              className="prompt-textarea"
              rows="2"
              value={char2}
              onChange={(e) => setChar2(e.target.value)}
            />
          </label>
          <label>Negative Prompt
            <textarea rows="2" value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} />
          </label>
        </div>
        <div>
          <div className="mode-toggle">
            <button className={mode === 'single' ? 'active' : ''} onClick={() => setMode('single')}>Single</button>
            <button className={mode === 'sweep' ? 'active' : ''} onClick={() => setMode('sweep')}>Sweep</button>
          </div>
          {mode === 'single' ? (
            <div className="dual">
              <label>Guidance
                <input type="number" value={guidance} step="0.1" onChange={(e) => setGuidance(e.target.value)} />
              </label>
              <label>Rescale
                <input type="number" value={rescale} step="0.1" onChange={(e) => setRescale(e.target.value)} />
              </label>
            </div>
          ) : (
            <div className="sweep-grid">
              <div className="panel-subheader">Guidance Sweep</div>
              <div className="dual">
                <label>Start
                  <input type="number" value={gStart} step="0.1" onChange={(e) => setGStart(e.target.value)} />
                </label>
                <label>End
                  <input type="number" value={gEnd} step="0.1" onChange={(e) => setGEnd(e.target.value)} />
                </label>
              </div>
              <label>Step
                <input type="number" value={gStep} step="0.1" onChange={(e) => setGStep(e.target.value)} />
              </label>
              <div className="panel-subheader">Rescale Sweep</div>
              <div className="dual">
                <label>Start
                  <input type="number" value={rStart} step="0.1" onChange={(e) => setRStart(e.target.value)} />
                </label>
                <label>End
                  <input type="number" value={rEnd} step="0.1" onChange={(e) => setREnd(e.target.value)} />
                </label>
              </div>
              <label>Step
                <input type="number" value={rStep} step="0.1" onChange={(e) => setRStep(e.target.value)} />
              </label>
              <div className="counts subtle">G values: {gValues.length} | R values: {rValues.length} | Total: {totalSweep}</div>
              {totalSweep > MAX_SWEEP_IMAGES && (
                <div className="warning">Cap {MAX_SWEEP_IMAGES} images. Adjust ranges.</div>
              )}
            </div>
          )}
          <div className="dual">
            <label>Width
              <input type="number" value={width} onChange={(e) => setWidth(e.target.value)} />
            </label>
            <label>Height
              <input type="number" value={height} onChange={(e) => setHeight(e.target.value)} />
            </label>
          </div>
          <label>Seed
            <input type="number" value={seed} onChange={(e) => setSeed(e.target.value)} />
          </label>
          {mode === 'single' ? (
            <button onClick={doGenerate} disabled={loading}>{loading ? 'Working...' : 'Generate'}</button>
          ) : (
            <div className="sweep-actions">
              <button onClick={startSweep} disabled={loading || totalSweep === 0 || totalSweep > MAX_SWEEP_IMAGES}>
                {loading ? 'Working...' : 'Start Sweep'}
              </button>
              {jobInfo?.jobId && (
                <button
                  className="ghost"
                  onClick={async () => {
                    await fetch(`${API_BASE}/api/jobs/${jobInfo.jobId}/cancel`, { method: 'POST' })
                    setStatus('Cancelled')
                    setLoading(false)
                    setJobInfo((info) => ({ ...info, status: 'cancelled' }))
                  }}
                >
                  Cancel
                </button>
              )}
            </div>
          )}
          {jobInfo?.jobId && (
            <div className="progress-block">
              <div className="progress-bar">
                <div className="fill" style={{ width: `${jobInfo.total ? Math.round((jobInfo.done / jobInfo.total) * 100) : 0}%` }} />
              </div>
              <div className="subtle">Job: {jobInfo.jobId}</div>
              <div className="subtle">{status}</div>
              {jobInfo.current_g !== null && jobInfo.current_r !== null && (
                <div className="subtle">Current G {formatTick(jobInfo.current_g)} / R {formatTick(jobInfo.current_r)}</div>
              )}
            </div>
          )}
          <div className="status">{status}</div>
          {preview && (
            <div className="preview">
              <div className="panel-subheader">Preview</div>
              <img src={preview} alt="Latest" />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

function ArchiveViewer() {
  const loadLayoutDefaults = () => {
    const fallback = { split: 65, gridFirst: true, selColor: '#7ec8ff' }
    if (typeof window === 'undefined') return fallback
    try {
      const raw = window.localStorage.getItem('archiveLayoutDefaults')
      if (raw) return { ...fallback, ...JSON.parse(raw) }
    } catch (err) {
      /* ignore */
    }
    return fallback
  }

  const [projects, setProjects] = useState([])
  const [project, setProject] = useState('')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState('grid')
  const [matrix, setMatrix] = useState(defaultMatrix)
  const [yHeaderWidth, setYHeaderWidth] = useState(84)
  const [activeCoords, setActiveCoords] = useState({ x: null, y: null })
  const [layout, setLayout] = useState(loadLayoutDefaults)
  const layoutDefaults = useRef(loadLayoutDefaults())
  const [lightboxOpen, setLightboxOpen] = useState(false)
  const pageSize = 200
  const matrixWrapperRef = useRef(null)
  const splitRef = useRef(null)
  const dragState = useRef({ active: false, startX: 0, startSplit: 60 })

  useEffect(() => {
    document.documentElement.style.setProperty('--sel-color', layout.selColor || '#7ec8ff')
  }, [layout.selColor])

  useEffect(() => {
    const loadProjects = async () => {
      try {
        const res = await fetch(`${API_BASE}/api/projects`)
        if (!res.ok) return
        const data = await res.json()
        setProjects(data.projects || [])
      } catch (err) {
        /* ignore */
      }
    }
    loadProjects()
  }, [])

  const fetchArchives = useCallback(
    async (signal) => {
      setLoading(true)
      try {
        let currentPage = 1
        let aggregated = []
        let expectedTotal = 0
        const seen = new Set()
        while (true) {
          const params = new URLSearchParams({ page: String(currentPage), page_size: String(pageSize) })
          if (project.trim()) params.append('project', project.trim())
          if (search.trim()) params.append('q', search.trim())
          const res = await fetch(`${API_BASE}/api/archives?${params.toString()}`, { signal })
          if (!res.ok) break
          const data = await res.json()
          const batch = data.items || []
          batch.forEach((item) => {
            if (!seen.has(item.id)) {
              seen.add(item.id)
              aggregated.push(item)
            }
          })
          expectedTotal = data.total ?? aggregated.length
          if (!batch.length || aggregated.length >= expectedTotal) {
            break
          }
          currentPage += 1
        }
        setItems(aggregated)
        setTotal(expectedTotal)
        setSelectedId(aggregated.length ? aggregated[0].id : null)
      } catch (err) {
        if (err.name !== 'AbortError') {
          console.error('Archive fetch failed', err)
        }
      } finally {
        setLoading(false)
      }
    },
    [pageSize, project, search],
  )

  useEffect(() => {
    const controller = new AbortController()
    fetchArchives(controller.signal)
    return () => controller.abort()
  }, [fetchArchives])

  const parsedItems = useMemo(
    () =>
      items.map((item) => ({
        ...item,
        params: parseParamsFromName(item.filename || item.relpath || ''),
      })),
    [items],
  )

  const thumbSrc = (item) => {
    if (item?.relpath) return `${API_BASE}/api/thumb_path/${encodeRelpath(item.relpath)}`
    if (item?.thumb_url) return `${API_BASE}${item.thumb_url}`
    return ''
  }

  const imageSrc = (item) => {
    if (item?.relpath) return `${API_BASE}/api/raw_path/${encodeRelpath(item.relpath)}`
    if (item?.image_url) return `${API_BASE}${item.image_url}`
    return ''
  }

  const GalleryThumb = ({ item, active, onSelect, className = '' }) => (
    <button
      className={`thumb ${active ? 'active' : ''} ${className}`.trim()}
      onClick={() => onSelect?.()}
    >
      <img src={thumbSrc(item)} alt={item.id} loading="lazy" />
    </button>
  )

  const xParamKey = matrix.xParam === 'G' ? 'g' : 'r'
  const yParamKey = matrix.yParam === 'R' ? 'r' : 'g'

  const normalizeTick = (value) => {
    if (value === null || value === undefined || Number.isNaN(value)) return null
    return Number(Number(value).toFixed(1))
  }

  const xTicks = useMemo(() => {
    if (matrix.autoX) {
      return uniqueSorted(parsedItems.map((i) => normalizeTick(i.params?.[xParamKey]))).map((v) => Number(v.toFixed(1)))
    }
    return buildTicks(matrix.xMin, matrix.xMax, matrix.xStep)
  }, [matrix.autoX, matrix.xMax, matrix.xMin, matrix.xStep, parsedItems, xParamKey])

  const yTicks = useMemo(() => {
    if (matrix.autoY) {
      return uniqueSorted(parsedItems.map((i) => normalizeTick(i.params?.[yParamKey]))).map((v) => Number(v.toFixed(1)))
    }
    return buildTicks(matrix.yMin, matrix.yMax, matrix.yStep)
  }, [matrix.autoY, matrix.yMax, matrix.yMin, matrix.yStep, parsedItems, yParamKey])

  const inferStep = (ticks, fallback) => {
    if (!ticks || ticks.length < 2) return fallback
    let minDiff = Infinity
    for (let i = 1; i < ticks.length; i += 1) {
      minDiff = Math.min(minDiff, Math.abs(ticks[i] - ticks[i - 1]))
    }
    return minDiff !== Infinity ? minDiff : fallback
  }

  const effXStep = matrix.autoX ? inferStep(xTicks, matrix.xStep) : matrix.xStep
  const effYStep = matrix.autoY ? inferStep(yTicks, matrix.yStep) : matrix.yStep

  const { matrixCells, orderedMatrixItems, idToCoords } = useMemo(() => {
    const mapping = new Map()
    parsedItems.forEach((item) => {
      const xVal = nearestTick(item.params?.[xParamKey], xTicks, effXStep)
      const yVal = nearestTick(item.params?.[yParamKey], yTicks, effYStep)
      if (xVal === null || yVal === null) return
      const key = `${yVal}|${xVal}`
      if (!mapping.has(key)) mapping.set(key, item)
    })

    const cells = []
    const order = []
    const coordMap = new Map()
    yTicks.forEach((yVal) => {
      xTicks.forEach((xVal) => {
        const key = `${yVal}|${xVal}`
        const item = mapping.get(key) || null
        cells.push({ key, xVal, yVal, item })
        if (item) {
          order.push(item)
          coordMap.set(item.id, { x: xVal, y: yVal })
        }
      })
    })

    return { matrixCells: cells, orderedMatrixItems: order, idToCoords: coordMap }
  }, [parsedItems, xParamKey, xTicks, yParamKey, yTicks, matrix.xStep, matrix.yStep, effXStep, effYStep])

  const displayOrder = viewMode === 'matrix' ? orderedMatrixItems : items
  const selectedItem = displayOrder.find((i) => i.id === selectedId) || displayOrder[0] || null
  const selectedSrc = selectedItem ? imageSrc(selectedItem) : ''

  const changeSelection = (delta) => {
    if (!displayOrder.length) return
    setSelectedId((current) => {
      const idx = displayOrder.findIndex((i) => i.id === current)
      const nextIdx = idx >= 0 ? (idx + delta + displayOrder.length) % displayOrder.length : delta > 0 ? 0 : displayOrder.length - 1
      return displayOrder[nextIdx].id
    })
  }

  useEffect(() => {
    if (selectedItem && idToCoords.has(selectedItem.id)) {
      setActiveCoords(idToCoords.get(selectedItem.id))
    }
  }, [idToCoords, selectedItem])

  useEffect(() => {
    const el = matrixWrapperRef.current
    if (!el) return undefined

    const measure = () => {
      const header = el.querySelector('.matrix-header.y-header')
      const yHeader = header ? header.getBoundingClientRect().width : 88
      const clamped = Math.max(72, Math.min(96, Math.round(yHeader)))
      setYHeaderWidth(clamped)
    }

    measure()
    const observer = new ResizeObserver(measure)
    observer.observe(el)
    return () => observer.disconnect()
  }, [xTicks.length])

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowLeft') {
        e.preventDefault()
        changeSelection(-1)
      }
      if (e.key === 'ArrowRight') {
        e.preventDefault()
        changeSelection(1)
      }
    }
    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  })

  const updateMatrix = (key, value) => setMatrix((m) => ({ ...m, [key]: value }))
  const handleColorChange = (e) => {
    const value = e.target.value
    setLayout((l) => ({ ...l, selColor: value }))
  }
  const swapPanels = () => setLayout((l) => ({ ...l, gridFirst: !l.gridFirst }))
  const resetLayout = () => setLayout(layoutDefaults.current)
  const saveDefaults = () => {
    layoutDefaults.current = layout
    try {
      window.localStorage.setItem('archiveLayoutDefaults', JSON.stringify(layout))
    } catch (err) {
      /* ignore */
    }
  }
  const clampSplit = (v) => Math.min(80, Math.max(20, v))
  const onMove = useCallback(
    (e) => {
      if (!dragState.current.active || !splitRef.current) return
      const width = splitRef.current.clientWidth || 1
      const delta = ((e.clientX - dragState.current.startX) / width) * 100
      const signed = layout.gridFirst ? delta : -delta
      const next = clampSplit(dragState.current.startSplit + signed)
      setLayout((l) => ({ ...l, split: next }))
    },
    [layout.gridFirst],
  )
  const stopDrag = useCallback(() => {
    dragState.current.active = false
    window.removeEventListener('mousemove', onMove)
    window.removeEventListener('mouseup', stopDrag)
  }, [onMove])
  const startDrag = (e) => {
    dragState.current = { active: true, startX: e.clientX, startSplit: layout.split }
    window.addEventListener('mousemove', onMove)
    window.addEventListener('mouseup', stopDrag)
  }
  useEffect(() => () => stopDrag(), [stopDrag])

  const matrixReadout = (
    <div className="subtle">
      Auto ticks: X {xTicks.length} values ({xTicks[0] ?? '–'} … {xTicks[xTicks.length - 1] ?? '–'}), Y {yTicks.length} values ({
        yTicks[0] ?? '–'
      } … {yTicks[yTicks.length - 1] ?? '–'}).
    </div>
  )

  const gridPanel = (
    <div className="archive-panel" style={{ flexBasis: layout.gridFirst ? 'var(--split)' : `calc(100% - var(--split))` }}>
      <div className="panel-body">
        <div className="viewer-modes">
          <div className="mode-buttons">
            <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')}>
              Gallery
            </button>
            <button className={viewMode === 'matrix' ? 'active' : ''} onClick={() => setViewMode('matrix')}>
              Matrix
            </button>
          </div>
          {viewMode === 'matrix' && (
            <div className="matrix-controls">
              <div className="dual">
                <label>
                  X Axis
                  <select value={matrix.xParam} onChange={(e) => updateMatrix('xParam', e.target.value)}>
                    <option value="R">Rescale (R)</option>
                    <option value="G">Guidance (G)</option>
                  </select>
                </label>
                <label>
                  Y Axis
                  <select value={matrix.yParam} onChange={(e) => updateMatrix('yParam', e.target.value)}>
                    <option value="G">Guidance (G)</option>
                    <option value="R">Rescale (R)</option>
                  </select>
                </label>
              </div>
              <div className="dual">
                <label className="row-align">
                  <input type="checkbox" checked={matrix.autoY} onChange={(e) => updateMatrix('autoY', e.target.checked)} /> Auto Y ticks
                </label>
                <label className="row-align">
                  <input type="checkbox" checked={matrix.autoX} onChange={(e) => updateMatrix('autoX', e.target.checked)} /> Auto X ticks
                </label>
              </div>
              <div className="subtle">Matrix cells built from filename tokens like "--G7.0_R0.7".</div>
              {matrixReadout}
              {activeCoords.x !== null && activeCoords.y !== null && (
                <div className="matrix-badge">Now viewing: {matrix.xParam}={activeCoords.x}, {matrix.yParam}={activeCoords.y}</div>
              )}
            </div>
          )}
        </div>

        {viewMode === 'grid' && (
            <div className="gallery-area">
              <div className="gallery-grid">
                {items.map((item) => (
                  <GalleryThumb
                    key={item.id}
                    item={item}
                    active={item.id === selectedId}
                    onSelect={() => setSelectedId(item.id)}
                  />
                ))}
              </div>
            </div>
          )}

        {viewMode === 'matrix' && (
          <div
            className="matrix-wrapper"
            ref={matrixWrapperRef}
            style={{
              '--yhdr': `${yHeaderWidth}px`,
              '--xcount': xTicks.length,
            }}
          >
            <div className="matrix-scroller">
              <div className="matrix-grid">
                <div className="matrix-corner sticky-corner" />
                {xTicks.map((x) => (
                  <div key={`x-${x}`} className={`matrix-header x-header ${activeCoords.x === x ? 'active-axis' : ''}`}>
                    {formatTick(x)}
                  </div>
                ))}
                {yTicks.map((y) => (
                  <React.Fragment key={`row-${y}`}>
                    <div className={`matrix-header y-header ${activeCoords.y === y ? 'active-axis' : ''}`}>{formatTick(y)}</div>
                    {xTicks.map((x) => {
                      const cell = matrixCells.find((c) => c.xVal === x && c.yVal === y)
                      const isActive = activeCoords.x === x && activeCoords.y === y
                      const sameX = activeCoords.x === x
                      const sameY = activeCoords.y === y
                      const classes = [
                        'matrixCell',
                        isActive ? 'matrixCell--active' : '',
                        sameX ? 'matrixCell--col' : '',
                        sameY ? 'matrixCell--row' : '',
                      ]
                        .filter(Boolean)
                        .join(' ')
                      return (
                        <div key={`${y}-${x}`} className={classes}>
                          {cell?.item ? (
                            <GalleryThumb
                              item={cell.item}
                              active={cell.item.id === selectedId}
                              onSelect={() => {
                                setSelectedId(cell.item.id)
                                setActiveCoords({ x, y })
                              }}
                            />
                          ) : (
                            <div className="matrix-placeholder">—</div>
                          )}
                        </div>
                      )
                    })}
                  </React.Fragment>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>
      <div className="viewer-controls">
        <button onClick={() => changeSelection(-1)}>Prev</button>
        <button onClick={() => changeSelection(1)}>Next</button>
      </div>
      <div className="subtle">{loading ? 'Loading archives…' : `Showing ${items.length} of ${total || items.length}`}</div>
    </div>
  )

  const detailPanel = (
    <div className="archive-panel" style={{ flexBasis: layout.gridFirst ? `calc(100% - var(--split))` : 'var(--split)' }}>
      <div className="panel-body detail-body">
        {selectedItem && (
          <>
            <div className="panel-subheader">{selectedItem.project} — {selectedItem.filename}</div>
            <div className="subtle">{selectedItem.relpath}</div>
            <div className="detail-image-wrap">
              <img
                src={selectedSrc}
                alt={selectedItem.id}
                loading="lazy"
                onClick={() => setLightboxOpen(true)}
                style={{ cursor: 'zoom-in' }}
              />
            </div>
            <textarea
              className="detail-meta"
              readOnly
              value={selectedItem.prompts || 'No metadata available'}
            />
          </>
        )}
      </div>
    </div>
  )

  const panels = layout.gridFirst ? (
    <>
      {gridPanel}
      <div className="splitter" onMouseDown={startDrag} />
      {detailPanel}
    </>
  ) : (
    <>
      {detailPanel}
      <div className="splitter" onMouseDown={startDrag} />
      {gridPanel}
    </>
  )

  return (
    <>
      <div className="glass-card archive-card" ref={splitRef}>
        <div className="panel-header">Archive Viewer</div>
        <div className="archive-toolbar">
          <div className="dual">
            <label>
              Project
              <select value={project} onChange={(e) => setProject(e.target.value)}>
                <option value="">All Projects</option>
                {projects.map((p) => (
                  <option key={p.name} value={p.name}>{`${p.name} (${p.count})`}</option>
                ))}
              </select>
            </label>
            <label>
              Search
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filename contains" />
            </label>
          </div>
          <div className="layout-actions">
            <button className="ghost" onClick={swapPanels}>Swap Panels</button>
            <button className="ghost" onClick={resetLayout}>Reset</button>
            <button className="ghost" onClick={saveDefaults}>Save as Default</button>
            <label className="color-picker">
              Select border
              <input type="color" value={layout.selColor} onChange={handleColorChange} />
            </label>
          </div>
        </div>

        <div className="archive-panels" style={{ '--split': `${layout.split}%` }}>
          {panels}
        </div>
      </div>
      {lightboxOpen && selectedItem ? (
        <LightboxModal
          item={selectedItem}
          src={selectedSrc}
          onClose={() => setLightboxOpen(false)}
          onPrev={() => changeSelection(-1)}
          onNext={() => changeSelection(1)}
        />
      ) : null}
    </>
  )
}

export default function App() {
  const [settings, setSettings] = useState(defaultGlass)
  const [activeTab, setActiveTab] = useState('generator')

  return (
    <div className="app-shell">
      <div className="aurora-layer" />
      <div className="aurora-layer glow" />
      <div className="content">
        <header className="hero">
          <h1>NAI Studio Web</h1>
          <p>FastAPI + React remake with premium dark glassmorphism.</p>
        </header>
        <div className="tab-bar">
          <button className={activeTab === 'generator' ? 'active' : ''} onClick={() => setActiveTab('generator')}>
            Generator
          </button>
          <button className={activeTab === 'archive' ? 'active' : ''} onClick={() => setActiveTab('archive')}>
            Archive
          </button>
        </div>

        <div className={`tab-panel ${activeTab === 'generator' ? 'active' : 'hidden'}`}>
          <div className="top-layout">
            <div className="card-column">
              <GeneratorPanel />
            </div>
            <div className="card-column">
              <GlassSettings settings={settings} setSettings={setSettings} />
            </div>
          </div>
        </div>

        <div className={`tab-panel ${activeTab === 'archive' ? 'active' : 'hidden'}`}>
          <div className="archive-tab">
            <ArchiveViewer />
          </div>
        </div>
      </div>
    </div>
  )
}

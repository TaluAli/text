import React, { useEffect, useMemo, useState } from 'react'

const API_BASE = import.meta.env.VITE_API_BASE || 'http://localhost:8000'

const defaultGlass = {
  blur: 22,
  alpha: 0.32,
  borderAlpha: 0.18,
  saturation: 160,
  depth: 0.7,
  inset: 0.9,
}

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

  const setToken = async () => {
    if (!tokenInput.trim()) return
    await fetch(`${API_BASE}/api/token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token: tokenInput }),
    })
    setTokenStatus('Token stored (in-memory)')
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
            <input value={char1} onChange={(e) => setChar1(e.target.value)} />
          </label>
          <label>Char 2
            <input value={char2} onChange={(e) => setChar2(e.target.value)} />
          </label>
          <label>Negative Prompt
            <textarea rows="2" value={negativePrompt} onChange={(e) => setNegativePrompt(e.target.value)} />
          </label>
        </div>
        <div>
          <div className="dual">
            <label>Guidance
              <input type="number" value={guidance} step="0.1" onChange={(e) => setGuidance(e.target.value)} />
            </label>
            <label>Rescale
              <input type="number" value={rescale} step="0.1" onChange={(e) => setRescale(e.target.value)} />
            </label>
          </div>
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
          <button onClick={doGenerate} disabled={loading}>{loading ? 'Working...' : 'Generate'}</button>
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
  const [project, setProject] = useState('')
  const [items, setItems] = useState([])
  const [page, setPage] = useState(1)
  const [pageSize] = useState(20)
  const [selected, setSelected] = useState(-1)

  const fetchArchives = async () => {
    const params = new URLSearchParams({ page, page_size: pageSize })
    if (project.trim()) params.append('project', project.trim())
    const res = await fetch(`${API_BASE}/api/archives?${params.toString()}`)
    const data = await res.json()
    setItems(data.items || [])
    setSelected(data.items?.length ? 0 : -1)
  }

  useEffect(() => {
    fetchArchives()
  }, [page, project])

  const selectedItem = selected >= 0 ? items[selected] : null

  const changeSelection = (delta) => {
    if (!items.length) return
    setSelected((idx) => {
      if (idx < 0) return 0
      return (idx + delta + items.length) % items.length
    })
  }

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

  return (
    <div className="glass-card">
      <div className="panel-header">Archive Viewer</div>
      <div className="dual">
        <label>Project Filter
          <input value={project} onChange={(e) => { setProject(e.target.value); setPage(1) }} placeholder="Project name" />
        </label>
        <div className="subtle">Use arrows or buttons to navigate</div>
      </div>
      <div className="gallery-grid">
        {items.map((item, idx) => (
          <button
            key={item.id}
            className={`thumb ${idx === selected ? 'active' : ''}`}
            onClick={() => setSelected(idx)}
          >
            <img src={`${API_BASE}${item.thumb_url}`} alt={item.id} />
          </button>
        ))}
      </div>
      <div className="viewer-controls">
        <button onClick={() => changeSelection(-1)}>Prev</button>
        <button onClick={() => changeSelection(1)}>Next</button>
      </div>
      {selectedItem && (
        <div className="detail">
          <div className="panel-subheader">{selectedItem.project} — Seed {selectedItem.seed}</div>
          <img src={`${API_BASE}${selectedItem.image_url}`} alt={selectedItem.id} />
          <div className="subtle">{selectedItem.prompts}</div>
        </div>
      )}
    </div>
  )
}

export default function App() {
  const [settings, setSettings] = useState(defaultGlass)

  return (
    <div className="app-shell">
      <div className="aurora-layer" />
      <div className="aurora-layer glow" />
      <div className="content">
        <header className="hero">
          <h1>NAI Studio Web</h1>
          <p>FastAPI + React remake with premium dark glassmorphism.</p>
        </header>
        <div className="layout">
          <div className="left-column">
            <GeneratorPanel />
            <ArchiveViewer />
          </div>
          <div className="right-column">
            <GlassSettings settings={settings} setSettings={setSettings} />
          </div>
        </div>
      </div>
    </div>
  )
}

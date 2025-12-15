import React, { useCallback, useEffect, useMemo, useState } from 'react'

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
  autoX: false,
  autoY: false,
}

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

function encodeRelpath(relpath = '') {
  return relpath
    .split('/')
    .map((part) => encodeURIComponent(part))
    .join('/')
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
  const [projects, setProjects] = useState([])
  const [project, setProject] = useState('')
  const [search, setSearch] = useState('')
  const [items, setItems] = useState([])
  const [selectedId, setSelectedId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [total, setTotal] = useState(0)
  const [viewMode, setViewMode] = useState('grid')
  const [matrix, setMatrix] = useState(defaultMatrix)
  const pageSize = 200

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

  const fetchArchives = useCallback(async (signal) => {
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
  }, [pageSize, project, search])

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
    [items]
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

  const xParamKey = matrix.xParam === 'G' ? 'g' : 'r'
  const yParamKey = matrix.yParam === 'R' ? 'r' : 'g'

  const xTicks = useMemo(() => {
    if (matrix.autoX) {
      return uniqueSorted(parsedItems.map((i) => i.params?.[xParamKey])).map((v) => Number(v.toFixed(3)))
    }
    return buildTicks(matrix.xMin, matrix.xMax, matrix.xStep)
  }, [matrix.autoX, matrix.xMax, matrix.xMin, matrix.xStep, parsedItems, xParamKey])

  const yTicks = useMemo(() => {
    if (matrix.autoY) {
      return uniqueSorted(parsedItems.map((i) => i.params?.[yParamKey])).map((v) => Number(v.toFixed(3)))
    }
    return buildTicks(matrix.yMin, matrix.yMax, matrix.yStep)
  }, [matrix.autoY, matrix.yMax, matrix.yMin, matrix.yStep, parsedItems, yParamKey])

  const { matrixCells, orderedMatrixItems, idToCoords } = useMemo(() => {
    const mapping = new Map()
    parsedItems.forEach((item) => {
      const xVal = nearestTick(item.params?.[xParamKey], xTicks, matrix.xStep)
      const yVal = nearestTick(item.params?.[yParamKey], yTicks, matrix.yStep)
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
  }, [parsedItems, xParamKey, xTicks, yParamKey, yTicks, matrix.xStep, matrix.yStep])

  const displayOrder = viewMode === 'matrix' ? orderedMatrixItems : items
  const selectedItem = displayOrder.find((i) => i.id === selectedId) || displayOrder[0] || null
  const [activeCoords, setActiveCoords] = useState({ x: null, y: null })

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

  return (
    <div className="glass-card">
      <div className="panel-header">Archive Viewer</div>
      <div className="dual">
        <label>Project
          <select value={project} onChange={(e) => setProject(e.target.value)}>
            <option value="">All Projects</option>
            {projects.map((p) => (
              <option key={p.name} value={p.name}>{`${p.name} (${p.count})`}</option>
            ))}
          </select>
        </label>
        <label>Search
          <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Filename contains" />
        </label>
      </div>

      <div className="viewer-modes">
        <div className="mode-buttons">
          <button className={viewMode === 'grid' ? 'active' : ''} onClick={() => setViewMode('grid')}>Gallery</button>
          <button className={viewMode === 'matrix' ? 'active' : ''} onClick={() => setViewMode('matrix')}>Matrix</button>
        </div>
        {viewMode === 'matrix' && (
          <div className="matrix-controls">
            <div className="dual">
              <label>X Axis
                <select value={matrix.xParam} onChange={(e) => updateMatrix('xParam', e.target.value)}>
                  <option value="R">Rescale (R)</option>
                  <option value="G">Guidance (G)</option>
                </select>
              </label>
              <label>Y Axis
                <select value={matrix.yParam} onChange={(e) => updateMatrix('yParam', e.target.value)}>
                  <option value="G">Guidance (G)</option>
                  <option value="R">Rescale (R)</option>
                </select>
              </label>
            </div>
            <div className="dual">
              <label>Y Min / Max / Step
                <div className="triple">
                  <input type="number" value={matrix.yMin} step="0.1" onChange={(e) => updateMatrix('yMin', Number(e.target.value))} />
                  <input type="number" value={matrix.yMax} step="0.1" onChange={(e) => updateMatrix('yMax', Number(e.target.value))} />
                  <input type="number" value={matrix.yStep} step="0.05" onChange={(e) => updateMatrix('yStep', Number(e.target.value))} />
                </div>
              </label>
              <label>X Min / Max / Step
                <div className="triple">
                  <input type="number" value={matrix.xMin} step="0.1" onChange={(e) => updateMatrix('xMin', Number(e.target.value))} />
                  <input type="number" value={matrix.xMax} step="0.1" onChange={(e) => updateMatrix('xMax', Number(e.target.value))} />
                  <input type="number" value={matrix.xStep} step="0.05" onChange={(e) => updateMatrix('xStep', Number(e.target.value))} />
                </div>
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
              <button
                key={item.id}
                className={`thumb ${item.id === selectedId ? 'active' : ''}`}
                onClick={() => setSelectedId(item.id)}
              >
                <img src={thumbSrc(item)} alt={item.id} loading="lazy" />
              </button>
            ))}
          </div>
        </div>
      )}

      {viewMode === 'matrix' && (
        <div className="matrix-wrapper">
          <div className="matrix-scroller">
            <div className="matrix-grid" style={{ gridTemplateColumns: `auto repeat(${xTicks.length}, 140px)` }}>
              <div className="matrix-corner sticky-corner" />
              {xTicks.map((x) => (
                <div
                  key={`x-${x}`}
                  className={`matrix-header x-header ${activeCoords.x === x ? 'active-axis' : ''}`}
                >
                  {x}
                </div>
              ))}
              {yTicks.map((y) => (
                <React.Fragment key={`row-${y}`}>
                  <div className={`matrix-header y-header ${activeCoords.y === y ? 'active-axis' : ''}`}>{y}</div>
                  {xTicks.map((x) => {
                    const cell = matrixCells.find((c) => c.xVal === x && c.yVal === y)
                    const isActive = activeCoords.x === x && activeCoords.y === y
                    const sameX = activeCoords.x === x
                    const sameY = activeCoords.y === y
                    return (
                      <div
                        key={`${y}-${x}`}
                        className={`matrix-cell ${isActive ? 'active-cell' : ''} ${sameX ? 'axis-x' : ''} ${sameY ? 'axis-y' : ''}`}
                      >
                        {cell?.item ? (
                          <button
                            className={`thumb ${cell.item.id === selectedId ? 'active' : ''}`}
                            onClick={() => {
                              setSelectedId(cell.item.id)
                              setActiveCoords({ x, y })
                            }}
                          >
                            <img src={thumbSrc(cell.item)} alt={cell.item.id} loading="lazy" />
                          </button>
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

      <div className="subtle">{loading ? 'Loading archives…' : `Showing ${items.length} of ${total || items.length}`}</div>
      <div className="viewer-controls">
        <button onClick={() => changeSelection(-1)}>Prev</button>
        <button onClick={() => changeSelection(1)}>Next</button>
      </div>
      {selectedItem && (
        <div className="detail">
          <div className="panel-subheader">{selectedItem.project} — {selectedItem.filename}</div>
          <div className="subtle">{selectedItem.relpath}</div>
          <img src={imageSrc(selectedItem)} alt={selectedItem.id} loading="lazy" />
          <div className="subtle">{selectedItem.prompts || 'No metadata available'}</div>
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

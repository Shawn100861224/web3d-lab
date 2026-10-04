import { useEffect, useState } from 'react'
import MetricsPanel from './components/MetricsPanel'
import SplatViewer, { type ViewerStats } from './components/SplatViewer'
import { ApiError, fetchScene, type Scene } from './lib/api'

const DEFAULT_SLUG = 'robot-head'

const EMPTY_STATS: ViewerStats = {
  status: 'loading',
  progress: 0,
  numSplats: 0,
  fps: 0,
  loadMs: 0,
  bytes: 0,
  camera: [0, 0, 0],
  extent: 0,
  bbox: [0, 0, 0, 0, 0, 0],
  error: null,
}

/**
 * 模块 3 的查看器页。路由（场景库 → 详情）在模块 4 用 react-router 接入，
 * 这里先用 `?scene=<slug>` 取场景，保持模块 3 的验收（打开就能转）独立可测。
 */
export default function App() {
  const [slug] = useState(
    () => new URLSearchParams(window.location.search).get('scene') ?? DEFAULT_SLUG,
  )
  const [scene, setScene] = useState<Scene | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)
  const [live, setLive] = useState<ViewerStats>(EMPTY_STATS)
  const [autoRotate, setAutoRotate] = useState(true)

  useEffect(() => {
    let alive = true
    fetchScene(slug)
      .then((s) => alive && setScene(s))
      .catch((err: unknown) => {
        if (!alive) return
        setMetaError(
          err instanceof ApiError && err.status === 404
            ? `场景 “${slug}” 不在库里（后端 /api/scenes/${slug} 返回 404）`
            : err instanceof Error
              ? err.message
              : String(err),
        )
      })
    return () => {
      alive = false
    }
  }, [slug])

  const pct = Math.round(live.progress * 100)

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <p className="kicker">web3d-lab · 3DGS 在线重建查看器</p>
          <h1>{scene?.title ?? slug}</h1>
          <p className="sub">
            {scene?.summary || '在浏览器里实时旋转一个三维高斯泼溅重建场景。'}
          </p>
        </div>
        <div className="topbar-actions">
          <span className="badge">{scene?.technique ?? '3DGS'}</span>
          <button type="button" onClick={() => setAutoRotate((v) => !v)}>
            {autoRotate ? '停止巡航' : '自动巡航'}
          </button>
        </div>
      </header>

      {metaError && <p className="note note--bad">元数据读取失败：{metaError}</p>}

      <div className="stage">
        <div className="viewport">
          <SplatViewer
            url={scene?.asset_url ?? `/demo/${slug}.spz`}
            autoRotate={autoRotate}
            onStats={setLive}
          />

          {live.status === 'loading' && (
            <div className="overlay">
              <div className="progress">
                <div className="progress-bar" style={{ width: `${pct}%` }} />
              </div>
              <p>
                正在加载高斯点云 {pct > 0 ? `${pct}%` : '…'}
                <br />
                <span className="muted">{scene?.asset_url ?? `/demo/${slug}.spz`}</span>
              </p>
            </div>
          )}

          {live.status === 'error' && (
            <div className="overlay overlay--error">
              <p>
                资产加载失败：{live.error}
                <br />
                <span className="muted">
                  检查 <code>frontend/public{scene?.asset_url ?? `/demo/${slug}.spz`}</code>{' '}
                  是否存在
                </span>
              </p>
            </div>
          )}

          <div className="hud">拖拽旋转 · 滚轮缩放 · 右键平移 · Home 键复位</div>

          {/* 自动化验收钩子：状态镜像到 DOM data-* 上（Playwright/浏览器工具都能读） */}
          <div
            id="viewer-state"
            hidden
            data-status={live.status}
            data-progress={live.progress.toFixed(3)}
            data-splats={live.numSplats}
            data-fps={live.fps}
            data-load-ms={live.loadMs}
            data-bytes={live.bytes}
            data-camera={live.camera.map((v) => v.toFixed(3)).join(',')}
            data-extent={live.extent.toFixed(4)}
            data-bbox={live.bbox.map((v) => v.toFixed(3)).join(',')}
            data-error={live.error ?? ''}
          />
        </div>

        <MetricsPanel scene={scene} live={live} />
      </div>

      <footer className="foot">
        <span>
          数据来源：后端 <code>/api/scenes/{slug}</code>（FastAPI + SQLModel）
        </span>
        <span>渲染：Three.js + @sparkjsdev/spark</span>
      </footer>
    </div>
  )
}

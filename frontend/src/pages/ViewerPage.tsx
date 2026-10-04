import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import MetricsPanel from '../components/MetricsPanel'
import SplatViewer, { type ViewerStats } from '../components/SplatViewer'
import { ApiError, fetchScene, type Scene } from '../lib/api'

export const EMPTY_STATS: ViewerStats = {
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
 * /scenes/:slug —— 3DGS 查看器页。
 *
 * 自动化验收钩子：状态镜像到 DOM 的 `#viewer-state`（data-status / data-splats /
 * data-fps / data-camera / data-extent / data-bbox / data-error），并同步到
 * `window.__web3dViewer`，供 Playwright 与脚本断言。
 */
export default function ViewerPage() {
  const { slug = '' } = useParams()
  const [scene, setScene] = useState<Scene | null>(null)
  const [metaError, setMetaError] = useState<string | null>(null)
  const [live, setLive] = useState<ViewerStats>(EMPTY_STATS)
  const [autoRotate, setAutoRotate] = useState(true)

  useEffect(() => {
    let alive = true
    setScene(null)
    setMetaError(null)
    setLive(EMPTY_STATS)
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
  const assetUrl = scene?.asset_url ?? `/demo/${slug}.spz`

  return (
    <div className="page">
      <header className="topbar">
        <div>
          <p className="kicker">
            <Link to="/scenes">← 场景库</Link>
          </p>
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
          <SplatViewer url={assetUrl} autoRotate={autoRotate} onStats={setLive} />

          {live.status === 'loading' && (
            <div className="overlay">
              <div className="progress">
                <div className="progress-bar" style={{ width: `${pct}%` }} />
              </div>
              <p>
                正在加载高斯点云 {pct > 0 ? `${pct}%` : '…'}
                <br />
                <span className="muted">{assetUrl}</span>
              </p>
            </div>
          )}

          {live.status === 'error' && (
            <div className="overlay overlay--error">
              <p>
                资产加载失败：{live.error}
                <br />
                <span className="muted">
                  检查 <code>frontend/public{assetUrl}</code> 是否存在
                </span>
              </p>
            </div>
          )}

          <div className="hud">拖拽旋转 · 滚轮缩放 · 右键平移 · Home 键复位</div>

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
    </div>
  )
}

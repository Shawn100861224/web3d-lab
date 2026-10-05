import { useEffect, useState } from 'react'
import SceneCard from '../components/SceneCard'
import { fetchScenes, trackEvent, type Scene } from '../lib/api'
import { useBackend } from '../lib/useBackend'

/** /scenes —— 场景库：卡片从 /api/scenes 拉取，点击进详情查看器。 */
export default function LibraryPage() {
  const mode = useBackend()
  const [scenes, setScenes] = useState<Scene[] | null>(null)
  const [total, setTotal] = useState(0)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    trackEvent('view', '/scenes')
    let alive = true
    fetchScenes({ limit: 100 })
      .then((doc) => {
        if (!alive) return
        setScenes(doc.items)
        setTotal(doc.total)
      })
      .catch((err: unknown) => {
        if (!alive) return
        setError(err instanceof Error ? err.message : String(err))
      })
    return () => {
      alive = false
    }
  }, [])

  return (
    <section className="library">
      <header className="page-head">
        <h1>场景库</h1>
        <p>
          每个场景都可以在浏览器里实时旋转查看；点数字来自 <code>/api/scenes</code>
          ，指标为训练时回写的真实评估值。
        </p>
      </header>

      {mode === 'offline' && (
        <p className="note" id="static-mode-note">
          本部署是<strong>静态演示版</strong>：下面这份列表来自随站点打包的场景快照。
          查看器为纯前端实时渲染（Three.js + Spark），不依赖服务端，可正常使用。
        </p>
      )}
      {error && <p className="note note--bad">读取场景列表失败：{error}</p>}
      {scenes === null && !error && <p className="note">正在从后端读取场景列表…</p>}

      {scenes !== null && total === 0 && (
        <p className="note">
          库里还没有场景。跑一次 <code>backend/scripts/seed_scenes.py</code> 灌入示例数据。
        </p>
      )}

      {scenes !== null && total > 0 && (
        <>
          <p className="count" data-total={total}>
            共 {total} 个场景
          </p>
          <div className="grid" id="scene-grid">
            {scenes.map((s) => (
              <SceneCard key={s.slug} scene={s} />
            ))}
          </div>
        </>
      )}
    </section>
  )
}

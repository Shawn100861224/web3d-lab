import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Sparkline from '../components/Sparkline'
import { assetUrl, fetchScenes, fetchStats, trackEvent, type Scene, type Stats } from '../lib/api'
import { useBackend } from '../lib/useBackend'

/**
 * / —— 首页。模块 4 打通「精选场景 → 场景库 → 查看器」主链路，模块 5 在底部接了
 * 一张访问统计卡（数据来自后端 /api/stats）。完整的个人主页与方法对比在模块 7。
 */
export default function HomePage() {
  const mode = useBackend()
  const [featured, setFeatured] = useState<Scene[] | null>(null)
  const [allScenes, setAllScenes] = useState<Scene[] | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    trackEvent('view', '/')
    let alive = true
    fetchScenes({ featured: true, limit: 4 })
      .then((doc) => alive && setFeatured(doc.items))
      .catch(() => alive && setFeatured([]))
    // hero 里那几个数字全部实时取自接口（本站规矩：数字要么实时取、要么不写）
    fetchScenes({ limit: 200 })
      .then((doc) => alive && setAllScenes(doc.items))
      .catch(() => alive && setAllScenes(null))
    fetchStats(14)
      .then((doc) => alive && setStats(doc))
      .catch(() => alive && setStats(null))
    return () => {
      alive = false
    }
  }, [])

  const daily = stats?.daily.map((d) => d.views) ?? []
  const labels = stats?.daily.map((d) => d.date.slice(5)) ?? []

  // hero 的仪表盘读数：全部来自 /api/scenes 与 /api/stats，取不到就显示「—」
  const sceneTotal = allScenes?.length ?? null
  const splatTotal = allScenes
    ? allScenes.reduce((sum, s) => sum + (s.num_points ?? 0), 0)
    : null
  const bestPsnr = allScenes?.length
    ? Math.max(...allScenes.map((s) => s.psnr ?? 0))
    : null
  const fmt = (n: number | null, unit = '') =>
    n == null || (unit === 'dB' && n <= 0) ? '—' : `${n.toLocaleString('zh-CN')}${unit}`

  return (
    <section className="home">
      <header className="hero">
        <div className="hero-cube" aria-hidden="true">
          <i />
          <i />
          <i />
          <i />
          <i />
          <i />
        </div>
        <p className="kicker">郑州大学 · 双足实验室 3D 方向 · 2026</p>
        <h1>
          <span className="w">在浏览器里，</span>
          <span className="w">转一个</span>
          <span className="w">我自己拍的、</span>
          <span className="w hl">自己训出来的 3DGS 场景</span>
        </h1>
        <p className="lede">
          三维高斯泼溅（3D Gaussian Splatting）把场景表示成一堆可学习的椭球，几十秒就能渲出一帧照片级画面。
          这个站点把「拍摄 → COLMAP 注册 → 云端训练 → 导出 → 网页实时渲染 → 指标展示」连成一条链：
          前端 Three.js + Spark 负责渲染，后端 FastAPI 提供场景元数据、访问统计与留言。
          页面上的高斯点数、PSNR/SSIM、帧率都不是写死的 —— 能对账的都对得起。
        </p>
        <div className="hero-actions">
          <Link to="/scenes" className="btn btn--primary">
            进入场景库 →
          </Link>
          <Link to="/methods" className="btn">
            3DGS 方法对比
          </Link>
          <Link to="/about" className="btn">
            关于我
          </Link>
        </div>
        <div className="hero-stats" id="hero-stats">
          <div>
            <b data-hero="scenes">{fmt(sceneTotal)}</b>
            <span>在线场景</span>
          </div>
          <div>
            <b data-hero="splats">{fmt(splatTotal)}</b>
            <span>高斯点合计</span>
          </div>
          <div>
            <b data-hero="best-psnr">
              {bestPsnr != null && bestPsnr > 0 ? bestPsnr.toFixed(2) : '—'}
            </b>
            <span>最好一批 PSNR dB</span>
          </div>
          <div>
            <b data-hero="views">{stats ? stats.total_views.toLocaleString('zh-CN') : '—'}</b>
            <span>累计浏览</span>
          </div>
        </div>
      </header>

      <h2 className="section-title">精选场景</h2>
      {featured === null && <p className="note">正在读取…</p>}
      {featured !== null && featured.length === 0 && (
        <p className="note">还没有精选场景，先去场景库看看。</p>
      )}
      {featured !== null && featured.length > 0 && (
        <div className="feature-row">
          {featured.map((s) => (
            <Link key={s.slug} to={`/scenes/${s.slug}`} className="feature">
              {s.thumbnail_url ? (
                <img src={assetUrl(s.thumbnail_url)} alt={`${s.title} 缩略图`} />
              ) : (
                <div className="thumb-empty">暂无缩略图</div>
              )}
              <div>
                <strong>{s.title}</strong>
                <span>{s.num_points ? `${s.num_points.toLocaleString('zh-CN')} 高斯点` : '—'}</span>
              </div>
            </Link>
          ))}
        </div>
      )}

      <h2 className="section-title">访问统计</h2>
      {stats === null ? (
        <p className="note" id="stats-offline">
          {mode === 'offline' ? (
            <>
              访问统计与留言由后端服务记录（FastAPI + SQLModel + PostgreSQL，39 项测试通过，代码见仓库）。
              本页是<strong>静态演示版</strong>，因此统计数据在这里不可用 —— 场景库与 3DGS 查看器完全正常。
            </>
          ) : (
            '统计接口暂不可用（后端没起或 /api/stats 报错）。'
          )}
        </p>
      ) : (
        <div className="stats-card" id="stats-card">
          <div className="stats-numbers">
            <div>
              <span className="num" data-stat="total_views">
                {stats.total_views}
              </span>
              <span className="label">累计浏览</span>
            </div>
            <div>
              <span className="num" data-stat="unique_clients">
                {stats.unique_clients}
              </span>
              <span className="label">独立访客</span>
            </div>
            <div>
              <span className="num" data-stat="splat_loads">
                {stats.splat_loads}
              </span>
              <span className="label">场景加载成功</span>
            </div>
          </div>
          <div className="stats-chart">
            <Sparkline values={daily} labels={labels} />
            <p className="muted">最近 14 天页面浏览（POST /api/events 写入，GET /api/stats 汇总）</p>
          </div>
          {stats.per_scene.length > 0 && (
            <ul className="stats-scenes">
              {stats.per_scene.slice(0, 5).map((s) => (
                <li key={s.slug}>
                  <Link to={`/scenes/${s.slug}`}>{s.title ?? s.slug}</Link>
                  <span>{s.views} 次</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </section>
  )
}

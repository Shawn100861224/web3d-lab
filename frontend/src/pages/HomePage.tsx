import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import Sparkline from '../components/Sparkline'
import { fetchScenes, fetchStats, trackEvent, type Scene, type Stats } from '../lib/api'

/**
 * / —— 首页。模块 4 打通「精选场景 → 场景库 → 查看器」主链路，模块 5 在底部接了
 * 一张访问统计卡（数据来自后端 /api/stats）。完整的个人主页与方法对比在模块 7。
 */
export default function HomePage() {
  const [featured, setFeatured] = useState<Scene[] | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)

  useEffect(() => {
    trackEvent('view', '/')
    let alive = true
    fetchScenes({ featured: true, limit: 4 })
      .then((doc) => alive && setFeatured(doc.items))
      .catch(() => alive && setFeatured([]))
    fetchStats(14)
      .then((doc) => alive && setStats(doc))
      .catch(() => alive && setStats(null))
    return () => {
      alive = false
    }
  }, [])

  const daily = stats?.daily.map((d) => d.views) ?? []
  const labels = stats?.daily.map((d) => d.date.slice(5)) ?? []

  return (
    <section className="home">
      <header className="hero">
        <p className="kicker">双足实验室 · 3D 方向考核作品</p>
        <h1>
          在浏览器里，转一个
          <br />
          我自己训出来的 3DGS 场景
        </h1>
        <p className="lede">
          三维高斯泼溅（3D Gaussian Splatting）把场景表示成一堆可学习的椭球，
          几十秒就能渲出一帧照片级画面。这个站点把「训练 → 导出 → 网页实时渲染 → 指标展示」
          连成一条链：前端 Three.js + Spark 负责渲染，后端 FastAPI 提供场景元数据、访问统计与留言。
        </p>
        <div className="hero-actions">
          <Link to="/scenes" className="btn btn--primary">
            进入场景库
          </Link>
          <Link to="/about" className="btn">
            关于我
          </Link>
          <Link to="/methods" className="btn">
            3DGS 方法对比
          </Link>
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
                <img src={s.thumbnail_url} alt={`${s.title} 缩略图`} />
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
        <p className="note">统计接口暂不可用（后端没起或 /api/stats 报错）。</p>
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

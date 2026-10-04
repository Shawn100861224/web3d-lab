import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { fetchScenes, type Scene } from '../lib/api'

/**
 * / —— 首页。本模块（4）先把「精选场景 → 场景库 → 查看器」这条主链路串起来；
 * 完整的个人主页与方法对比页在模块 7 补上（届时本页会并入 About 内容）。
 */
export default function HomePage() {
  const [featured, setFeatured] = useState<Scene[] | null>(null)

  useEffect(() => {
    let alive = true
    fetchScenes({ featured: true, limit: 4 })
      .then((doc) => alive && setFeatured(doc.items))
      .catch(() => alive && setFeatured([]))
    return () => {
      alive = false
    }
  }, [])

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
          连成一条链：前端 Three.js + Spark 负责渲染，后端 FastAPI 提供场景元数据与统计。
        </p>
        <div className="hero-actions">
          <Link to="/scenes" className="btn btn--primary">
            进入场景库
          </Link>
          <a
            className="btn"
            href="https://github.com/sparkjsdev/spark"
            target="_blank"
            rel="noreferrer"
          >
            渲染器 Spark
          </a>
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
    </section>
  )
}

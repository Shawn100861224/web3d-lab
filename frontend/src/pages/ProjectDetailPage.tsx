import { useEffect, useMemo, useState } from 'react'
import { Link, useParams } from 'react-router-dom'

import { fetchRadar, formatStars, isPicked, licenseLabel, type RadarData } from '../lib/radar'
import { badgeStyle, coverGlyph, coverStyle, coverUrl, langColor } from '../lib/projectCovers'
import './projects.css'

/**
 * 项目详情页：/projects/:owner/:name
 * 直接用 radar.json 里的真实字段渲染，没有任何二次加工的数字。
 */
export default function ProjectDetailPage() {
  const { owner = '', name = '' } = useParams<{ owner: string; name: string }>()
  const [data, setData] = useState<RadarData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  // 本地 OG 图加载失败 → 回退程序化封面
  const [imgOk, setImgOk] = useState(true)

  useEffect(() => {
    fetchRadar()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const item = useMemo(
    () => data?.items.find((i) => i.owner === owner && i.name === name) ?? null,
    [data, owner, name],
  )

  const copyInstall = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopied(true)
      window.setTimeout(() => setCopied(false), 1600)
    } catch {
      setCopied(false)
    }
  }

  if (error) {
    return (
      <section>
        <p className="empty">读取项目数据失败：{error}</p>
        <Link className="pj-btn" to="/projects">
          ← 返回项目列表
        </Link>
      </section>
    )
  }

  if (!data) {
    return (
      <section>
        <p className="empty">正在读取项目数据…</p>
      </section>
    )
  }

  if (!item) {
    return (
      <section>
        <h1 className="section-title">没有这个项目</h1>
        <p className="lede">
          雷达里没有 <code>{owner}/{name}</code>。可能是仓库改名了，或者它不在这一轮抓取的名单里。
        </p>
        <Link className="pj-btn" to="/projects">
          ← 返回项目列表
        </Link>
      </section>
    )
  }

  const picked = isPicked(item)

  return (
    <article id="project-detail">
      <p>
        <Link className="pj-btn pj-btn--ghost" to="/projects">
          ← 返回项目列表
        </Link>
      </p>

      <div className="pj-detail-cover" style={coverStyle(item.full_name, item.lang)}>
        {imgOk && (
          <img
            className="pj-detail-img"
            src={coverUrl(item.owner, item.name)}
            alt={`${item.full_name} 的 GitHub 卡片`}
            decoding="async"
            onError={() => setImgOk(false)}
          />
        )}
        {!imgOk && <span className="pj-cover-glyph">{coverGlyph(item.name)}</span>}
      </div>

      <div className="pj-detail-head">
        <h1>
          <span className="pj-owner">{item.owner}/</span>
          {item.name}
        </h1>
        {item.hot && (
          <span className="pj-badge" style={badgeStyle('hot')}>
            星速爆发
          </span>
        )}
        {picked && (
          <span className="pj-badge" style={badgeStyle('picked')}>
            我读过
          </span>
        )}
        <a className="pj-btn" href={item.url} target="_blank" rel="noreferrer">
          在 GitHub 打开 ↗
        </a>
        {item.homepage && (
          <a className="pj-btn pj-btn--ghost" href={item.homepage} target="_blank" rel="noreferrer">
            项目主页 ↗
          </a>
        )}
      </div>

      <p className="pj-detail-desc">{item.desc || '（仓库没有填描述）'}</p>

      <div className="pj-tags">
        <span className="pj-tag">
          <i className="pj-dot" style={{ background: langColor(item.lang) }} />
          {item.lang?.trim() || '未标注语言'}
        </span>
        {item.topics.slice(0, 16).map((t) => (
          <span className="pj-tag" key={t}>
            #{t}
          </span>
        ))}
      </div>

      <ul className="pj-kv">
        <li>
          <span>分类</span>
          <b>{item.category}</b>
        </li>
        <li>
          <span>星标</span>
          <b>{formatStars(item.stars)}</b>
        </li>
        <li>
          <span>星速（星/月）</span>
          <b>{item.star_per_month.toFixed(1)}</b>
        </li>
        <li>
          <span>派生</span>
          <b>{formatStars(item.forks)}</b>
        </li>
        <li>
          <span>待处理议题</span>
          <b>{item.issues}</b>
        </li>
        <li>
          <span>仓库年龄</span>
          <b>{item.age_months} 个月</b>
        </li>
        <li>
          <span>许可</span>
          <b>{licenseLabel(item.license)}</b>
        </li>
        <li>
          <span>创建</span>
          <b>{item.created.slice(0, 10)}</b>
        </li>
        <li>
          <span>最近更新</span>
          <b>{item.updated.slice(0, 10)}</b>
        </li>
        <li>
          <span>归档状态</span>
          <b>{item.archived ? '已归档' : '活跃'}</b>
        </li>
      </ul>

      {item.why && (
        <>
          <h2 className="pj-section">我的中文笔记</h2>
          <p className="pj-note-box">{item.why}</p>
        </>
      )}

      {item.install && (
        <>
          <h2 className="pj-section">安装 / 上手命令</h2>
          <div className="pj-cmd">
            <code>{item.install}</code>
            <button type="button" className="pj-btn" onClick={() => copyInstall(item.install as string)}>
              {copied ? '已复制' : '复制'}
            </button>
          </div>
        </>
      )}

      <h2 className="pj-section">仓库地址</h2>
      <p>
        <a href={item.url} target="_blank" rel="noreferrer">
          {item.url}
        </a>
      </p>
    </article>
  )
}

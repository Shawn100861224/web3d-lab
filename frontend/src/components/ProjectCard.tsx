import { useState } from 'react'
import { Link } from 'react-router-dom'

import { formatStars, isPicked, licenseLabel, type RadarItem } from '../lib/radar'
import { badgeStyle, coverGlyph, coverStyle, coverUrl, langColor } from '../lib/projectCovers'

/**
 * 单个项目卡片：封面（优先真实 OG 卡，缺失时回退程序化封面）
 * + 名称 + 中文笔记/描述 + 元信息 + 「查看详情」。
 */
export default function ProjectCard({ item }: { item: RadarItem }) {
  const to = `/projects/${item.owner}/${item.name}`
  const picked = isPicked(item)
  // 中文笔记优先展示（有笔记 = 我读过），否则退回仓库自带描述
  const note = item.why ? item.why.replace(/\s+/g, ' ').trim() : null
  // 本地没有缓存到 OG 图时（或加载失败）就只用程序化封面，不会出现裂图
  const [imgOk, setImgOk] = useState(true)

  return (
    <li className="pj-card" data-full-name={item.full_name}>
      <Link to={to} className="pj-cover" style={coverStyle(item.full_name, item.lang)} tabIndex={-1} aria-hidden="true">
        {imgOk && (
          <img
            className="pj-cover-img"
            src={coverUrl(item.owner, item.name)}
            alt=""
            loading="lazy"
            decoding="async"
            onError={() => setImgOk(false)}
          />
        )}
        {!imgOk && <span className="pj-cover-glyph">{coverGlyph(item.name)}</span>}
        <span className="pj-cover-stars">★ {formatStars(item.stars)}</span>
        <span className="pj-cover-cat">{item.category}</span>
      </Link>

      <div className="pj-body">
        <div className="pj-head">
          <Link to={to} className="pj-name">
            <span className="pj-owner">{item.owner}/</span>
            {item.name}
          </Link>
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
        </div>

        {note && <p className="pj-note">{note}</p>}
        <p className="pj-desc">{item.desc || '（仓库没有填描述）'}</p>

        <div className="pj-meta">
          {item.lang && (
            <span>
              <i className="pj-dot" style={{ background: langColor(item.lang) }} />
              {item.lang}
            </span>
          )}
          <span>★ {formatStars(item.stars)}</span>
          <span>{licenseLabel(item.license)}</span>
        </div>

        <div className="pj-foot">
          <Link to={to} className="pj-btn">
            查看详情
          </Link>
          <a className="pj-btn pj-btn--ghost" href={item.url} target="_blank" rel="noreferrer">
            GitHub ↗
          </a>
        </div>
      </div>
    </li>
  )
}

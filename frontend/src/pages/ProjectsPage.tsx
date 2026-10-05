import { useEffect, useMemo, useState } from 'react'

import ProjectCard from '../components/ProjectCard'
import { fetchRadar, isPicked, type RadarData } from '../lib/radar'
import './projects.css'

type SortKey = 'stars' | 'star_per_month' | 'updated'

const PER_PAGE = 24

/** 分页页码窗口：1 … 4 5 6 … 12（页数多时不把按钮铺满） */
function pageWindow(totalPages: number, current: number): (number | '...')[] {
  if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1)
  const out: (number | '...')[] = [1]
  const from = Math.max(2, current - 1)
  const to = Math.min(totalPages - 1, current + 1)
  if (from > 2) out.push('...')
  for (let p = from; p <= to; p += 1) out.push(p)
  if (to < totalPages - 1) out.push('...')
  out.push(totalPages)
  return out
}

/**
 * 开源项目雷达（卡片流版）。
 * 数据来自 public/radar.json（脚本从 GitHub REST API 抓的真实数据，不编造数字）。
 */
export default function ProjectsPage() {
  const [data, setData] = useState<RadarData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [category, setCategory] = useState('')
  const [lang, setLang] = useState('')
  const [sort, setSort] = useState<SortKey>('stars')
  const [onlyPicked, setOnlyPicked] = useState(false)
  const [page, setPage] = useState(1)

  useEffect(() => {
    fetchRadar()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  /** 分类 + 计数（按数量降序） */
  const categories = useMemo(() => {
    if (!data) return [] as [string, number][]
    const counts = new Map<string, number>()
    for (const item of data.items) counts.set(item.category, (counts.get(item.category) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [data])

  /** 语言 + 计数 */
  const langs = useMemo(() => {
    if (!data) return [] as [string, number][]
    const counts = new Map<string, number>()
    for (const item of data.items) {
      const key = item.lang?.trim() || '未标注'
      counts.set(key, (counts.get(key) ?? 0) + 1)
    }
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [data])

  const filtered = useMemo(() => {
    if (!data) return []
    const needle = q.trim().toLowerCase()
    const rows = data.items.filter((item) => {
      if (category && item.category !== category) return false
      if (lang && (item.lang?.trim() || '未标注') !== lang) return false
      if (onlyPicked && !isPicked(item)) return false
      if (!needle) return true
      return (
        item.full_name.toLowerCase().includes(needle) ||
        item.desc.toLowerCase().includes(needle) ||
        item.topics.some((t) => t.toLowerCase().includes(needle)) ||
        (item.why ?? '').toLowerCase().includes(needle)
      )
    })
    return rows.sort((a, b) => {
      if (sort === 'stars') return b.stars - a.stars
      if (sort === 'star_per_month') return b.star_per_month - a.star_per_month
      return b.updated.localeCompare(a.updated)
    })
  }, [data, q, category, lang, onlyPicked, sort])

  const totalPages = Math.max(1, Math.ceil(filtered.length / PER_PAGE))
  const safePage = Math.min(page, totalPages)
  const shown = filtered.slice((safePage - 1) * PER_PAGE, safePage * PER_PAGE)

  // 换筛选条件后回到第一页，否则会停在空白页
  useEffect(() => {
    setPage(1)
  }, [q, category, lang, sort, onlyPicked])

  return (
    <section id="projects-page">
      <h1 className="section-title">开源项目雷达</h1>
      <p className="lede">
        从 GitHub 抓取的 {data?.total ?? '…'} 个三维视觉 / SLAM / 神经渲染项目，含 {data?.picked ?? '…'}{' '}
        个我读过并写了中文笔记的。数据抓取于 {data?.generated_at ?? '…'}
        {data ? `（共 ${filtered.length} 个符合当前筛选）` : ''}
      </p>

      <div className="pj-toolbar">
        <input
          className="pj-search"
          type="search"
          placeholder="搜索仓库名 / 描述 / 主题 / 笔记…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          aria-label="搜索项目"
        />
        <select className="pj-select" value={sort} onChange={(e) => setSort(e.target.value as SortKey)} aria-label="排序方式">
          <option value="stars">按星标数</option>
          <option value="star_per_month">按星速（星/月）</option>
          <option value="updated">按最近更新</option>
        </select>
        <select className="pj-select" value={lang} onChange={(e) => setLang(e.target.value)} aria-label="按语言筛选">
          <option value="">全部语言</option>
          {langs.map(([name, n]) => (
            <option key={name} value={name}>
              {name}（{n}）
            </option>
          ))}
        </select>
        <label className="pj-toggle">
          <input type="checkbox" checked={onlyPicked} onChange={(e) => setOnlyPicked(e.target.checked)} />
          只看我读过的
        </label>
      </div>

      <div className="pj-chips">
        <button type="button" className="pj-chip" data-on={category === ''} onClick={() => setCategory('')}>
          全部 <b>{data?.total ?? 0}</b>
        </button>
        {categories.map(([name, n]) => (
          <button
            key={name}
            type="button"
            className="pj-chip"
            data-on={category === name}
            onClick={() => setCategory(category === name ? '' : name)}
          >
            {name} <b>{n}</b>
          </button>
        ))}
      </div>

      {error && <p className="empty">读取 radar.json 失败：{error}</p>}

      {!data && !error && <p className="empty">正在读取项目数据…</p>}

      {data && shown.length === 0 && <p className="empty">没有符合筛选的项目，换个关键词试试。</p>}

      <ul className="pj-grid">
        {shown.map((item) => (
          <ProjectCard key={item.full_name} item={item} />
        ))}
      </ul>

      {data && totalPages > 1 && (
        <nav className="pj-pager" aria-label="分页">
          <button type="button" className="pj-page-btn" disabled={safePage === 1} onClick={() => setPage(safePage - 1)}>
            上一页
          </button>
          {pageWindow(totalPages, safePage).map((p, i) =>
            p === '...' ? (
              <span key={`gap-${i}`}>…</span>
            ) : (
              <button
                key={p}
                type="button"
                className="pj-page-btn"
                data-on={p === safePage}
                onClick={() => setPage(p)}
              >
                {p}
              </button>
            ),
          )}
          <button
            type="button"
            className="pj-page-btn"
            disabled={safePage === totalPages}
            onClick={() => setPage(safePage + 1)}
          >
            下一页
          </button>
          <span>
            第 {(safePage - 1) * PER_PAGE + 1}–{Math.min(safePage * PER_PAGE, filtered.length)} 项 / 共{' '}
            {filtered.length} 项
          </span>
        </nav>
      )}
    </section>
  )
}

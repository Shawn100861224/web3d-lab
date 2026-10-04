import { useEffect, useMemo, useState } from 'react'
import { fetchRadar, formatStars, isPicked, type RadarData, type RadarItem } from '../lib/radar'

type SortKey = 'stars' | 'star_per_month' | 'updated'

/**
 * 3D 项目雷达：数据来自 public/radar.json（脚本从 GitHub REST API 抓的真实数据，
 * 抓取脚本在原静态页仓库 tools/fetch_projects.py）。这里只做检索与排序，
 * 不编造任何数字——页脚显示数据生成时间。
 */
export default function RadarTable() {
  const [data, setData] = useState<RadarData | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [q, setQ] = useState('')
  const [category, setCategory] = useState<string>('')
  const [sort, setSort] = useState<SortKey>('stars')
  const [onlyPicked, setOnlyPicked] = useState(false)

  useEffect(() => {
    fetchRadar()
      .then(setData)
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }, [])

  const categories = useMemo(() => {
    if (!data) return []
    const counts = new Map<string, number>()
    for (const item of data.items) counts.set(item.category, (counts.get(item.category) ?? 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1])
  }, [data])

  const rows = useMemo(() => {
    if (!data) return []
    const needle = q.trim().toLowerCase()
    const filtered = data.items.filter((item) => {
      if (category && item.category !== category) return false
      if (onlyPicked && !isPicked(item)) return false
      if (!needle) return true
      return (
        item.full_name.toLowerCase().includes(needle) ||
        item.desc.toLowerCase().includes(needle) ||
        item.topics.some((t) => t.toLowerCase().includes(needle))
      )
    })
    const key = (item: RadarItem) =>
      sort === 'stars' ? item.stars : sort === 'star_per_month' ? item.star_per_month : item.updated
    return [...filtered].sort((a, b) => (key(b) > key(a) ? 1 : key(b) < key(a) ? -1 : 0))
  }, [data, q, category, sort, onlyPicked])

  if (error) return <p className="note note--bad">项目雷达数据读取失败：{error}</p>
  if (!data) return <p className="note">正在读取项目雷达数据…</p>

  const pickedCount = data.items.filter(isPicked).length

  return (
    <div className="radar">
      <div className="radar-stats">
        <div>
          <b data-stat="total">{data.total}</b>
          <span>仓库总数</span>
        </div>
        <div>
          <b data-stat="picked">{pickedCount}</b>
          <span>我读过 / 精选</span>
        </div>
        <div>
          <b data-stat="hot">{data.hot}</b>
          <span>星速爆发</span>
        </div>
        <div>
          <b>{data.items.reduce((sum, i) => sum + i.stars, 0).toLocaleString('zh-CN')}</b>
          <span>合计星标</span>
        </div>
      </div>

      <div className="radar-tools">
        <input
          type="search"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="搜项目名 / 描述 / topic，如 colmap、splat、depth"
          aria-label="搜索项目"
        />
        <select value={category} onChange={(e) => setCategory(e.target.value)} aria-label="按分类过滤">
          <option value="">全部分类</option>
          {categories.map(([name, count]) => (
            <option key={name} value={name}>
              {name}（{count}）
            </option>
          ))}
        </select>
        <select value={sort} onChange={(e) => setSort(e.target.value as SortKey)} aria-label="排序方式">
          <option value="stars">星标数</option>
          <option value="star_per_month">星速（星/月）</option>
          <option value="updated">最近更新</option>
        </select>
        <label className="radar-toggle">
          <input type="checkbox" checked={onlyPicked} onChange={(e) => setOnlyPicked(e.target.checked)} />
          只看我读过的
        </label>
      </div>

      <p className="count" data-rows={rows.length}>
        命中 {rows.length} 个
      </p>

      <ul className="radar-list">
        {rows.slice(0, 40).map((item) => (
          <li key={item.full_name} data-repo={item.full_name}>
            <div className="radar-main">
              <a href={item.url} target="_blank" rel="noreferrer" className="radar-name">
                {item.full_name}
              </a>
              {item.hot && <span className="tag tag--hot">星速爆发</span>}
              {isPicked(item) && <span className="tag">我读过</span>}
              <span className="tag tag--muted">{item.category}</span>
            </div>
            <p className="radar-desc">{item.desc}</p>
            {item.why && <p className="radar-why">笔记：{item.why}</p>}
            {item.install && <code className="radar-install">{item.install}</code>}
            <div className="radar-meta">
              <span>★ {formatStars(item.stars)}</span>
              <span>{item.star_per_month.toFixed(1)} 星/月</span>
              <span>{item.lang ?? '—'}</span>
              <span>{item.license ?? '—'}</span>
              <span>更新 {item.updated}</span>
            </div>
          </li>
        ))}
      </ul>
      {rows.length > 40 && <p className="note">只显示前 40 条，用搜索或分类再收窄。</p>}
      <p className="muted">
        数据源：{data.source} · 生成于 {data.generated_at}（脚本抓取，非手写）
      </p>
    </div>
  )
}

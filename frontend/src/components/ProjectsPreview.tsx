import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router-dom'

import ProjectCard from './ProjectCard'
import { fetchRadar, isPicked, type RadarData } from '../lib/radar'
import '../pages/projects.css'

/**
 * /about 里的「项目雷达」入口：只放 6 张卡片（优先带中文笔记的），
 * 完整 116 个的检索/筛选/分页在 /projects。
 */
export default function ProjectsPreview() {
  const [data, setData] = useState<RadarData | null>(null)

  useEffect(() => {
    fetchRadar()
      .then(setData)
      .catch(() => setData(null))
  }, [])

  const picks = useMemo(() => {
    if (!data) return []
    const picked = data.items.filter(isPicked).sort((a, b) => b.stars - a.stars)
    const rest = data.items.filter((i) => !isPicked(i)).sort((a, b) => b.stars - a.stars)
    return [...picked, ...rest].slice(0, 6)
  }, [data])

  if (!data) return <p className="empty">正在读取项目雷达数据…</p>

  return (
    <>
      <ul className="pj-grid pj-grid--preview">
        {picks.map((item) => (
          <ProjectCard key={item.full_name} item={item} />
        ))}
      </ul>
      <p>
        <Link className="pj-btn" to="/projects">
          查看全部 {data.total} 个项目（可搜索 / 按分类筛选 / 排序）→
        </Link>
      </p>
    </>
  )
}

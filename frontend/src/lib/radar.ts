/** 项目雷达数据（frontend/public/radar.json）。 */

export type RadarItem = {
  full_name: string
  name: string
  owner: string
  url: string
  homepage: string | null
  desc: string
  stars: number
  forks: number
  issues: number
  lang: string | null
  license: string | null
  topics: string[]
  created: string
  updated: string
  archived: boolean
  star_per_month: number
  age_months: number
  hot: boolean
  tier: string | null
  category: string
  /** 有中文笔记的才是「我读过的」 */
  why: string | null
  install: string | null
}

export type RadarData = {
  generated_at: string
  source: string
  total: number
  picked: number
  hot: number
  categories: Record<string, number> | string[]
  items: RadarItem[]
}

export async function fetchRadar(): Promise<RadarData> {
  const res = await fetch(`${import.meta.env.BASE_URL}radar.json`)
  if (!res.ok) throw new Error(`读取 radar.json 失败：HTTP ${res.status}`)
  return (await res.json()) as RadarData
}

export function isPicked(item: RadarItem): boolean {
  return Boolean(item.why)
}

export function formatStars(n: number): string {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

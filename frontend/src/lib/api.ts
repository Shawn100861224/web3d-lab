/** 与后端 /api 的契约层。字段名跟 backend/app/models.py 的 SceneBase 一一对应。 */

export type Scene = {
  id: number
  slug: string
  title: string
  summary: string
  technique: string
  source: string
  num_points: number | null
  sh_degree: number | null
  iterations: number | null
  train_seconds: number | null
  gpu_mem_mb: number | null
  capture_device: string | null
  capture_views: number | null
  psnr: number | null
  ssim: number | null
  lpips: number | null
  asset_url: string
  asset_format: string
  thumbnail_url: string | null
  license: string
  featured: boolean
  published: boolean
  created_at: string
  updated_at: string
}

export type SceneList = { total: number; items: Scene[] }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
    this.name = 'ApiError'
  }
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(path)
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = (await res.json()) as { detail?: string }
      if (body.detail) detail = body.detail
    } catch {
      /* 响应不是 JSON，保留状态文本 */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as T
}

export function fetchScene(slug: string): Promise<Scene> {
  return getJson<Scene>(`/api/scenes/${encodeURIComponent(slug)}`)
}

export function fetchScenes(params: { technique?: string; featured?: boolean; limit?: number } = {}) {
  const qs = new URLSearchParams()
  if (params.technique) qs.set('technique', params.technique)
  if (params.featured !== undefined) qs.set('featured', String(params.featured))
  if (params.limit) qs.set('limit', String(params.limit))
  const suffix = qs.toString() ? `?${qs}` : ''
  return getJson<SceneList>(`/api/scenes${suffix}`)
}

export function formatBytes(bytes: number): string {
  if (!bytes) return '—'
  const mb = bytes / 1024 / 1024
  return mb >= 1 ? `${mb.toFixed(2)} MB` : `${(bytes / 1024).toFixed(0)} KB`
}

export function formatCount(n: number | null): string {
  if (n === null || n === undefined) return '—'
  return n.toLocaleString('zh-CN')
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return '—'
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return m ? `${m} 分 ${s} 秒` : `${s} 秒`
}

/**
 * 与后端 /api 的契约层。字段名跟 backend/app/models.py 的 SceneBase 一一对应。
 *
 * 线上可能只有静态托管（没后端），所以这里做了三层处理：
 *  1. 所有请求都走 `apiUrl()`，部署时用 VITE_API_BASE 指到后端，本地留空走 vite 代理；
 *  2. 场景「读」类接口在后端不可达时自动退回打包进站点的 scenes-fallback.json；
 *  3. 写类接口（统计、留言）在后端已知离线时直接不打扰用户，失败也只记 console。
 */

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

const ENV = import.meta.env as Record<string, string | undefined>
/** 部署时指向后端（如 https://api.example.com）；本地留空，走 vite 的 /api 代理 */
export const API_BASE = (ENV.VITE_API_BASE ?? '').replace(/\/+$/, '')

export function apiUrl(path: string): string {
  return `${API_BASE}${path}`
}

let backendOnline: boolean | null = null
const listeners = new Set<(v: boolean) => void>()

function setBackendOnline(value: boolean): void {
  if (backendOnline === value) return
  backendOnline = value
  for (const fn of listeners) fn(value)
}

/** null = 还没探测过 */
export function isBackendOnline(): boolean | null {
  return backendOnline
}

export function onBackendStatus(fn: (v: boolean) => void): () => void {
  listeners.add(fn)
  return () => listeners.delete(fn)
}

/** 启动时探测一次：首探 2.5 秒不响应就再给一次 8 秒长超时（后端冷启动需要），
 *  两次都不行才算离线；页面照常可用（静态兜底）。 */
export async function probeBackend(timeoutMs = 2500): Promise<boolean> {
  // 冷启动实测：线上 /api/health 第一次要 ~1.1s（Neon 自动唤醒 + 云函数冷启），
  // 稍冷一点就会超过 2.5s 的首次超时 → fetch 被 AbortController 中断 →
  // 前端误判「离线」→ 首屏短暂回退到「静态演示版」提示（2026-10-11 抓控制台实测到
  // /api/health → net::ERR_ABORTED 就是这个原因）。
  // 所以：首探用短超时保证「正常时快速确认」，失败后再给一次长超时——冷启动的机器
  // 有足够时间醒来；确实离线也仍会在 ~10s 内定论，不会一直挂着。
  const attempt = async (ms: number): Promise<boolean> => {
    const ctrl = new AbortController()
    const timer = setTimeout(() => ctrl.abort(), ms)
    try {
      const res = await fetch(apiUrl('/api/health'), { signal: ctrl.signal })
      return res.ok
    } catch {
      return false
    } finally {
      clearTimeout(timer)
    }
  }

  let ok = await attempt(timeoutMs)
  if (!ok) {
    ok = await attempt(Math.max(timeoutMs * 3, 8000))
  }
  setBackendOnline(ok)
  return ok
}

// ---------- 静态兜底（后端不可达时用） ----------

type FallbackFile = { items: Scene[] }

let fallbackCache: Scene[] | null = null

async function loadFallbackScenes(): Promise<Scene[]> {
  if (fallbackCache) return fallbackCache
  // BASE_URL 由 vite 的 base 决定：子路径部署时资源在 /<repo>/schemes-fallback.json
  const res = await fetch(`${import.meta.env.BASE_URL}scenes-fallback.json`)
  if (!res.ok) throw new Error(`静态兜底数据缺失：HTTP ${res.status}`)
  const doc = (await res.json()) as FallbackFile
  fallbackCache = doc.items
  return fallbackCache
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(apiUrl(path))
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

/**
 * 把后端/兜底数据里的站内绝对路径（如 `/demo/x.splat`）解析成当前部署下可用的地址。
 * 子路径部署（GitHub Pages 的 /<repo>/）时必须补 base，否则会去站点根目录找 → 404。
 */
export function assetUrl(path: string | null | undefined): string {
  if (!path) return ''
  if (!path.startsWith('/')) return path
  const base = import.meta.env.BASE_URL.replace(/\/$/, '')
  return `${base}${path}`
}

export async function fetchScene(slug: string): Promise<Scene> {
  try {
    const scene = await getJson<Scene>(`/api/scenes/${encodeURIComponent(slug)}`)
    setBackendOnline(true)
    return scene
  } catch (err) {
    const offline = await loadFallbackScenes().catch(() => null)
    const hit = offline?.find((s) => s.slug === slug)
    if (hit) {
      setBackendOnline(false)
      return hit
    }
    throw err
  }
}

export async function fetchScenes(
  params: { technique?: string; featured?: boolean; limit?: number } = {},
): Promise<SceneList> {
  const qs = new URLSearchParams()
  if (params.technique) qs.set('technique', params.technique)
  if (params.featured !== undefined) qs.set('featured', String(params.featured))
  if (params.limit) qs.set('limit', String(params.limit))
  const suffix = qs.toString() ? `?${qs}` : ''
  try {
    const doc = await getJson<SceneList>(`/api/scenes${suffix}`)
    setBackendOnline(true)
    return doc
  } catch (err) {
    const all = await loadFallbackScenes().catch(() => null)
    if (!all) throw err
    setBackendOnline(false)
    let items = all.filter((s) => s.published)
    if (params.technique) items = items.filter((s) => s.technique === params.technique)
    if (params.featured !== undefined) items = items.filter((s) => s.featured === params.featured)
    if (params.limit) items = items.slice(0, params.limit)
    return { total: items.length, items }
  }
}

/**
 * 同参数「还在飞」时复用同一个请求的场景列表读取。
 *
 * 背景（2026-10-14 实测基线）：首页 App.tsx 与 HomePage.tsx 各调一次
 * fetchScenes({ limit: 200 })，于是同一个 URL 在首屏被请求两次 ——
 * 白花 12,209 B 与一个 RTT（实测两份资源条目 duration 都是 3.7–4.1 s）。
 *
 * 只做 in-flight 复用（请求一落地就从表里删掉），**不做成功缓存** ——
 * 站点的规矩是数字要么实时取、要么不写，所以不去承担任何过期风险。
 */
const sceneListInflight = new Map<string, Promise<SceneList>>()

export function fetchScenesCached(
  params: { technique?: string; featured?: boolean; limit?: number } = {},
): Promise<SceneList> {
  const key = JSON.stringify(params)
  const hit = sceneListInflight.get(key)
  if (hit) return hit
  const p = fetchScenes(params)
  sceneListInflight.set(key, p)
  const drop = () => {
    // 只在自己仍是当前那次请求时才删，避免把后来者的记录一起删掉
    if (sceneListInflight.get(key) === p) sceneListInflight.delete(key)
  }
  p.then(drop, drop)
  return p
}

/**
 * 读取随构建打包的静态快照（同域资源，无云函数冷启动）。
 *
 * 用途：首屏「先渲染快照、再用接口覆盖」—— 见 HomePage 的 useEffect。
 * ⚠️ 调用方**必须让用户看得出这是快照值**（本站规矩：数字要么实时取、要么不写）；
 * HomePage 里那句 `data-hero-source="snapshot"` 的标注就是干这个的。
 */
export function loadBundledScenes(): Promise<Scene[]> {
  return loadFallbackScenes()
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


// ---------- 访问统计 ----------

export type SceneStat = { slug: string; title: string | null; views: number }
export type DailyStat = { date: string; views: number }
export type Stats = {
  total_views: number
  unique_clients: number
  splat_loads: number
  per_scene: SceneStat[]
  daily: DailyStat[]
  generated_at: string
}

const CLIENT_ID_KEY = 'web3d-lab:client-id'

/** 访客随机 ID：只存在浏览器本地，后端拿它算「独立访客」，与身份无关。 */
export function getClientId(): string {
  try {
    const existing = window.localStorage.getItem(CLIENT_ID_KEY)
    if (existing) return existing
    const fresh =
      typeof crypto.randomUUID === 'function'
        ? crypto.randomUUID()
        : `c-${Math.random().toString(36).slice(2)}${Date.now().toString(36)}`
    window.localStorage.setItem(CLIENT_ID_KEY, fresh)
    return fresh
  } catch {
    // 隐身模式/禁用存储时退化成一次性 ID，统计仍然可用
    return `ephemeral-${Math.random().toString(36).slice(2)}`
  }
}

export type TrackedEvent = 'view' | 'splat_load' | 'render_error'

/** 上报事件。统计不该拖慢页面：失败只记 console，不抛给调用方。 */
export function trackEvent(event: TrackedEvent, path: string, sceneSlug?: string | null): void {
  // 已知后端离线（静态托管）时直接跳过：不让统计失败污染控制台，也不白等一次请求
  if (backendOnline === false) return
  const body = JSON.stringify({
    event,
    path,
    scene_slug: sceneSlug ?? null,
    client_id: getClientId(),
    referrer: document.referrer || null,
  })
  void fetch(apiUrl('/api/events'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body,
    keepalive: true,
  })
    .then((r) => {
      if (!r.ok && r.status !== 202) console.warn('[stats] 事件上报未成功', r.status)
    })
    .catch((err: unknown) => console.warn('[stats] 事件上报失败', err))
}

export function fetchStats(days = 14): Promise<Stats> {
  return getJson<Stats>(`/api/stats?days=${days}`)
}

/** 后端是否可用（给页面显示「静态模式」用） */
export function backendMode(): 'online' | 'offline' | 'unknown' {
  if (backendOnline === null) return 'unknown'
  return backendOnline ? 'online' : 'offline'
}


// ---------- 留言板 ----------

export type GuestbookEntry = {
  id: number
  name: string
  message: string
  scene_slug: string | null
  created_at: string
}

export type GuestbookList = { total: number; items: GuestbookEntry[] }

export type GuestbookSnapshot = { total: number; items: GuestbookEntry[]; note?: string }

/** 静态部署下的留言快照（只读）——让留言板不是一片空白，而是"示例数据 + 边界说明"。 */
export async function fetchGuestbookSnapshot(): Promise<GuestbookSnapshot> {
  const res = await fetch(`${import.meta.env.BASE_URL}guestbook-fallback.json`)
  if (!res.ok) throw new Error(`留言快照缺失：HTTP ${res.status}`)
  return (await res.json()) as GuestbookSnapshot
}

export function fetchGuestbook(sceneSlug?: string | null, limit = 100): Promise<GuestbookList> {
  // 静态模式：留言板没有后端就直说，不要抛异常让页面报错
  if (backendOnline === false) {
    return Promise.reject(new ApiError(503, '后端未连接（静态托管模式）'))
  }
  const qs = new URLSearchParams({ limit: String(limit) })
  if (sceneSlug) qs.set('scene_slug', sceneSlug)
  return getJson<GuestbookList>(`/api/guestbook?${qs}`)
}

/** 提交留言。429 时抛 ApiError(status=429)，由页面提示限流秒数。 */
export async function postGuestbook(input: {
  name: string
  message: string
  scene_slug?: string | null
}): Promise<GuestbookEntry> {
  const res = await fetch(apiUrl('/api/guestbook'), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ ...input, scene_slug: input.scene_slug ?? null, client_id: getClientId() }),
  })
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`
    try {
      const doc = (await res.json()) as { detail?: string }
      if (doc.detail) detail = doc.detail
    } catch {
      /* 非 JSON 响应 */
    }
    throw new ApiError(res.status, detail)
  }
  return (await res.json()) as GuestbookEntry
}

import { useEffect, useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useBackend } from '../lib/useBackend'
import {
  ApiError,
  fetchGuestbook,
  fetchGuestbookSnapshot,
  fetchScenes,
  postGuestbook,
  trackEvent,
  type GuestbookEntry,
  type GuestbookSnapshot,
  type Scene,
} from '../lib/api'

/**
 * /guestbook —— 留言板。支持 ?scene=<slug> 只看某场景的留言。
 *
 * 两种运行形态：
 *  * **连得上后端**：表单可写，列表来自 /api/guestbook（含限流与错误提示）。
 *  * **静态演示版**（线上当前形态）：表单换成一段说明，列表展示随站点打包的
 *    **离线快照**并明确标注——宁可写清边界，也不要让访客看到"空白/报错"。
 *
 * XSS 说明：这里**只用 JSX 插值**渲染留言正文，绝不使用 dangerouslySetInnerHTML。
 * 后端按原文存储（含 `<script>`），转义发生在这一层——React 会把尖括号渲染成文本。
 */
export default function GuestbookPage() {
  const mode = useBackend()
  const [params] = useSearchParams()
  const sceneFilter = params.get('scene')

  const [entries, setEntries] = useState<GuestbookEntry[] | null>(null)
  const [snapshot, setSnapshot] = useState<GuestbookSnapshot | null>(null)
  const [total, setTotal] = useState(0)
  const [scenes, setScenes] = useState<Scene[]>([])
  const [name, setName] = useState('')
  const [message, setMessage] = useState('')
  const [sceneSlug, setSceneSlug] = useState(sceneFilter ?? '')
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [sending, setSending] = useState(false)

  const offline = mode === 'offline'

  const reload = () => {
    fetchGuestbook(sceneFilter)
      .then((doc) => {
        setEntries(doc.items)
        setTotal(doc.total)
      })
      .catch((err: unknown) => setError(err instanceof Error ? err.message : String(err)))
  }

  useEffect(() => {
    trackEvent('view', '/guestbook', sceneFilter)
    if (offline) {
      // 静态演示版：读打包进来的快照
      fetchGuestbookSnapshot()
        .then((doc) => {
          const items = sceneFilter ? doc.items.filter((i) => i.scene_slug === sceneFilter) : doc.items
          setSnapshot({ ...doc, items })
          setTotal(items.length)
        })
        .catch(() => setSnapshot({ total: 0, items: [] }))
    } else {
      reload()
    }
    fetchScenes({ limit: 100 })
      .then((doc) => setScenes(doc.items))
      .catch(() => setScenes([]))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sceneFilter, offline])

  const submit = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setNotice(null)
    setSending(true)
    try {
      await postGuestbook({ name, message, scene_slug: sceneSlug || null })
      setName('')
      setMessage('')
      setNotice('留言已提交，感谢反馈。')
      reload()
    } catch (err: unknown) {
      if (err instanceof ApiError && err.status === 429) {
        setError(`提交太频繁：${err.message}`)
      } else {
        setError(err instanceof Error ? err.message : String(err))
      }
    } finally {
      setSending(false)
    }
  }

  const shown: GuestbookEntry[] | null = offline ? (snapshot?.items ?? null) : entries

  return (
    <section className="library">
      <header className="page-head">
        <h1>留言板</h1>
        <p>
          对某个场景的重建质量、页面交互有任何意见都可以留在这里；数据写进后端数据库，
          同一访客 10 分钟最多 3 条（防刷）。
        </p>
      </header>

      {offline ? (
        <p className="note" id="gb-offline">
          留言写入需要后端服务。本部署是<strong>静态演示版</strong>——下面展示的是随站点打包的
          <strong>离线快照</strong>，用于说明数据形态；后端实现见仓库
          （FastAPI + SQLModel + PostgreSQL，含限流与注入防护的测试，<code>backend/tests</code>）。
        </p>
      ) : (
        <form className="gb-form" onSubmit={submit}>
          <div className="gb-row">
            <label>
              称呼
              <input
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                maxLength={40}
                placeholder="怎么称呼你"
              />
            </label>
            <label>
              关联场景（可选）
              <select value={sceneSlug} onChange={(e) => setSceneSlug(e.target.value)}>
                <option value="">不指定</option>
                {scenes.map((s) => (
                  <option key={s.slug} value={s.slug}>
                    {s.title}
                  </option>
                ))}
              </select>
            </label>
          </div>
          <label className="gb-full">
            留言
            <textarea
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              required
              maxLength={600}
              rows={4}
              placeholder="例如：这个场景在浏览器里转起来很顺，但背景有点糊"
            />
          </label>
          <div className="gb-actions">
            <button type="submit" disabled={sending}>
              {sending ? '提交中…' : '提交留言'}
            </button>
            <span className="muted">{message.length}/600</span>
          </div>
          {error && (
            <p className="note note--bad" id="gb-error">
              {error}
            </p>
          )}
          {notice && (
            <p className="note note--ok" id="gb-notice">
              {notice}
            </p>
          )}
        </form>
      )}

      <h2 className="section-title">
        {offline ? '留言快照（只读）' : '全部留言'}
        {sceneFilter && (
          <>
            {' '}
            · 仅看 <code>{sceneFilter}</code>{' '}
            <Link to="/guestbook">（看全部）</Link>
          </>
        )}
      </h2>
      <p className="count" data-total={total}>
        共 {total} 条
      </p>

      {shown === null && <p className="note">正在读取…</p>}
      {shown !== null && shown.length === 0 && (
        <p className="note" id="gb-empty">
          {offline
            ? '这里目前没有任何留言 —— 静态演示版没有后端，写不进来；留言功能本身是完整实现的（限流、注入防护都有测试覆盖），本地起后端就能真的写入。'
            : '还没有留言，做第一个吧。'}
        </p>
      )}
      {shown !== null && shown.length > 0 && (
        <ul className="gb-list" id="gb-list">
          {shown.map((entry) => (
            <li key={entry.id} data-entry-id={entry.id}>
              <div className="gb-meta">
                <strong>{entry.name}</strong>
                <span>{new Date(entry.created_at).toLocaleString('zh-CN')}</span>
                {entry.scene_slug && <Link to={`/scenes/${entry.scene_slug}`}>{entry.scene_slug}</Link>}
                {offline && <span className="tag tag--muted">离线快照</span>}
              </div>
              <p>{entry.message}</p>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

import { useEffect, useState } from 'react'

type Health = {
  status: string
  service: string
  version: string
  db: string
  uptime_seconds: number
}

type Probe =
  | { state: 'loading' }
  | { state: 'ok'; body: Health }
  | { state: 'error'; message: string }

/**
 * 模块 1 的脚手架页：唯一职责是证明「前端 → /api 代理 → 后端」这条通道是通的。
 * 真正的个人主页 / 场景库 / 查看器在模块 3、4、7 里做。
 */
export default function App() {
  const [probe, setProbe] = useState<Probe>({ state: 'loading' })

  useEffect(() => {
    let alive = true
    fetch('/api/health')
      .then(async (r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`)
        return (await r.json()) as Health
      })
      .then((body) => alive && setProbe({ state: 'ok', body }))
      .catch(
        (e: unknown) =>
          alive &&
          setProbe({
            state: 'error',
            message: e instanceof Error ? e.message : String(e),
          }),
      )
    return () => {
      alive = false
    }
  }, [])

  return (
    <main className="scaffold">
      <h1>web3d-lab</h1>
      <p className="tagline">3DGS 在线重建查看器 · 脚手架自检页</p>

      <section className={`card card--${probe.state}`}>
        <h2>后端连通性</h2>
        {probe.state === 'loading' && <p>探测 <code>/api/health</code> …</p>}
        {probe.state === 'error' && (
          <p>
            ✕ 连不上后端（<code>{probe.message}</code>）。请先启动 backend：
            <br />
            <code>.venv/Scripts/python.exe -m uvicorn app.main:app --port 8000</code>
          </p>
        )}
        {probe.state === 'ok' && (
          <>
            <p>✓ 链路正常</p>
            <dl>
              <dt>service</dt>
              <dd>{probe.body.service}</dd>
              <dt>version</dt>
              <dd>{probe.body.version}</dd>
              <dt>db</dt>
              <dd>{probe.body.db}</dd>
              <dt>uptime</dt>
              <dd>{probe.body.uptime_seconds}s</dd>
            </dl>
          </>
        )}
      </section>
    </main>
  )
}

import { Link, useLocation } from 'react-router-dom'

/** 通配路由页面。EdgeOne Pages 的文档明确要求 SPA 用 catch-all 由客户端处理 404
 *  （不要往输出根目录塞 404.html，那会干扰客户端路由）。 */
export default function NotFoundPage() {
  const { pathname } = useLocation()
  return (
    <section className="library">
      <header className="page-head">
        <h1>这个路径没有东西</h1>
        <p>
          <code>{pathname}</code> 没有对应页面。
        </p>
      </header>
      <div className="hero-actions">
        <Link to="/" className="btn btn--primary">
          回首页
        </Link>
        <Link to="/scenes" className="btn">
          去场景库
        </Link>
      </div>
    </section>
  )
}

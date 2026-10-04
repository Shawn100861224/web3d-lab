import { Link } from 'react-router-dom'
import { formatCount } from '../lib/api'
import type { Scene } from '../lib/api'

type Props = { scene: Scene }

/** 场景库卡片：缩略图 + 标题 + 方法徽标 + 关键数字。 */
export default function SceneCard({ scene }: Props) {
  return (
    <Link to={`/scenes/${scene.slug}`} className="card-scene">
      <div className="thumb">
        {scene.thumbnail_url ? (
          <img src={scene.thumbnail_url} alt={`${scene.title} 的渲染缩略图`} loading="lazy" />
        ) : (
          <div className="thumb-empty">暂无缩略图</div>
        )}
        <span className="thumb-badge">{scene.technique}</span>
      </div>
      <div className="card-body">
        <h3>{scene.title}</h3>
        <p>{scene.summary}</p>
        <dl>
          <div>
            <dt>高斯点</dt>
            <dd>{formatCount(scene.num_points)}</dd>
          </div>
          <div>
            <dt>PSNR</dt>
            <dd>{scene.psnr != null ? scene.psnr.toFixed(2) : '待回写'}</dd>
          </div>
          <div>
            <dt>来源</dt>
            <dd>{scene.source === 'sample' ? '官方示例' : '本机自训'}</dd>
          </div>
        </dl>
      </div>
    </Link>
  )
}

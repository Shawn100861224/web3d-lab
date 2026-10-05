import { Link } from 'react-router-dom'
import { assetUrl, formatCount } from '../lib/api'
import type { Scene } from '../lib/api'

/** 来源必须如实区分：自己拍的/自己训的 ≠ 官方示例 ≠ 公开数据集（别人拍的） */
const SOURCE_LABEL: Record<string, string> = {
  'self-trained': '本机自训',
  sample: '官方示例',
  'public-dataset': '公开数据集',
}

type Props = { scene: Scene }

/** 场景库卡片：缩略图 + 标题 + 方法徽标 + 关键数字。 */
export default function SceneCard({ scene }: Props) {
  return (
    <Link to={`/scenes/${scene.slug}`} className="card-scene">
      <div className="thumb">
        {scene.thumbnail_url ? (
          <img src={assetUrl(scene.thumbnail_url)} alt={`${scene.title} 的渲染缩略图`} loading="lazy" />
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
            <dd>{SOURCE_LABEL[scene.source] ?? scene.source}</dd>
          </div>
        </dl>
      </div>
    </Link>
  )
}

import { Link } from 'react-router-dom'
import { assetUrl, formatCount } from '../lib/api'
import type { Scene } from '../lib/api'

/** 来源必须如实区分：自己拍的/自己训的 ≠ 官方示例 ≠ 公开数据集（别人拍的） */
const SOURCE_LABEL: Record<string, string> = {
  'self-trained': '本机自训',
  sample: '官方示例',
  'public-dataset': '公开数据集',
}

/** 「早期实验」的判据用**指标**而不是写死名单：低于这个 PSNR 就标出来。
 *  早期几批是在本机 8GB 显存下做的（渲染分辨率与高斯数都被压住），画质明显弱；
 *  用数据驱动，以后重训改善或新增场景时标记会自动跟着走。 */
const EARLY_EXPERIMENT_PSNR = 20

/** 例外：shoe-clean 是 shoe 的后处理版（同一模型，只做了后处理，PSNR 未重新评估），
 *  因此拿不到上面的指标判据，只能显式列出来 —— 画质与 shoe 同样受限。 */
const EARLY_EXPERIMENT_SLUGS = new Set(['shoe-clean'])

type Props = { scene: Scene }

/** 场景库卡片：缩略图 + 标题 + 方法徽标 + 关键数字。 */
export default function SceneCard({ scene }: Props) {
  const isEarly =
    (scene.psnr != null && scene.psnr < EARLY_EXPERIMENT_PSNR) || EARLY_EXPERIMENT_SLUGS.has(scene.slug)
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
        <h3>
          {scene.title}
          {isEarly && <span className="pill-early">早期实验</span>}
        </h3>
        <p>{scene.summary}</p>
        <dl>
          <div>
            <dt>高斯点</dt>
            <dd>{formatCount(scene.num_points)}</dd>
          </div>
          <div>
            <dt>PSNR</dt>
            <dd>{scene.psnr != null ? scene.psnr.toFixed(2) : '未测'}</dd>
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

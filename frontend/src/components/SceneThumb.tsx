import { assetUrl } from '../lib/api'

/**
 * 场景缩略图：优先 WebP、自动回退原 JPG（由浏览器按 <picture> 自己选）。
 *
 * 为什么这么做（2026-10-14 实测）：
 *   · 同一张缩略图 WebP 比 JPG 小 50–64%（首页三张精选 114.0 KB → 55.3 KB、省 58.7 KB）；
 *   · 源 jpg **一律保留**作为兜底 —— 不支持的旧浏览器会自己回退，数据库、文案、资产管理都不用动；
 *   · 首屏第一张传 priority ⇒ loading=eager + fetchpriority=high，其余懒加载。
 *
 * 故意【不写 width/height 属性】：两处渲染上下文都由 CSS 给了确定高度
 * （首页 .feature img = 152px、场景库 .card-scene .thumb img = 168px + width:100%），
 * 布局在 CSS 到位时就没有位移风险；写死 640×480 反而对 640×328 的官方示例图是假数字 ✗。
 */
export default function SceneThumb({
  src,
  alt,
  priority = false,
}: {
  src: string
  alt: string
  priority?: boolean
}) {
  const webp = src.replace(/\.jpe?g$/i, '.webp')
  return (
    <picture>
      <source srcSet={assetUrl(webp)} type="image/webp" />
      <img
        src={assetUrl(src)}
        alt={alt}
        loading={priority ? 'eager' : 'lazy'}
        fetchPriority={priority ? 'high' : 'auto'}
        decoding="async"
      />
    </picture>
  )
}

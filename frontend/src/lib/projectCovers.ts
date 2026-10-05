/**
 * 程序化封面：按语言取色 + 按仓库名做确定性变化。
 *
 * 为什么不用真实截图/OG 图：
 *  - 116 个仓库逐个抓图要 10–20 分钟，还有一批没有 social preview（会 404）
 *  - GitHub OG 图风格统一、辨识度低，且依赖外网
 * 这里全部离线生成：同名的仓库每次颜色一致（哈希决定），永不 404、零请求。
 */

import type { CSSProperties } from 'react'

/** GitHub linguist 的常用语言色（取其中我们雷达里出现过的） */
const LANG_COLORS: Record<string, string> = {
  Python: '#3572A5',
  'C++': '#f34b7d',
  C: '#8f8f8f',
  'Jupyter Notebook': '#DA5B0B',
  TypeScript: '#3178c6',
  JavaScript: '#f1e05a',
  Rust: '#dea584',
  Cuda: '#4e8a3a',
  'Cuda ': '#4e8a3a',
  TeX: '#3D6117',
  Shell: '#89e051',
  CMake: '#DA3434',
  Lua: '#2f4fa5',
  MATLAB: '#e16737',
  Dockerfile: '#384d54',
  Java: '#b07219',
  Go: '#00ADD8',
  HTML: '#e34c26',
  CSS: '#563d7c',
}

const FALLBACK = '#7a8699'

export function langColor(lang: string | null | undefined): string {
  if (!lang) return FALLBACK
  return LANG_COLORS[lang.trim()] ?? '#5b6b8c'
}

/** FNV-1a：稳定哈希，保证同一仓库每次生成同一张封面 */
function hash(s: string): number {
  let h = 2166136261
  for (let i = 0; i < s.length; i += 1) {
    h ^= s.charCodeAt(i)
    h = Math.imul(h, 16777619)
  }
  return h >>> 0
}

/** 封面上的大字：仓库名首字母（数字/符号开头就用 ◈） */
export function coverGlyph(name: string): string {
  const first = (name || '?').trim().charAt(0).toUpperCase()
  return /[A-Z]/.test(first) ? first : '◈'
}

/**
 * 生成封面的 background 值：
 * 暗底 + 语言色双径向光斑（角度/位置由哈希决定，所以同语言的仓库也不完全一样）
 */
export function coverBackground(fullName: string, lang: string | null): string {
  const h = hash(fullName)
  const deg = 100 + (h % 80) // 100–180 度
  const c = langColor(lang)
  const shift = 20 + (h % 30)
  return [
    `radial-gradient(circle at ${15 + (h % 30)}% 20%, ${c}40, transparent 62%)`,
    `radial-gradient(circle at ${70 + (h % 20)}% 85%, ${c}22, transparent 58%)`,
    `linear-gradient(${deg}deg, hsl(212 ${shift}% 13%), hsl(215 ${shift}% 9%))`,
  ].join(', ')
}

/** 封面的完整内联样式（含细网格底纹） */
export function coverStyle(fullName: string, lang: string | null): CSSProperties {
  const c = langColor(lang)
  return {
    backgroundImage: [
      `repeating-linear-gradient(0deg, ${c}14 0 1px, transparent 1px 22px)`,
      `repeating-linear-gradient(90deg, ${c}14 0 1px, transparent 1px 22px)`,
      coverBackground(fullName, lang),
    ].join(', '),
    backgroundBlendMode: 'overlay, overlay, normal',
  }
}

/** 本地缓存的 GitHub 官方 OG 卡路径（由 frontend/scripts/fetch_covers.py 下载、
 *  compress_covers.py 压成 WebP）。文件不存在时 <img> 触发 onError，
 *  前端自动回退到上面的程序化封面。 */
export function coverUrl(owner: string, name: string): string {
  return `${import.meta.env.BASE_URL}covers/${owner}-${name}.webp`
}

/** 「我读过 / 星速爆发」这类角标的样式配色 */
export function badgeStyle(kind: 'picked' | 'hot'): CSSProperties {
  if (kind === 'picked') {
    return { color: '#6ee7bb', borderColor: '#6ee7bb55', background: '#6ee7bb14' }
  }
  return { color: '#f0b46a', borderColor: '#f0b46a55', background: '#f0b46a14' }
}

/**
 * 离线诊断 .spz：不解码到 GPU，只用 PackedSplats 读点位，回答
 * 「这个文件里到底有没有有效的高斯中心」。
 *
 *   node scripts/inspect_spz.mjs ../public/demo/snow-street.spz
 *
 * 起因：snow-street.spz 在浏览器里 status=ready、numSplats=981908，但
 * getBoundingBox() 返回空盒（±Infinity）且画面全黑。把「解析」和「渲染」
 * 分开看，才能判断是文件本身的问题还是渲染管线的问题。
 */

import { readFileSync } from 'node:fs'
import { PackedSplats } from '@sparkjsdev/spark'

const path = process.argv[2]
if (!path) {
  console.error('用法：node scripts/inspect_spz.mjs <file.spz>')
  process.exit(2)
}

const bytes = new Uint8Array(readFileSync(path))
console.log(`文件：${path}  ${(bytes.byteLength / 1024 / 1024).toFixed(2)} MB`)

const packed = new PackedSplats({ fileBytes: bytes })
await packed.initialized
console.log(`numSplats（解析结果）：${packed.numSplats}`)

const min = [Infinity, Infinity, Infinity]
const max = [-Infinity, -Infinity, -Infinity]
let nonFinite = 0
let opaque = 0
let sumOpacity = 0
let scaleSum = 0
let n = 0

packed.forEachSplat((_i, center, scales, _quat, opacity) => {
  n += 1
  for (let a = 0; a < 3; a += 1) {
    const v = center.getComponent(a)
    if (!Number.isFinite(v)) {
      nonFinite += 1
      continue
    }
    if (v < min[a]) min[a] = v
    if (v > max[a]) max[a] = v
  }
  sumOpacity += opacity
  if (opacity > 0.5) opaque += 1
  scaleSum += (scales.x + scales.y + scales.z) / 3
})

const size = max.map((v, i) => v - min[i])
console.log(`遍历 splat：${n}`)
console.log(`非有限坐标分量：${nonFinite}`)
console.log(`bbox min：${min.map((v) => v.toFixed(3)).join(', ')}`)
console.log(`bbox max：${max.map((v) => v.toFixed(3)).join(', ')}`)
console.log(`bbox size：${size.map((v) => (Number.isFinite(v) ? v.toFixed(3) : String(v))).join(', ')}`)
console.log(`平均不透明度：${(sumOpacity / Math.max(n, 1)).toFixed(4)}  不透明点(>0.5)：${opaque}`)
console.log(`平均尺度：${(scaleSum / Math.max(n, 1)).toExponential(3)}`)
console.log(
  `结论：${nonFinite > 0 ? '文件含非有限坐标（数据/解码问题）' : size.every((v) => Number.isFinite(v) && v > 0) ? '数据有效' : '数据退化'}`,
)

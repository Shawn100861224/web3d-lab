/**
 * ply2spz.mjs —— 把 3DGS PLY 转成 spark 原生的 .spz（用 spark 自己的 transcodeSpz）。
 *
 * 为什么要它：官方示例（.spz）在同一个查看器里非常清晰，而本项目自训资产用 .splat
 * 在查看器里像一团发光碎片 —— 怀疑 .splat 这条通道对 scale/opacity 的解释与我们的导出约定不一致。
 * 用 spark 自己的写入器产出 .spz 即可 A/B 对照。
 *
 * 用法： node scripts/ply2spz.mjs <in.ply> <out.spz> [maxSh] [fractionalBits] [opacityThreshold]
 */
import fs from 'node:fs'
import { transcodeSpz } from '@sparkjsdev/spark'

const [, , src, dst, maxShArg, fbArg, opArg] = process.argv
if (!src || !dst) {
  console.error('用法：node scripts/ply2spz.mjs <in.ply> <out.spz> [maxSh=0] [fractionalBits=12] [opacityThreshold=0.02]')
  process.exit(2)
}
const maxSh = maxShArg === undefined ? 0 : Number(maxShArg)
const fractionalBits = fbArg === undefined ? 12 : Number(fbArg)
const opacityThreshold = opArg === undefined ? 0.02 : Number(opArg)

const bytes = new Uint8Array(fs.readFileSync(src))
console.log(`输入 ${src}：${(bytes.length / 1048576).toFixed(2)} MB`)

const t0 = Date.now()
const { fileBytes, clippedCount } = await transcodeSpz({
  inputs: [{ fileBytes: bytes, fileType: 'ply', pathOrUrl: src }],
  maxSh,
  fractionalBits,
  opacityThreshold,
  version: 2,
})
fs.writeFileSync(dst, Buffer.from(fileBytes))
console.log(`✅ ${dst}：${(fileBytes.length / 1048576).toFixed(2)} MB | clipped=${clippedCount} | ${Date.now() - t0}ms`)

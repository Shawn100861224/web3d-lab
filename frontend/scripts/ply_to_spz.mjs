#!/usr/bin/env node
/**
 * ply_to_spz.mjs —— 用 spark 自带的 transcodeSpz 把 .splat/.ply 转成 .spz（官方示例用的原生格式）。
 *
 *   node scripts/ply_to_spz.mjs <输入 .splat|.ply> <输出 .spz> [fractionalBits]
 *
 * 目的：同一份权重，换个容器格式进查看器，用来看清「画质差」到底是模型的锅还是 .splat 通道的锅。
 */
import fs from 'node:fs'
import path from 'node:path'
import { transcodeSpz } from '@sparkjsdev/spark'

const [inPath, outPath, fbRaw] = process.argv.slice(2)
if (!inPath || !outPath) {
  console.error('用法: node scripts/ply_to_spz.mjs <in.splat|in.ply> <out.spz> [fractionalBits] [maxSh] [opacityThreshold]')
  process.exit(2)
}
const fractionalBits = fbRaw ? Number(fbRaw) : 12
const maxSh = process.argv[5] !== undefined ? Number(process.argv[5]) : undefined
const opacityThreshold = process.argv[6] !== undefined ? Number(process.argv[6]) : undefined
const ext = path.extname(inPath).slice(1).toLowerCase()
const fileType = ext === 'ply' ? 'ply' : 'splat'

const bytes = new Uint8Array(fs.readFileSync(inPath))
const t0 = Date.now()
const { fileBytes, clippedCount } = await transcodeSpz({
  inputs: [{ fileBytes: bytes, fileType }],
  fractionalBits,
  ...(maxSh !== undefined ? { maxSh } : {}),
  ...(opacityThreshold !== undefined ? { opacityThreshold } : {}),
})
fs.writeFileSync(outPath, Buffer.from(fileBytes))
console.log(
  `✅ ${inPath} (${fileType}, ${(bytes.length / 1048576).toFixed(2)} MB) -> ${outPath} ` +
  `(${(fileBytes.length / 1048576).toFixed(2)} MB) | fractionalBits=${fractionalBits} | ` +
  `maxSh=${maxSh ?? '(默认)'} | 不透明度阈值=${opacityThreshold ?? '(默认)'} | ` +
  `裁剪点数=${clippedCount ?? 0} | ${Date.now() - t0} ms`,
)

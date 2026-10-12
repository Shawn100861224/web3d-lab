#!/usr/bin/env node
/**
 * splat_to_spz_v3.mjs —— 同 ply_to_spz.mjs，但可指定 SPZ 写入版本。
 *
 * 起因：EdgeOne Makers 有「单文件 25 MB」硬限制（官方排障指南/配额页），
 * 而 garden 的 3.65M 高斯按默认 v2 写出来是 50 MB。v3 布局更紧凑，先试它。
 *
 *   node scripts/splat_to_spz_v3.mjs <in.splat> <out.spz> [fractionalBits] [version]
 */
import fs from 'node:fs'
import { transcodeSpz } from '@sparkjsdev/spark'

const [inPath, outPath, fbRaw, verRaw] = process.argv.slice(2)
if (!inPath || !outPath) {
  console.error('用法: node scripts/splat_to_spz_v3.mjs <in.splat> <out.spz> [fractionalBits] [version]')
  process.exit(2)
}
const fractionalBits = fbRaw ? Number(fbRaw) : 12
const version = verRaw ? Number(verRaw) : 3

const bytes = new Uint8Array(fs.readFileSync(inPath))
const t0 = Date.now()
const { fileBytes, clippedCount } = await transcodeSpz({
  inputs: [{ fileBytes: bytes, fileType: 'splat' }],
  fractionalBits,
  version,
})
fs.writeFileSync(outPath, Buffer.from(fileBytes))
console.log(
  `✅ ${inPath} (${(bytes.length / 1048576).toFixed(2)} MB) -> ${outPath} (${(fileBytes.length / 1048576).toFixed(2)} MB) ` +
    `| fractionalBits=${fractionalBits} | version=${version} | 裁剪点数=${clippedCount ?? 0} | ${Date.now() - t0} ms`,
)

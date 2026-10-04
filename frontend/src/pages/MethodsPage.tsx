import { useEffect } from 'react'
import { trackEvent } from '../lib/api'

/**
 * /methods —— 3DGS 方法对比页。
 *
 * 这张表不是抄来的宣传语：每一行的「与我有关」列写的都是「对我这台 8GB 显存笔记本意味着什么」，
 * 而 3DGS 那一行的数字（45,401 点 / 526ms 加载 / 76–147 FPS）是本站查看器的实测值。
 */

type Method = {
  name: string
  venue: string
  primitive: string
  surface: string
  scale: string
  speed: string
  compression: string
  open: string
  mine: string
}

const METHODS: Method[] = [
  {
    name: '3DGS',
    venue: "SIGGRAPH'23",
    primitive: '3D 各向异性高斯（μ, Σ, α, SH）',
    surface: '弱（点云似的，表面发毛）',
    scale: '单物体 ~ 房间',
    speed: '实时（本机实测 76–147 FPS / 4.5 万点）',
    compression: '原始 .ply 大，导出 .spz 可压',
    open: '官方 CUDA 实现 + gsplat（PyTorch）',
    mine: '本站查看器的基线：45,401 点加载 526ms。这是我动手的起点。',
  },
  {
    name: 'Mip-Splatting',
    venue: "CVPR'24 最佳学生论文",
    primitive: '3D 高斯 + Mip 滤波（3D 平滑 + 2D Mip）',
    surface: '同 3DGS',
    scale: '同 3DGS',
    speed: '与 3DGS 相近',
    compression: '同 3DGS',
    open: '官方仓库开源',
    mine: '解决「拉远/近距离闪烁」。我拍的桌面场景如果分辨率变化大，会先试它。',
  },
  {
    name: '2DGS',
    venue: "SIGGRAPH'24",
    primitive: '2D 圆盘（带法向）',
    surface: '好（有明确表面）',
    scale: '单物体 ~ 房间',
    speed: '实时',
    compression: '同量级',
    open: '官方开源 + 被 nerfstudio 生态吸收',
    mine: '如果队友要网格（mesh）而不是点云，这个更合适——机器人抓取需要表面。',
  },
  {
    name: 'SuGaR / PGSR',
    venue: "CVPR'24 / TVCG'24",
    primitive: '3D 高斯 + 表面对齐 / 平面正则',
    surface: 'PGSR 目前最深（无偏深度渲染）',
    scale: '房间级',
    speed: '训练更慢，渲染实时',
    compression: '附带 mesh 导出',
    open: '官方开源',
    mine: '「从照片到网格」这条线的当前答案；模块 8 若要做 mesh 导出的对照，选它。',
  },
  {
    name: 'Scaffold-GS / CityGaussian',
    venue: "ICCV'23 / ECCV'24",
    primitive: '锚点 + 局部高斯 / 分层 LOD',
    surface: '中（偏渲染）',
    scale: '建筑 ~ 城市',
    speed: '按需 LOD，大场景可交互',
    compression: '锚点天然压缩',
    open: '官方开源',
    mine: '我 8GB 显存跑不了城市级，但「锚点 + LOD」的思路和浏览器端的 LOD 是一回事。',
  },
  {
    name: '前馈类（MVSplat / GS-LRM / AnySplat）',
    venue: "ECCV'24 / SIGGRAPH'25 等",
    primitive: '网络一次前向直接吐高斯',
    surface: '中',
    scale: '稀疏视角、单次前向',
    speed: '免优化，秒级出结果',
    compression: '输出点数可控',
    open: '多数开源',
    mine: '和「自己训几十分钟」是两条路。要在网页上做「上传即看」，这类才有戏；我现在的管线是训练式的。',
  },
  {
    name: '压缩类（Compact-3DGS / HAC / NanoGS）',
    venue: "CVPR'24 / arXiv'26",
    primitive: '同 3DGS（改的是编码与剪枝）',
    surface: '同 3DGS',
    scale: '同 3DGS',
    speed: '解码后更快',
    compression: '10–1000 倍（HAC ~100x，MobileGS 50–100x）',
    open: '多数开源',
    mine: '直接决定网页首屏：我现在的示例是 1.1–7.8MB 的 .spz，压缩类方法就是「能不能秒开」的关键。',
  },
  {
    name: '3DGS-SLAM 系列',
    venue: "CVPR'24 亮点 起",
    primitive: '3D 高斯 + 在线位姿估计',
    surface: '中',
    scale: '房间级（在线）',
    speed: '在线建图 + 渲染',
    compression: 'N/A',
    open: '多方开源',
    mine: '这是「机器人上的 3DGS」入口：边跑边建图。也是我理解「视觉做状态估计」的具体例子。',
  },
  {
    name: '几何大模型（DUSt3R / VGGT）',
    venue: "CVPR'24 / ICCV'25",
    primitive: '点图（pointmap）直接回归',
    surface: '中～好',
    scale: '任意张图，免标定',
    speed: '秒级推理',
    compression: 'N/A',
    open: '官方开源（含权重）',
    mine: '最省事的一条：不用 COLMAP 就能拿到点云与位姿。是我下一个要试的实验。',
  },
]

const DIMENSIONS = [
  '几何基元',
  '表面质量',
  '可扩展规模',
  '速度',
  '压缩/体积',
  '开源情况',
  '为什么和我有关',
]

export default function MethodsPage() {
  useEffect(() => {
    trackEvent('view', '/methods')
  }, [])

  return (
    <section className="library">
      <header className="page-head">
        <h1>3DGS 方法对比</h1>
        <p>
          三维高斯泼溅是一个还在快速分叉的家族。这张表按「几何基元 → 表面质量 → 规模 → 速度 →
          体积 → 开源 → 对我意味着什么」七个维度横向对比九类方法；
          最后一列是我挑它们的理由，不是官方宣传语。
        </p>
      </header>

      <div className="table-wrap">
        <table className="cmp" id="methods-table">
          <thead>
            <tr>
              <th>方法</th>
              {DIMENSIONS.map((d) => (
                <th key={d}>{d}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {METHODS.map((m) => (
              <tr key={m.name}>
                <th scope="row">
                  <b>{m.name}</b>
                  <span className="venue">{m.venue}</span>
                </th>
                <td>{m.primitive}</td>
                <td>{m.surface}</td>
                <td>{m.scale}</td>
                <td>{m.speed}</td>
                <td>{m.compression}</td>
                <td>{m.open}</td>
                <td className="mine">{m.mine}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <h2 className="section-title">我怎么用这张表</h2>
      <ul className="clean">
        <li>
          <b>先把基线跑稳：</b>3DGS 是所有人的对照组，本站查看器用的就是它导出的 .spz。
        </li>
        <li>
          <b>按「下一步要什么」选：</b>要网格 → 2DGS / PGSR；要秒开 → 压缩类；
          要免标定 → DUSt3R / VGGT；要在机器人上边跑边建图 → 3DGS-SLAM。
        </li>
        <li>
          <b>承认约束：</b>这台笔记本是 8GB 显存，所以城市级方法（Scaffold-GS+、CityGaussian）
          我只读论文和代码结构，不做复现——那是我换机器之后的事。
        </li>
      </ul>
      <p className="note">
        表内方法信息来自各论文与官方仓库（截至 2026-10），数字如需引用请以原文为准；
        只有「本机实测」那几项是这台笔记本上跑出来的。
      </p>
    </section>
  )
}

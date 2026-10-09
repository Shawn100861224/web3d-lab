import Sparkline from './Sparkline'
import type { Scene } from '../lib/api'
import { formatBytes, formatCount, formatDuration } from '../lib/api'
import type { ViewerStats } from './SplatViewer'

type Props = {
  scene: Scene | null
  live: ViewerStats
  /** 帧率采样历史（最近 ~20 秒），用于画实时性能曲线 */
  fpsHistory?: number[]
}

function Row({ label, value, hint }: { label: string; value: string; hint?: string }) {
  return (
    <div className="row">
      <dt>{label}</dt>
      <dd>
        {value}
        {hint && <span className="hint">{hint}</span>}
      </dd>
    </div>
  )
}

/**
 * 指标面板：左边是「元数据里声明的」（训练时回写），右边是「浏览器里实测的」。
 * 两组分开列，是为了让访客一眼看出哪些数字来自训练、哪些来自本次渲染。
 */
export default function MetricsPanel({ scene, live, fpsHistory = [] }: Props) {
  const declared = scene
  const isPlaceholder = declared?.source === 'sample' || declared?.source === 'public-dataset'
  const sourceNote =
    declared?.source === 'public-dataset'
      ? '该场景来自公开数据集（Mip-NeRF 360），非本人拍摄，仅用于验证真实照片重建链路。'
      : '该场景是上游官方示例，指标由来源方提供，非本人训练。'

  return (
    <aside className="panel">
      <div className="panel-block">
        <h2>
          训练指标
          {isPlaceholder && (
            <span className="badge">
              {declared?.source === 'public-dataset' ? '公开数据集' : '示例资产'}
            </span>
          )}
        </h2>
        {isPlaceholder && <p className="note">{sourceNote}</p>}
        <dl>
          <Row label="方法" value={declared?.technique ?? '—'} />
          <Row
            label="PSNR"
            value={declared?.psnr != null ? declared.psnr.toFixed(2) : '—'}
            hint={declared?.psnr == null ? '未测' : 'dB'}
          />
          <Row
            label="SSIM"
            value={declared?.ssim != null ? declared.ssim.toFixed(4) : '—'}
            hint={declared?.ssim == null ? '未测' : undefined}
          />
          <Row
            label="LPIPS"
            value={declared?.lpips != null ? declared.lpips.toFixed(4) : '—'}
            hint={declared?.lpips == null ? '未测' : undefined}
          />
          <Row label="迭代步数" value={formatCount(declared?.iterations ?? null)} />
          <Row label="训练耗时" value={formatDuration(declared?.train_seconds ?? null)} />
          <Row
            label="训练显存"
            value={declared?.gpu_mem_mb != null ? `${declared.gpu_mem_mb} MB` : '—'}
          />
          <Row
            label="高斯点数"
            value={formatCount(declared?.num_points ?? null)}
            hint={declared?.num_points == null ? undefined : '资产内'}
          />
          <Row label="球谐阶数" value={declared?.sh_degree != null ? `SH${declared.sh_degree}` : '—'} />
          <Row label="采集设备" value={declared?.capture_device ?? '—'} />
          <Row
            label="采集视角"
            value={declared?.capture_views != null ? `${declared.capture_views} 张` : '—'}
          />
        </dl>
      </div>

      <div className="panel-block">
        <h2>本次渲染实测</h2>
        <dl>
          <Row
            label="状态"
            value={
              live.status === 'ready' ? '渲染中' : live.status === 'loading' ? '加载中' : '加载失败'
            }
          />
          <Row
            label="实际高斯数"
            value={live.numSplats ? live.numSplats.toLocaleString('zh-CN') : '—'}
            hint={live.numSplats ? '从文件解析' : undefined}
          />
          <Row label="资产体积" value={formatBytes(live.bytes)} />
          <Row label="加载耗时" value={live.loadMs ? `${live.loadMs} ms` : '—'} />
          <Row label="帧率" value={live.fps ? `${live.fps} FPS` : '—'} />
          <Row
            label="相机位置"
            value={live.camera.every((v) => v === 0) ? '—' : live.camera.map((v) => v.toFixed(2)).join(' / ')}
            hint="拖拽后会变"
          />
          <Row
            label="场景半径"
            value={live.extent ? live.extent.toFixed(2) : '—'}
            hint={live.status === 'ready' && !live.extent ? 'bbox 退化，用兜底机位' : '世界单位'}
          />
        </dl>

        {fpsHistory.length > 2 && (
          <div className="fps-chart">
            <span className="label">帧率走势（最近 20 秒）</span>
            <Sparkline values={fpsHistory} height={44} />
          </div>
        )}

        {live.error && <p className="note note--bad">错误：{live.error}</p>}
      </div>

      <div className="panel-block">
        <h2>资产与许可</h2>
        <dl>
          <Row label="文件" value={declared?.asset_url ?? '—'} />
          <Row label="格式" value={declared?.asset_format ?? '—'} />
          <Row label="许可" value={declared?.license ?? '—'} />
        </dl>
      </div>
    </aside>
  )
}

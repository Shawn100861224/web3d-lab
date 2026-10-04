import { useEffect, useRef } from 'react'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark'

export type ViewerStatus = 'loading' | 'ready' | 'error'

export type ViewerStats = {
  status: ViewerStatus
  progress: number // 0..1
  numSplats: number
  fps: number
  loadMs: number
  bytes: number
  /** 相机世界坐标，用来验证「拖拽/巡航真的在动」 */
  camera: [number, number, number]
  /** 场景包围球半径（世界单位），0 表示 bbox 退化、用了兜底机位 */
  extent: number
  /** 原始 bbox 尺寸与中心，用于诊断「解析成功但画面全空」 */
  bbox: [number, number, number, number, number, number]
  error: string | null
}

type Props = {
  /** .spz/.splat/.ply 资产地址（同源，放在 public/demo/ 下） */
  url: string
  autoRotate?: boolean
  /** 自动巡航的角速度（弧度/秒），0 表示关闭 */
  rotateSpeed?: number
  onStats?: (stats: ViewerStats) => void
  className?: string
}

/**
 * 3DGS 查看器。Spark 负责高斯泼溅的排序与光栅化，OrbitControls 负责轨道漫游。
 *
 * 为什么用 OrbitControls 而不是 Spark 自带的 SparkControls：考核作品的交互是
 * 「围着物体转一圈看重建质量」，轨道相机比第一人称自由飞更直观；SparkControls
 * 留作模块 4 的「自由漫游」切换项。
 *
 * 自动化验收钩子：状态会同步到 `window.__web3dViewer`（含 status/numSplats/fps），
 * 供 Playwright 与脚本断言，不要当成业务状态源。
 */
export default function SplatViewer({
  url,
  autoRotate = false,
  rotateSpeed = 0.6,
  onStats,
  className,
}: Props) {
  const hostRef = useRef<HTMLDivElement>(null)
  const statsRef = useRef<ViewerStats>({
    status: 'loading',
    progress: 0,
    numSplats: 0,
    fps: 0,
    loadMs: 0,
    bytes: 0,
    camera: [0, 0, 0],
    extent: 0,
    bbox: [0, 0, 0, 0, 0, 0],
    error: null,
  })
  const onStatsRef = useRef(onStats)
  onStatsRef.current = onStats

  useEffect(() => {
    const host = hostRef.current
    if (!host) return

    const push = (patch: Partial<ViewerStats>) => {
      statsRef.current = { ...statsRef.current, ...patch }
      const snapshot = statsRef.current
      ;(window as unknown as { __web3dViewer?: ViewerStats }).__web3dViewer = snapshot
      onStatsRef.current?.(snapshot)
    }

    push({ status: 'loading', progress: 0, numSplats: 0, fps: 0, error: null })

    const scene = new THREE.Scene()
    scene.background = null

    const camera = new THREE.PerspectiveCamera(55, 1, 0.01, 5000)
    camera.position.set(0, 0.5, 3)

    const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true })
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
    renderer.setClearColor(0x0d0f13, 0)
    host.appendChild(renderer.domElement)
    renderer.domElement.style.display = 'block'
    renderer.domElement.style.width = '100%'
    renderer.domElement.style.height = '100%'
    renderer.domElement.style.touchAction = 'none'

    const spark = new SparkRenderer({ renderer })
    scene.add(spark)

    const controls = new OrbitControls(camera, renderer.domElement)
    controls.enableDamping = true
    controls.dampingFactor = 0.08
    controls.autoRotate = autoRotate
    controls.autoRotateSpeed = rotateSpeed
    controls.screenSpacePanning = true

    const startedAt = performance.now()
    let disposed = false
    let splat: SplatMesh | null = null

    splat = new SplatMesh({
      url,
      onProgress: (event: ProgressEvent) => {
        if (disposed) return
        const total = event.total || 0
        const progress = total > 0 ? Math.min(1, event.loaded / total) : 0
        push({ progress, bytes: event.loaded })
      },
    })
    scene.add(splat)

    splat.initialized
      .then((mesh) => {
        if (disposed) return
        // 资产来自 OpenCV 坐标系（+Y 向下），绕 X 轴翻 180° 才正立
        mesh.quaternion.set(1, 0, 0, 0)

        const box = mesh.getBoundingBox()
        const size = new THREE.Vector3()
        const center = new THREE.Vector3()
        box.getSize(size)
        box.getCenter(center)

        // 场景级点云偶尔给出退化 bbox（空盒 → ±Infinity，或个别 NaN 中心），
        // 直接除下去会把相机算成 NaN、画面全空。退化时退回到「以原点为中心、
        // 半径 1」的兜底机位，至少保证有东西可看，再由用户自己缩放。
        const rawRadius = size.length() / 2
        const usable =
          Number.isFinite(rawRadius) &&
          rawRadius > 1e-6 &&
          Number.isFinite(center.x) &&
          Number.isFinite(center.y) &&
          Number.isFinite(center.z)
        if (!usable) {
          center.set(0, 0, 0)
          size.set(2, 2, 2)
        }
        const radius = usable ? rawRadius : 1

        // 按「视口宽高比 + 包围盒半宽/半高」分别算需要的距离，取较远的那一个。
        // 用包围球直径会让又大又扁的场景（如 916×342×415 的山谷）在画幅里只占一个小点。
        const aspect = Math.max(host.clientWidth, 1) / Math.max(host.clientHeight, 1)
        const tanV = Math.tan(((camera.fov * Math.PI) / 180) / 2)
        const tanH = tanV * aspect
        const minHalf = radius * 0.05
        const distV = Math.max(size.y / 2, minHalf) / tanV
        const distH = Math.max(size.x / 2, minHalf) / tanH
        const distance = Math.max(distV, distH, minHalf) * 1.2

        controls.target.copy(center)
        camera.position.copy(center).add(new THREE.Vector3(0, 0, distance))
        camera.near = Math.max(distance / 1000, 0.001)
        camera.far = distance + radius * 4
        camera.updateProjectionMatrix()
        controls.update()

        push({
          status: 'ready',
          progress: 1,
          numSplats: mesh.numSplats,
          loadMs: Math.round(performance.now() - startedAt),
          bytes: statsRef.current.bytes,
          extent: usable ? rawRadius : 0,
          bbox: [size.x, size.y, size.z, center.x, center.y, center.z],
          error: null,
        })
      })
      .catch((err: unknown) => {
        if (disposed) return
        push({
          status: 'error',
          error: err instanceof Error ? err.message : String(err),
        })
      })

    const resize = () => {
      const w = host.clientWidth || 1
      const h = host.clientHeight || 1
      renderer.setSize(w, h, false)
      camera.aspect = w / h
      camera.updateProjectionMatrix()
    }
    resize()
    const ro = new ResizeObserver(resize)
    ro.observe(host)

    // 帧率统计：每 500ms 汇总一次，避免每帧触发 React setState
    let frames = 0
    let lastSample = performance.now()
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    if (reduceMotion) controls.autoRotate = false

    renderer.setAnimationLoop(() => {
      controls.update()
      renderer.render(scene, camera)
      if (statsRef.current.status !== 'ready') return
      frames += 1
      const now = performance.now()
      if (now - lastSample >= 500) {
        const fps = Math.round((frames * 1000) / (now - lastSample))
        frames = 0
        lastSample = now
        push({
          fps,
          camera: [camera.position.x, camera.position.y, camera.position.z],
        })
      }
    })

    return () => {
      disposed = true
      renderer.setAnimationLoop(null)
      ro.disconnect()
      controls.dispose()
      splat?.dispose()
      renderer.dispose()
      renderer.domElement.remove()
      ;(window as unknown as { __web3dViewer?: ViewerStats }).__web3dViewer = undefined
    }
  }, [url, autoRotate, rotateSpeed])

  return <div ref={hostRef} className={className} style={{ width: '100%', height: '100%' }} />
}

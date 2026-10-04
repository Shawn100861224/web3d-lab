import { useEffect, useState } from 'react'
import { backendMode, onBackendStatus, probeBackend } from './api'

export type BackendMode = 'unknown' | 'online' | 'offline'

/**
 * 后端可用性 hook：应用启动探测一次，之后跟着每次接口调用的结果更新。
 * 页面用它决定「显示真数据」还是「显示静态兜底 + 一行说明」。
 */
export function useBackend(probe = false): BackendMode {
  const [mode, setMode] = useState<BackendMode>(backendMode())

  useEffect(() => {
    const off = onBackendStatus(() => setMode(backendMode()))
    if (probe) void probeBackend()
    return () => {
      off()
    }
  }, [probe])

  return mode
}

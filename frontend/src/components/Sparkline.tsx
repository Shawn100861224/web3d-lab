type Props = {
  values: number[]
  labels?: string[]
  width?: number
  height?: number
}

/**
 * 极简日访问曲线（纯 SVG，不引图表库）。
 * 14 天全为 0 时显示一条基线，避免出现空坐标轴。
 */
export default function Sparkline({ values, labels = [], width = 420, height = 72 }: Props) {
  const max = Math.max(1, ...values)
  const step = values.length > 1 ? width / (values.length - 1) : width
  const y = (v: number) => height - 12 - (v / max) * (height - 24)

  const points = values.map((v, i) => [i * step, y(v)] as const)
  const line = points.map(([px, py]) => `${px.toFixed(1)},${py.toFixed(1)}`).join(' ')
  const area = `0,${height - 12} ${line} ${width},${height - 12}`

  return (
    <svg
      className="spark"
      viewBox={`0 0 ${width} ${height}`}
      width="100%"
      height={height}
      role="img"
      aria-label={`最近 ${values.length} 天访问量，共 ${values.reduce((a, b) => a + b, 0)} 次`}
      data-spark-total={values.reduce((a, b) => a + b, 0)}
    >
      <polygon points={area} fill="rgba(98,208,255,0.12)" />
      <polyline points={line} fill="none" stroke="#62d0ff" strokeWidth="2" />
      {points.map(([px, py], i) =>
        values[i] > 0 ? <circle key={i} cx={px} cy={py} r="2.5" fill="#62d0ff" /> : null,
      )}
      {labels.map((label, i) => (
        <text key={label} x={i * step} y={height - 1} fontSize="9" fill="#8a93a5" textAnchor="middle">
          {label}
        </text>
      ))}
    </svg>
  )
}

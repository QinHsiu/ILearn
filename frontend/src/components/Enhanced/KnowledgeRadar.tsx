import { useMemo } from 'react'
import styles from './enhanced.module.css'

interface KnowledgeRadarProps {
  knowledgeMastery: Record<string, number>
  maxItems?: number
  size?: number
}

function truncateLabel(name: string): string {
  return name.length > 6 ? `${name.slice(0, 6)}…` : name
}

export function KnowledgeRadar({
  knowledgeMastery,
  maxItems = 8,
  size = 220,
}: KnowledgeRadarProps) {
  const data = useMemo(() => {
    const entries = Object.entries(knowledgeMastery || {})
    entries.sort((a, b) => a[1] - b[1])
    return entries.slice(0, maxItems)
  }, [knowledgeMastery, maxItems])

  if (data.length < 3) {
    return (
      <div className={styles.radarFallback} style={{ height: size }}>
        数据不足，暂无法绘制（需至少 3 个知识点）
      </div>
    )
  }

  const cx = size / 2
  const cy = size / 2
  const maxR = size * 0.34
  const n = data.length

  const pointAt = (i: number, value: number) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2
    const clamped = Math.max(0, Math.min(1, value))
    const r = maxR * clamped
    return {
      x: cx + r * Math.cos(angle),
      y: cy + r * Math.sin(angle),
    }
  }

  const dataPoints = data
    .map(([, v], i) => {
      const p = pointAt(i, v)
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
    })
    .join(' ')

  const gridLevels = [0.25, 0.5, 0.75, 1.0]
  const gridPolygons = gridLevels.map((level) =>
    Array.from({ length: n }, (_, i) => {
      const p = pointAt(i, level)
      return `${p.x.toFixed(1)},${p.y.toFixed(1)}`
    }).join(' '),
  )

  const axes = Array.from({ length: n }, (_, i) => pointAt(i, 1.0))

  const labels = data.map(([name], i) => {
    const p = pointAt(i, 1.18)
    return { name: truncateLabel(name), fullName: name, x: p.x, y: p.y }
  })

  return (
    <svg
      viewBox={`0 0 ${size} ${size}`}
      width="100%"
      height={size}
      role="img"
      aria-label="知识点掌握度雷达图"
    >
      {gridPolygons.map((pts, i) => (
        <polygon
          key={`grid-${i}`}
          points={pts}
          fill="none"
          stroke="#e5e7eb"
          strokeWidth={1}
        />
      ))}

      {axes.map((p, i) => (
        <line
          key={`axis-${i}`}
          x1={cx}
          y1={cy}
          x2={p.x}
          y2={p.y}
          stroke="#e5e7eb"
          strokeWidth={1}
        />
      ))}

      <polygon
        points={dataPoints}
        fill="rgba(66,133,244,0.22)"
        stroke="#4285f4"
        strokeWidth={2}
      />

      {data.map(([name, v], i) => {
        const p = pointAt(i, v)
        return (
          <g key={`pt-${i}`}>
            <circle cx={p.x} cy={p.y} r={3} fill="#4285f4">
              <title>
                {name}: {Math.round(v * 100)}%
              </title>
            </circle>
          </g>
        )
      })}

      {labels.map((l, i) => (
        <text
          key={`label-${i}`}
          x={l.x}
          y={l.y}
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={10}
          fill="#6b7280"
        >
          {l.name}
          <title>{l.fullName}</title>
        </text>
      ))}
    </svg>
  )
}

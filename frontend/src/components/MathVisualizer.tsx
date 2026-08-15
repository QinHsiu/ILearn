import type { VisualizationSpec } from '../lib/inferVisualization'

type MathVisualizerProps = {
  spec: VisualizationSpec
}

export default function MathVisualizer({ spec }: MathVisualizerProps) {
  const { type, data } = spec
  if (type === 'none' || !data) return null

  if (type === 'fraction') {
    const numerator = Number(data.numerator)
    const denominator = Number(data.denominator)
    if (!denominator) return null
    const percentage = Math.min(1, Math.max(0, numerator / denominator))
    const radius = 45
    const circumference = 2 * Math.PI * radius
    const offset = circumference * (1 - percentage)
    const label = String(data.label || `${numerator}/${denominator}`)

    return (
      <div className="math-visual math-visual-fraction">
        <svg width="120" height="120" viewBox="0 0 120 120" aria-hidden>
          <circle cx="60" cy="60" r={radius} fill="#f0f0f0" stroke="#ddd" strokeWidth="5" />
          <circle
            className="math-visual-arc"
            cx="60"
            cy="60"
            r={radius}
            fill="transparent"
            strokeWidth="20"
            strokeDasharray={circumference}
            strokeDashoffset={offset}
            strokeLinecap="round"
            transform="rotate(-90 60 60)"
          />
          <text x="60" y="65" textAnchor="middle" fontSize="18" fontWeight="700">
            {label}
          </text>
        </svg>
        <span className="math-visual-caption">{label}</span>
      </div>
    )
  }

  if (type === 'bar_chart') {
    const items = (data.items as Array<{ label: string; value: number }>) || []
    if (!items.length) return null
    const max = Math.max(...items.map((item) => item.value), 1)
    return (
      <div className="math-visual math-visual-bars">
        {items.map((item) => {
          const height = (item.value / max) * 80 + 20
          return (
            <div className="math-visual-bar" key={item.label}>
              <div className="math-visual-bar-fill" style={{ height }} />
              <span>{item.label}</span>
              <strong>{item.value}</strong>
            </div>
          )
        })}
      </div>
    )
  }

  if (type === 'number_line') {
    const min = Number(data.min)
    const max = Number(data.max)
    const marks = (data.marks as Array<{ position: number; label: string }>) || []
    const span = max - min || 1
    return (
      <svg
        className="math-visual math-visual-line"
        width="100%"
        height="60"
        viewBox="0 0 300 60"
        aria-hidden
      >
        <line x1="20" y1="30" x2="280" y2="30" stroke="currentColor" strokeWidth="3" />
        {marks.map((mark) => {
          const x = 20 + ((mark.position - min) / span) * 260
          return (
            <g key={`${mark.position}-${mark.label}`}>
              <line x1={x} y1="25" x2={x} y2="35" stroke="currentColor" strokeWidth="2" />
              <text x={x} y="50" textAnchor="middle" fontSize="14">
                {mark.label}
              </text>
            </g>
          )
        })}
      </svg>
    )
  }

  return null
}

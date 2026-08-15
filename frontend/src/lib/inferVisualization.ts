export type VisualizationType =
  | 'fraction'
  | 'number_line'
  | 'bar_chart'
  | 'geometry'
  | 'none'

export type VisualizationSpec = {
  type: VisualizationType
  data: Record<string, unknown> | null
}

const FRACTION_RE = /(\d+)\s*\/\s*(\d+)/

/** Heuristic visualization from stem text; falls back to none. */
export function inferVisualization(stem: string): VisualizationSpec {
  const text = stem.trim()
  if (!text) return { type: 'none', data: null }

  const fraction = text.match(FRACTION_RE)
  if (fraction && /分数|平均分|几分之/.test(text)) {
    const numerator = Number(fraction[1])
    const denominator = Number(fraction[2])
    if (denominator > 0 && numerator >= 0 && numerator <= denominator * 2) {
      return {
        type: 'fraction',
        data: {
          numerator,
          denominator,
          label: `${numerator}/${denominator}`,
        },
      }
    }
  }

  if (/数轴|在数轴上/.test(text)) {
    return {
      type: 'number_line',
      data: {
        min: 0,
        max: 10,
        marks: [
          { position: 0, label: '0' },
          { position: 5, label: '5' },
          { position: 10, label: '10' },
        ],
      },
    }
  }

  if (/条形统计图|统计图|条形图/.test(text)) {
    return {
      type: 'bar_chart',
      data: {
        items: [
          { label: '甲', value: 3 },
          { label: '乙', value: 5 },
          { label: '丙', value: 4 },
        ],
      },
    }
  }

  return { type: 'none', data: null }
}

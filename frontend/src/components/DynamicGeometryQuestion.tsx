import { useEffect, useRef } from 'react'

export type GeoInteractionEvent = {
  type: 'drag_point'
  questionId: string
  position: [number, number]
  timestamp: number
}

export type GeoQuestion = {
  id: string
  type: 'drag_point' | 'drag_slider' | 'construct_shape'
  config?: {
    boundingbox?: number[]
    start?: [number, number]
    snapToGrid?: boolean
  }
  correct_answer: { x: number; y: number }
}

type Props = {
  question: GeoQuestion
  onInteraction: (log: GeoInteractionEvent) => void
  onReady?: (api: { checkAnswer: () => boolean }) => void
}

type BoardPoint = {
  X: () => number
  Y: () => number
  on: (event: string, handler: () => void) => void
}

type Board = {
  create: (type: string, parents: unknown[], attrs?: Record<string, unknown>) => BoardPoint
  destroy?: () => void
}

type JxgModule = {
  JSXGraph: {
    initBoard: (el: HTMLElement | string, attrs: Record<string, unknown>) => Board
    freeBoard?: (board: Board) => void
  }
}

export default function DynamicGeometryQuestion({
  question,
  onInteraction,
  onReady,
}: Props) {
  const boardRef = useRef<HTMLDivElement | null>(null)
  const pointRef = useRef<BoardPoint | null>(null)

  useEffect(() => {
    const el = boardRef.current
    if (!el) return

    let board: Board | null = null
    let cancelled = false

    async function setup() {
      const JXG = (await import('jsxgraph')) as unknown as JxgModule
      if (cancelled || !boardRef.current) return
      const box = question.config?.boundingbox ?? [-5, 5, 5, -5]
      const start = question.config?.start ?? [1, 2]
      board = JXG.JSXGraph.initBoard(boardRef.current, {
        boundingbox: box,
        showNavigation: false,
        showCopyright: false,
      })

      if (question.type === 'drag_point') {
        const point = board.create('point', start, {
          name: 'P',
          size: 4,
          snapToGrid: question.config?.snapToGrid ?? true,
          withLabel: true,
        })
        pointRef.current = point
        point.on('drag', () => {
          onInteraction({
            type: 'drag_point',
            questionId: question.id,
            position: [point.X(), point.Y()],
            timestamp: Date.now(),
          })
        })
        board.create('text', [
          box[0] + 0.5,
          box[3] + 0.5,
          () => `P: (${point.X().toFixed(1)}, ${point.Y().toFixed(1)})`,
        ])
        onReady?.({
          checkAnswer: () => {
            const p = pointRef.current
            if (!p) return false
            return (
              Math.abs(p.X() - question.correct_answer.x) < 0.1 &&
              Math.abs(p.Y() - question.correct_answer.y) < 0.1
            )
          },
        })
      }
    }

    void setup()

    return () => {
      cancelled = true
      if (board) {
        try {
          board.destroy?.()
        } catch {
          /* ignore */
        }
      }
      pointRef.current = null
    }
  }, [question, onInteraction, onReady])

  return <div ref={boardRef} className="dynamic-geometry-board" style={{ width: '100%', height: 400 }} />
}

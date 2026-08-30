import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, waitFor } from '@testing-library/react'
import DynamicGeometryQuestion from './DynamicGeometryQuestion'

const point = {
  X: () => 1.0,
  Y: () => 2.0,
  on: vi.fn(),
}

const board = {
  create: vi.fn(() => point),
  destroy: vi.fn(),
}

vi.mock('jsxgraph', () => ({
  JSXGraph: {
    initBoard: vi.fn(() => board),
    freeBoard: vi.fn(),
  },
}))

describe('DynamicGeometryQuestion', () => {
  beforeEach(() => {
    point.on.mockClear()
    board.create.mockClear()
  })

  it('initializes board and exposes checkAnswer via onReady', async () => {
    const onInteraction = vi.fn()
    const onReady = vi.fn()
    render(
      <DynamicGeometryQuestion
        question={{
          id: 'g1',
          type: 'drag_point',
          correct_answer: { x: 1, y: 2 },
          config: { start: [1, 2] },
        }}
        onInteraction={onInteraction}
        onReady={onReady}
      />,
    )
    await waitFor(() => expect(onReady).toHaveBeenCalled())
    const api = onReady.mock.calls[0][0]
    expect(api.checkAnswer()).toBe(true)
    expect(board.create).toHaveBeenCalled()
  })
})

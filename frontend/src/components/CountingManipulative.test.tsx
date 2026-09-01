import { fireEvent, render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import CountingManipulative from './CountingManipulative'

describe('CountingManipulative', () => {
  it('marks apples as removed and reports remaining count', () => {
    const onRemainingChange = vi.fn()
    render(
      <CountingManipulative
        spec={{ type: 'counting_takeaway', total: 6, takeAway: 3, objectLabel: '苹果' }}
        onRemainingChange={onRemainingChange}
      />,
    )

    const apples = screen.getAllByRole('button', { name: /^苹果 \d+$/ })
    expect(apples).toHaveLength(6)

    fireEvent.click(apples[0])
    fireEvent.click(apples[1])
    fireEvent.click(apples[2])

    expect(screen.getByText('已标记 3 / 3')).toBeInTheDocument()
    expect(screen.getByRole('strong')).toHaveTextContent('3')
    expect(onRemainingChange).toHaveBeenLastCalledWith(3)
  })
})

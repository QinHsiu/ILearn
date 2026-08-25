import { describe, expect, it, beforeEach, afterEach, vi } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import { useRole } from './useRole'
import { useResponsive } from './useResponsive'

function setSearch(search: string) {
  window.history.pushState({}, '', search)
}

describe('useRole', () => {
  beforeEach(() => {
    setSearch('/')
  })

  it('detects parent role and dashboard route', () => {
    setSearch('/?role=parent&user=p1')
    const { result } = renderHook(() => useRole())
    expect(result.current.isParent).toBe(true)
    expect(result.current.userId).toBe('p1')
    expect(result.current.getDashboardRoute()).toContain('role=parent')
  })

  it('detects student entry', () => {
    setSearch('/?student=1')
    const { result } = renderHook(() => useRole())
    expect(result.current.isStudent).toBe(true)
    expect(result.current.getDashboardRoute()).toBe('?student=1')
  })
})

describe('useResponsive', () => {
  const original = window.innerWidth

  afterEach(() => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: original })
  })

  it('maps widths to breakpoints', () => {
    Object.defineProperty(window, 'innerWidth', { configurable: true, value: 500 })
    const { result, rerender } = renderHook(() => useResponsive())
    expect(result.current).toBe('mobile')

    act(() => {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: 800 })
      window.dispatchEvent(new Event('resize'))
    })
    rerender()
    expect(result.current).toBe('tablet')

    act(() => {
      Object.defineProperty(window, 'innerWidth', { configurable: true, value: 1200 })
      window.dispatchEvent(new Event('resize'))
    })
    rerender()
    expect(result.current).toBe('desktop')
  })
})

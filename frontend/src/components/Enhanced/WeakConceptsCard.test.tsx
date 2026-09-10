import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { WeakConceptsCard } from './WeakConceptsCard'

describe('WeakConceptsCard', () => {
  it('shows student title「待加强」', () => {
    render(<WeakConceptsCard weakConcepts={['分数']} viewMode="student" />)

    expect(screen.getByText('待加强')).toBeInTheDocument()
    expect(screen.queryByText('薄弱知识点')).not.toBeInTheDocument()
  })

  it('shows teacher title「薄弱知识点」', () => {
    render(<WeakConceptsCard weakConcepts={['分数']} viewMode="teacher" />)

    expect(screen.getByText('薄弱知识点')).toBeInTheDocument()
    expect(screen.queryByText('待加强')).not.toBeInTheDocument()
  })

  it('shows student empty message', () => {
    render(<WeakConceptsCard weakConcepts={[]} viewMode="student" />)

    expect(screen.getByText('暂无需加强的内容，继续保持！')).toBeInTheDocument()
  })

  it('shows teacher empty message', () => {
    render(<WeakConceptsCard weakConcepts={[]} viewMode="teacher" />)

    expect(screen.getByText('暂无明显薄弱点')).toBeInTheDocument()
  })

  it('renders up to 8 weak concept chips', () => {
    const concepts = Array.from({ length: 10 }, (_, i) => `概念${i + 1}`)

    render(<WeakConceptsCard weakConcepts={concepts} viewMode="student" />)

    expect(screen.getAllByTitle(/概念/)).toHaveLength(8)
    expect(screen.queryByTitle('概念9')).not.toBeInTheDocument()
  })
})

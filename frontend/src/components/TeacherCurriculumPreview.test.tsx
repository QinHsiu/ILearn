import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import TeacherCurriculumPreview from './TeacherCurriculumPreview'
import type { AssessmentItem } from '../api/client'

describe('TeacherCurriculumPreview', () => {
  it('shows chapter and confidence without answer keys', () => {
    const items: AssessmentItem[] = [
      {
        id: 'q1',
        stem: '1.2×3',
        type: 'short',
        difficulty: 'easy',
        knowledge_ids: ['k1'],
        answer_key: '3.6',
        source_refs: [
          {
            textbook_chapter: '小数乘法',
            curriculum_objective_ids: ['BJ-5-M-01'],
            confidence: 0.91,
            example_answer: '3.6',
          },
        ],
      },
    ]
    render(<TeacherCurriculumPreview items={items} />)
    expect(screen.getByRole('heading', { name: /题级课标预览/ })).toBeInTheDocument()
    expect(screen.getByText(/章节：小数乘法/)).toBeInTheDocument()
    expect(screen.getByText(/置信度：91%/)).toBeInTheDocument()
    expect(screen.queryByText('3.6')).not.toBeInTheDocument()
  })
})

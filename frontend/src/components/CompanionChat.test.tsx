import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import CompanionChat from './CompanionChat'
import { api } from '../api/client'

vi.mock('../api/client', () => ({
  api: {
    companionChat: vi.fn(),
    companionTranscribe: vi.fn(),
    companionHistory: vi.fn(),
  },
}))

describe('CompanionChat', () => {
  beforeEach(() => {
    vi.mocked(api.companionHistory).mockResolvedValue({ session_id: 's1', turns: [] })
    vi.mocked(api.companionChat).mockResolvedValue({
      intent: 'answer',
      reply: '分数表示整体的一部分。',
      speech: { ssml_or_text: '分数表示整体的一部分。', locale: 'zh-CN', speakable: true },
      actions: [],
      input_modality: 'text',
      mode: 'exam_tutor',
    })
  })

  it('sends text and renders assistant reply', async () => {
    render(<CompanionChat sessionId="s1" />)
    fireEvent.change(screen.getByLabelText('输入问题'), {
      target: { value: '什么是分数？' },
    })
    fireEvent.click(screen.getByRole('button', { name: '发送' }))
    await waitFor(() => {
      expect(api.companionChat).toHaveBeenCalledWith('s1', { message: '什么是分数？' })
    })
    expect(await screen.findByText('分数表示整体的一部分。')).toBeInTheDocument()
  })

  it('fires onStartAssessment when evaluate action returns', async () => {
    const onStart = vi.fn()
    vi.mocked(api.companionChat).mockResolvedValue({
      intent: 'evaluate',
      reply: '好的，启动测评。',
      speech: { ssml_or_text: '好的，启动测评。', speakable: true },
      actions: [{ type: 'start_assessment', payload: {} }],
      input_modality: 'text',
    })
    render(<CompanionChat sessionId="s1" onStartAssessment={onStart} />)
    fireEvent.click(screen.getByRole('button', { name: '开始测评' }))
    await waitFor(() => expect(onStart).toHaveBeenCalled())
  })
})

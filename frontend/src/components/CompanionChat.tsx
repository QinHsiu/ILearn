import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '../api/client'
import type { CompanionReply } from '../api/client'

type ChatTurn = {
  role: 'user' | 'assistant'
  text: string
  intent?: string
  speech?: string
  modality?: string
}

type CompanionChatProps = {
  sessionId: string
  onStartAssessment?: () => void
  onBack?: () => void
}

const SUGGESTIONS = ['什么是分数？', '我想学', '给我出一套测评卷', '帮我规划本周学习']

export default function CompanionChat({
  sessionId,
  onStartAssessment,
  onBack,
}: CompanionChatProps) {
  const [turns, setTurns] = useState<ChatTurn[]>([])
  const [draft, setDraft] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [listening, setListening] = useState(false)
  const [lastSpeech, setLastSpeech] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)

  const scrollBottom = useCallback(() => {
    const el = listRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [])

  useEffect(() => {
    scrollBottom()
  }, [turns, scrollBottom])

  useEffect(() => {
    let cancelled = false
    void api
      .companionHistory(sessionId)
      .then((hist) => {
        if (cancelled || !hist.turns?.length) return
        const restored: ChatTurn[] = []
        for (const row of hist.turns) {
          const meta = row.metadata || {}
          const userText = typeof meta.user_text === 'string' ? meta.user_text : ''
          const replyText =
            typeof meta.reply === 'string'
              ? meta.reply
              : typeof meta.assistant_text === 'string'
                ? meta.assistant_text
                : ''
          if (userText) restored.push({ role: 'user', text: userText })
          if (replyText) {
            restored.push({
              role: 'assistant',
              text: replyText,
              intent: typeof meta.intent === 'string' ? meta.intent : undefined,
            })
          }
        }
        if (restored.length) setTurns(restored)
      })
      .catch(() => {
        /* history is best-effort */
      })
    return () => {
      cancelled = true
    }
  }, [sessionId])

  function applyReply(userText: string, reply: CompanionReply) {
    setTurns((prev) => [
      ...prev,
      { role: 'user', text: userText, modality: reply.input_modality },
      {
        role: 'assistant',
        text: reply.reply,
        intent: reply.intent,
        speech: reply.speech?.ssml_or_text,
        modality: reply.input_modality,
      },
    ])
    setLastSpeech(reply.speech?.ssml_or_text || reply.reply)
    if (reply.actions?.some((a) => a.type === 'start_assessment')) {
      onStartAssessment?.()
    }
  }

  async function sendText(raw: string) {
    const message = raw.trim()
    if (!message || busy) return
    setBusy(true)
    setError(null)
    try {
      const reply = await api.companionChat(sessionId, { message })
      applyReply(message, reply)
      setDraft('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  /** Mic hook: capture blob → object URL as audio_ref → /transcribe with text_fallback for P1. */
  async function onMicClick() {
    if (busy || listening) return
    setError(null)
    if (!navigator.mediaDevices?.getUserMedia) {
      setError('当前浏览器不支持麦克风；可先用文字提问。')
      return
    }
    setListening(true)
    let stream: MediaStream | null = null
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const recorder = new MediaRecorder(stream)
      const chunks: BlobPart[] = []
      const done = new Promise<Blob>((resolve, reject) => {
        recorder.ondataavailable = (ev) => {
          if (ev.data.size) chunks.push(ev.data)
        }
        recorder.onstop = () => resolve(new Blob(chunks, { type: 'audio/webm' }))
        recorder.onerror = () => reject(new Error('录音失败'))
      })
      recorder.start()
      await new Promise((r) => window.setTimeout(r, 1800))
      if (recorder.state !== 'inactive') recorder.stop()
      const blob = await done
      const audioRef = URL.createObjectURL(blob)
      const fallback = draft.trim() || '我想学'
      const asr = await api.companionTranscribe(sessionId, {
        audio_ref: audioRef,
        text_fallback: fallback,
      })
      const text = (asr.text || fallback).trim()
      setDraft(text)
      const reply = await api.companionChat(sessionId, {
        perception: {
          source_type: 'speech',
          text,
          audio_ref: audioRef,
          confidence: asr.confidence,
        },
      })
      applyReply(text, reply)
      setDraft('')
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      stream?.getTracks().forEach((t) => t.stop())
      setListening(false)
      setBusy(false)
    }
  }

  function speakLast() {
    if (!lastSpeech || typeof window.speechSynthesis === 'undefined') return
    window.speechSynthesis.cancel()
    const utt = new SpeechSynthesisUtterance(lastSpeech)
    utt.lang = 'zh-CN'
    window.speechSynthesis.speak(utt)
  }

  return (
    <section className="panel student-panel companion-chat">
      <p className="student-panel-eyebrow">COMPANION / ASK · ANSWER</p>
      <h2>学习同伴</h2>
      <p className="lede">
        先问清楚再学；需要测评时直接说「给我出一套测评卷」。语音入口已接好，可点麦克风试说。
      </p>

      <div className="companion-suggestions" role="group" aria-label="快捷提问">
        {SUGGESTIONS.map((s) => (
          <button
            key={s}
            type="button"
            className="companion-chip"
            disabled={busy}
            onClick={() => void sendText(s)}
          >
            {s}
          </button>
        ))}
      </div>

      <div className="companion-turns" ref={listRef} aria-live="polite">
        {turns.length === 0 ? (
          <p className="companion-empty">还没有对话。试着问一个概念，或直接开始测评。</p>
        ) : (
          turns.map((t, i) => (
            <div
              key={`${t.role}-${i}`}
              className={`companion-turn companion-turn-${t.role}`}
            >
              <p className="companion-turn-role">
                {t.role === 'user' ? '你' : '同伴'}
                {t.intent ? ` · ${t.intent}` : ''}
                {t.modality && t.modality !== 'text' ? ` · ${t.modality}` : ''}
              </p>
              <p className="companion-turn-text">{t.text}</p>
            </div>
          ))
        )}
      </div>

      {error ? (
        <p className="error" role="alert">
          {error}
        </p>
      ) : null}

      <div className="companion-composer">
        <label className="sr-only" htmlFor="companion-draft">
          输入问题
        </label>
        <textarea
          id="companion-draft"
          rows={2}
          value={draft}
          disabled={busy}
          placeholder="想学什么？或直接说「给我出一套测评卷」"
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              void sendText(draft)
            }
          }}
        />
        <div className="companion-composer-actions">
          <button
            type="button"
            className={`btn secondary companion-mic${listening ? ' is-listening' : ''}`}
            disabled={busy}
            aria-pressed={listening}
            aria-label="语音输入"
            onClick={() => void onMicClick()}
          >
            {listening ? '聆听中…' : '麦克风'}
          </button>
          <button
            type="button"
            className="btn secondary"
            disabled={!lastSpeech}
            onClick={speakLast}
          >
            朗读回复
          </button>
          <button
            type="button"
            className="btn"
            disabled={busy || !draft.trim()}
            onClick={() => void sendText(draft)}
          >
            {busy ? '思考中…' : '发送'}
          </button>
        </div>
      </div>

      <div className="actions">
        {onBack ? (
          <button className="btn secondary" type="button" onClick={onBack}>
            返回建档
          </button>
        ) : null}
        <button
          className="btn"
          type="button"
          disabled={busy}
          onClick={() => {
            void sendText('给我出一套测评卷')
          }}
        >
          开始测评
        </button>
      </div>
    </section>
  )
}

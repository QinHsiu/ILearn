import type { ReactNode } from 'react'

type Props = {
  source: string
}

function inline(text: string): ReactNode[] {
  const parts: ReactNode[] = []
  const re = /\*\*(.+?)\*\*/g
  let last = 0
  let match: RegExpExecArray | null
  let key = 0
  while ((match = re.exec(text)) !== null) {
    if (match.index > last) {
      parts.push(text.slice(last, match.index))
    }
    parts.push(<strong key={`b-${key++}`}>{match[1]}</strong>)
    last = match.index + match[0].length
  }
  if (last < text.length) {
    parts.push(text.slice(last))
  }
  return parts
}

export default function MarkdownView({ source }: Props) {
  const lines = source.replace(/\r\n/g, '\n').split('\n')
  const blocks: ReactNode[] = []
  let list: string[] = []
  let key = 0

  const flushList = () => {
    if (!list.length) return
    blocks.push(
      <ul key={`ul-${key++}`}>
        {list.map((item, i) => (
          <li key={i}>{inline(item)}</li>
        ))}
      </ul>,
    )
    list = []
  }

  for (const raw of lines) {
    const line = raw.trimEnd()
    const trimmed = line.trim()
    if (!trimmed) {
      flushList()
      continue
    }
    if (trimmed.startsWith('- ')) {
      list.push(trimmed.slice(2))
      continue
    }
    flushList()
    if (trimmed.startsWith('### ')) {
      blocks.push(<h3 key={`h3-${key++}`}>{inline(trimmed.slice(4))}</h3>)
    } else if (trimmed.startsWith('## ')) {
      blocks.push(<h2 key={`h2-${key++}`}>{inline(trimmed.slice(3))}</h2>)
    } else if (trimmed.startsWith('# ')) {
      blocks.push(<h1 key={`h1-${key++}`}>{inline(trimmed.slice(2))}</h1>)
    } else if (trimmed.startsWith('> ')) {
      blocks.push(
        <blockquote key={`q-${key++}`}>{inline(trimmed.slice(2))}</blockquote>,
      )
    } else if (trimmed.startsWith('|')) {
      blocks.push(
        <pre key={`t-${key++}`} className="md-table-fallback">
          {trimmed}
        </pre>,
      )
    } else {
      blocks.push(<p key={`p-${key++}`}>{inline(trimmed)}</p>)
    }
  }
  flushList()

  if (!blocks.length) {
    return <p className="lede">暂无计划内容</p>
  }
  return <div className="md-view">{blocks}</div>
}

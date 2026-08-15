import type { CSSProperties, ReactNode } from 'react'

type Props = {
  source: string
}

type Align = 'left' | 'right' | 'center'

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

function splitRow(line: string): string[] {
  return line
    .replace(/^\|/, '')
    .replace(/\|$/, '')
    .split('|')
    .map((cell) => cell.trim())
}

function isSeparatorRow(line: string): boolean {
  const cells = splitRow(line)
  return cells.length > 0 && cells.every((cell) => /^:?-{1,}:?$/.test(cell))
}

function alignOf(cell: string): Align {
  const left = cell.startsWith(':')
  const right = cell.endsWith(':')
  if (left && right) return 'center'
  if (right) return 'right'
  return 'left'
}

function cellStyle(align: Align): CSSProperties | undefined {
  return align === 'left' ? undefined : { textAlign: align }
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

  for (let i = 0; i < lines.length; i += 1) {
    const line = lines[i].trimEnd()
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
      const rows: string[] = []
      let cursor = i
      while (cursor < lines.length && lines[cursor].trim().startsWith('|')) {
        rows.push(lines[cursor].trim())
        cursor += 1
      }
      i = cursor - 1

      const separatorIndex = rows.findIndex(isSeparatorRow)
      if (separatorIndex < 1) {
        // Not a well-formed table (no header/separator): keep raw text readable.
        blocks.push(
          <pre key={`t-${key++}`} className="md-table-fallback">
            {rows.join('\n')}
          </pre>,
        )
        continue
      }

      const headers = splitRow(rows[separatorIndex - 1])
      const aligns = splitRow(rows[separatorIndex]).map(alignOf)
      const bodyRows = rows.slice(separatorIndex + 1).map(splitRow)

      blocks.push(
        <div key={`tw-${key++}`} className="md-table-wrap">
          <table className="md-table">
            <thead>
              <tr>
                {headers.map((header, c) => (
                  <th key={c} style={cellStyle(aligns[c] || 'left')}>
                    {inline(header)}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {bodyRows.map((cells, r) => (
                <tr key={r}>
                  {headers.map((_, c) => (
                    <td key={c} style={cellStyle(aligns[c] || 'left')}>
                      {inline(cells[c] || '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>,
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

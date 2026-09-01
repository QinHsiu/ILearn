export function splitMarkdownAtHeading(source: string, heading: string): [string, string] {
  const marker = `## ${heading}`
  const normalized = source.replace(/\r\n/g, '\n')
  const needle = `\n${marker}`
  const idx = normalized.indexOf(needle)
  if (idx >= 0) {
    return [normalized.slice(0, idx).trim(), normalized.slice(idx + 1).trim()]
  }
  if (normalized.startsWith(marker)) {
    return ['', normalized.trim()]
  }
  return [normalized.trim(), '']
}

export function splitPlanMarkdown(source: string): [string, string] {
  return splitMarkdownAtHeading(source, '科学学习方法')
}

export function splitFullReportMarkdown(source: string): [string, string] {
  return splitMarkdownAtHeading(source, '学习计划')
}

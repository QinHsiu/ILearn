import type { ReactNode } from 'react'

type DashboardHomeProps = {
  title: string
  children: ReactNode
}

export function updateDashboardQuery(updates: Record<string, string | null>) {
  const params = new URLSearchParams(window.location.search)
  Object.entries(updates).forEach(([key, value]) => {
    if (value === null) params.delete(key)
    else params.set(key, value)
  })
  const query = params.toString()
  window.history.replaceState({}, '', `${window.location.pathname}${query ? `?${query}` : ''}`)
}

export default function DashboardHome({ title, children }: DashboardHomeProps) {
  return (
    <div className="app-shell dashboard-shell">
      <header className="brand-row">
        <h1 className="brand">ILearn</h1>
        <div className="brand-copy">
          <p className="brand-sub">课标在环的个性化学习向导</p>
          <p className="brand-sub">{title}</p>
        </div>
      </header>
      {children}
    </div>
  )
}

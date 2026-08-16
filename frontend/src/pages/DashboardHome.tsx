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
          <div className="dashboard-header-meta">
            <span className="dashboard-role-badge">{title}</span>
            <a className="back-link dashboard-back-link" href="/">
              返回角色选择
            </a>
          </div>
        </div>
      </header>
      {children}
    </div>
  )
}

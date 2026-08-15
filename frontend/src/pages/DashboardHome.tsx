import type { ReactNode } from 'react'

type DashboardHomeProps = {
  title: string
  children: ReactNode
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

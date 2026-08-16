import { useState } from 'react'
import type { FormEvent } from 'react'
import { authApi } from '../api/client'
import type { AuthRole } from '../api/client'

type LoginPageProps = {
  role: AuthRole
}

const roleLabels: Record<AuthRole, string> = {
  parent: '家长',
  teacher: '老师',
}

export default function LoginPage({ role }: LoginPageProps) {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError(null)
    try {
      const result = await authApi.login(role, username, password)
      window.history.pushState({}, '', `?role=${result.role}&user=${encodeURIComponent(result.user_id)}`)
      window.dispatchEvent(new PopStateEvent('popstate'))
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <main className="login-page">
      <a className="back-link" href="?login=1">
        ← 返回角色选择
      </a>
      <p className="eyebrow">ILearn · {roleLabels[role]}端</p>
      <h1>{roleLabels[role]}登录</h1>
      <p className="landing-lede">登录后查看专属学习数据。</p>
      <form className="panel login-form" onSubmit={onSubmit}>
        <div className="field">
          <label htmlFor="username">用户名</label>
          <input
            id="username"
            value={username}
            onChange={(event) => setUsername(event.target.value)}
            autoComplete="username"
            required
          />
        </div>
        <div className="field">
          <label htmlFor="password">密码</label>
          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            autoComplete="current-password"
            required
          />
        </div>
        <div className="actions">
          <button className="btn" type="submit" disabled={busy}>
            {busy ? '登录中…' : '登录'}
          </button>
        </div>
        {error ? <p className="error" role="alert">{error}</p> : null}
      </form>
    </main>
  )
}

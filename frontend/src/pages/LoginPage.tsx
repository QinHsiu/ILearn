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

const roleCopy: Record<AuthRole, { eyebrow: string; title: string; description: string }> = {
  parent: {
    eyebrow: 'CHILD GROWTH',
    title: '进入孩子成长空间',
    description: '查看孩子的诊断、学习阶段与下一步支持建议。',
  },
  teacher: {
    eyebrow: 'CLASS STUDIO',
    title: '进入班级工作台',
    description: '扫描班级状态，定位需要优先干预的学生。',
  },
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
    <main className={`login-page login-${role}`}>
      <header className="login-header">
        <a className="back-link" href="?login=1">
        ← 返回角色选择
        </a>
        <p className="landing-meta">ILearn / {roleCopy[role].eyebrow}</p>
      </header>
      <div className="login-grid">
        <section className="login-intro" aria-labelledby="login-title">
          <p className="eyebrow">ILearn · {roleLabels[role]}端</p>
          <h1 id="login-title">{roleCopy[role].title}</h1>
          <p className="landing-lede">{roleCopy[role].description}</p>
        </section>
        <form className="panel login-form" onSubmit={onSubmit}>
          <p className="form-caption">身份验证 / SIGN IN</p>
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
      </div>
    </main>
  )
}

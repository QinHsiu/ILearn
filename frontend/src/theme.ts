export type Band = 'primary' | 'junior' | 'senior'

export function bandForGrade(grade: number): Band {
  if (grade <= 6) return 'primary'
  if (grade <= 9) return 'junior'
  return 'senior'
}

export function themeKeyFor(grade: number, gender: string): string {
  const g = ['male', 'female', 'unspecified'].includes(gender) ? gender : 'unspecified'
  return `${bandForGrade(grade)}_${g}`
}

export type ThemeTokens = {
  accent: string
  radius: string
  ink: string
  scale: string
}

export const THEMES: Record<string, ThemeTokens> = {
  primary_male: { accent: '#1a73e8', radius: '18px', ink: '#16343a', scale: '1.05' },
  primary_female: { accent: '#e84393', radius: '18px', ink: '#16343a', scale: '1.05' },
  primary_unspecified: { accent: '#176b67', radius: '18px', ink: '#16343a', scale: '1.05' },
  junior_male: { accent: '#0b5cab', radius: '12px', ink: '#1b2a33', scale: '1' },
  junior_female: { accent: '#c2185b', radius: '12px', ink: '#1b2a33', scale: '1' },
  junior_unspecified: { accent: '#176b67', radius: '12px', ink: '#1b2a33', scale: '1' },
  senior_male: { accent: '#1b3a4b', radius: '8px', ink: '#122026', scale: '0.98' },
  senior_female: { accent: '#6d214f', radius: '8px', ink: '#122026', scale: '0.98' },
  senior_unspecified: { accent: '#16343a', radius: '8px', ink: '#122026', scale: '0.98' },
}

export function applyTheme(grade: number, gender: string) {
  const key = themeKeyFor(grade, gender)
  const tokens = THEMES[key] || THEMES.primary_unspecified
  const root = document.documentElement
  root.dataset.band = bandForGrade(grade)
  root.dataset.gender = gender
  root.style.setProperty('--accent', tokens.accent)
  root.style.setProperty('--radius', tokens.radius)
  root.style.setProperty('--btn-radius', tokens.radius)
  root.style.setProperty('--card-radius', tokens.radius)
  root.style.setProperty('--ink', tokens.ink)
  root.style.setProperty('--theme-scale', tokens.scale)
}

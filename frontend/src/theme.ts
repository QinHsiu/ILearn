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
  background: string
  fontBody: string
}

// Palettes from doc/deepseek_edition/0815/config.ts (elementary/middle/high → primary/junior/senior)
export const THEMES: Record<string, ThemeTokens> = {
  primary_male: {
    accent: '#4A90D9',
    radius: '20px',
    ink: '#1A2A3A',
    scale: '1.05',
    background: '#F0F7FF',
    fontBody: '18px',
  },
  primary_female: {
    accent: '#FF6B81',
    radius: '20px',
    ink: '#3A1A2A',
    scale: '1.05',
    background: '#FFF5F7',
    fontBody: '18px',
  },
  primary_unspecified: {
    accent: '#4A90D9',
    radius: '20px',
    ink: '#1A2A3A',
    scale: '1.05',
    background: '#F0F7FF',
    fontBody: '18px',
  },
  junior_male: {
    accent: '#2C3E50',
    radius: '12px',
    ink: '#1A2A3A',
    scale: '1',
    background: '#F5F8FA',
    fontBody: '16px',
  },
  junior_female: {
    accent: '#6C5CE7',
    radius: '12px',
    ink: '#2A1A3A',
    scale: '1',
    background: '#F8F5FF',
    fontBody: '16px',
  },
  junior_unspecified: {
    accent: '#2C3E50',
    radius: '12px',
    ink: '#1A2A3A',
    scale: '1',
    background: '#F5F8FA',
    fontBody: '16px',
  },
  senior_male: {
    accent: '#1A1A2E',
    radius: '8px',
    ink: '#1A1A2E',
    scale: '0.98',
    background: '#F8F8FC',
    fontBody: '15px',
  },
  senior_female: {
    accent: '#4A2A5A',
    radius: '8px',
    ink: '#2A1A3A',
    scale: '0.98',
    background: '#FAF8FC',
    fontBody: '15px',
  },
  senior_unspecified: {
    accent: '#1A1A2E',
    radius: '8px',
    ink: '#1A1A2E',
    scale: '0.98',
    background: '#F8F8FC',
    fontBody: '15px',
  },
}

export function applyTheme(grade: number, gender: string) {
  const key = themeKeyFor(grade, gender)
  const tokens = THEMES[key] || THEMES.primary_unspecified
  const root = document.documentElement
  root.dataset.band = bandForGrade(grade)
  root.dataset.gender = gender
  root.style.setProperty('--accent', tokens.accent)
  root.style.setProperty('--color-primary', tokens.accent)
  root.style.setProperty('--radius', tokens.radius)
  root.style.setProperty('--btn-radius', tokens.radius)
  root.style.setProperty('--card-radius', tokens.radius)
  root.style.setProperty('--ink', tokens.ink)
  root.style.setProperty('--paper', tokens.background)
  root.style.setProperty('--theme-scale', tokens.scale)
  root.style.setProperty('--font-size-body', tokens.fontBody)
}

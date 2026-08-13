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

/** Accent hues aligned with existing Streamlit theme packs. */
const ACCENTS: Record<string, string> = {
  primary_male: '#1a73e8',
  primary_female: '#e84393',
  primary_unspecified: '#176b67',
  junior_male: '#0b5cab',
  junior_female: '#c2185b',
  junior_unspecified: '#176b67',
  senior_male: '#1b3a4b',
  senior_female: '#6d214f',
  senior_unspecified: '#16343a',
}

export function applyTheme(grade: number, gender: string) {
  const key = themeKeyFor(grade, gender)
  const root = document.documentElement
  root.dataset.band = bandForGrade(grade)
  root.dataset.gender = gender
  root.style.setProperty('--accent', ACCENTS[key] || ACCENTS.primary_unspecified)
}

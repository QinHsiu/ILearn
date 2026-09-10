import styles from './enhanced.module.css'

interface EmotionCardProps {
  currentEmotion: string
  learningStyle: string
  overallMastery?: number
}

const EMOTION_MAP: Record<string, { label: string; emoji: string }> = {
  neutral: { label: '中性', emoji: '😐' },
  confused: { label: '困惑', emoji: '🤔' },
  frustrated: { label: '挫败', emoji: '😤' },
  excited: { label: '兴奋', emoji: '😊' },
  bored: { label: '无聊', emoji: '😴' },
  engaged: { label: '投入', emoji: '🎯' },
}

const STYLE_MAP: Record<string, string> = {
  guided: '引导型',
  exploratory: '探究型',
  visual: '视觉型',
  verbal: '语言型',
}

export function EmotionCard({
  currentEmotion,
  learningStyle,
  overallMastery,
}: EmotionCardProps) {
  const emotion = EMOTION_MAP[currentEmotion] || EMOTION_MAP.neutral
  const styleLabel = STYLE_MAP[learningStyle] || '未识别'
  const masteryPct =
    typeof overallMastery === 'number' ? Math.round(overallMastery * 100) : null

  return (
    <div className={styles.card}>
      <div className={styles.cardTitleSpaced}>学习状态</div>
      <div className={styles.emotionRow}>
        <div className={styles.emotionGroup}>
          <span className={styles.emotionEmoji} aria-hidden>
            {emotion.emoji}
          </span>
          <span className={styles.emotionLabel}>{emotion.label}</span>
        </div>
        <div className={styles.divider} />
        <div className={styles.metaText}>
          风格：<span className={styles.metaValue}>{styleLabel}</span>
        </div>
        {masteryPct !== null && (
          <>
            <div className={styles.divider} />
            <div className={styles.metaText}>
              掌握度：<span className={styles.metaValue}>{masteryPct}%</span>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

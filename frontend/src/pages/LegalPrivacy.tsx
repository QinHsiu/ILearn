export default function LegalPrivacy() {
  return (
    <main className="landing-page legal-privacy">
      <header className="landing-header">
        <div className="landing-brand-block">
          <p className="landing-kicker">TRUST</p>
          <p className="landing-brand">ILearn</p>
        </div>
        <p className="landing-meta">
          <a href="?">返回首页</a>
        </p>
      </header>
      <section className="landing-hero" aria-labelledby="privacy-title">
        <h1 id="privacy-title">隐私与能力边界</h1>
        <p className="landing-lede">
          ILearn 软上线演示用于验证「课标在环 · 辅导不泄题 · 掌握度有证据」的产品承诺。
        </p>
          <ul>
            <li>演示数据可能为预置教学单元，不代表真实学校档案。</li>
            <li>试点范围：小学数学四至六年级 · 北京·人教；未覆盖学段/学科不作商用承诺。</li>
            <li>不收集身份证号等敏感身份证件信息；候补邮箱仅用于开放通知。</li>
            <li>苏格拉底辅导默认不直接给出最终数值答案；LLM 为可选增强，无密钥时可离线降级。</li>
            <li>批改与课标引用可审计；请勿将本系统当作搜题、拍照出答案或代写作业工具。</li>
            <li>
              与常见搜题产品不同：ILearn 输出的是可追溯诊断与学习计划，而不是题目终答。
            </li>
          </ul>
      </section>
    </main>
  )
}

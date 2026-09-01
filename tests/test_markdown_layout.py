from ilearn.core.markdown_layout import split_learning_report, split_plan_report


def test_split_plan_report():
    md = "# 计划\n\n## 每日安排\n\n内容\n\n## 科学学习方法\n\n方法"
    left, right = split_plan_report(md)
    assert "每日安排" in left
    assert "科学学习方法" in right
    assert "方法" in right


def test_split_learning_report():
    md = "# 报告\n\n## 学情诊断\n\n诊断\n\n## 学习计划\n\n计划"
    left, right = split_learning_report(md)
    assert "学情诊断" in left
    assert "学习计划" in right

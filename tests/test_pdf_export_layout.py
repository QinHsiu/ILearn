"""PDF export layout and HTML structure tests."""

from ilearn.core.markdown_layout import split_learning_report
from ilearn.core.pdf_export import (
    markdown_to_html,
    markdown_to_html_two_column,
    markdown_to_pdf,
    markdown_to_pdf_report,
)


SAMPLE_REPORT = """# ILearn 学习报告

## 基本信息

- **地区：** 北京
- **年级：** 5 年级

## 学情诊断

### 知识掌握

| 知识点 | 得分率 | 掌握等级 | 关联题目 |
| --- | ---: | --- | --- |
| 小数乘法 | 60% | 薄弱 | q1 |

## 学习计划

### 第 1 天

- 复习小数乘法
"""


def test_markdown_to_html_includes_branded_layout():
    html = markdown_to_html(SAMPLE_REPORT)
    assert "pdf-brand-bar" in html
    assert "data-table" in html
    assert "section-heading" in html
    assert "doc-title" in html
    assert "ILearn 学习报告" in html


def test_two_column_html_splits_diagnosis_and_plan():
    left, right = split_learning_report(SAMPLE_REPORT)
    assert "学情诊断" in left
    assert "学习计划" in right
    html = markdown_to_html_two_column(left, right)
    assert "report-columns" in html
    assert "report-col-left" in html
    assert "report-col-right" in html


def test_question_heading_class_for_assessment_blocks():
    md = """# ILearn 做题复盘

## 题目作答记录

### 第 1 题 · 正确

题干内容
"""
    html = markdown_to_html(md)
    assert "question-heading" in html


def test_pdf_bytes_generated():
    pdf = markdown_to_pdf(SAMPLE_REPORT)
    assert pdf[:4] == b"%PDF"


def test_pdf_report_uses_two_column_path():
    pdf = markdown_to_pdf_report(SAMPLE_REPORT)
    assert pdf[:4] == b"%PDF"
    assert len(pdf) > 200

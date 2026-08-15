import re
from typing import Any, Dict, Optional


class MathVerifyAdapter:
    """
    数学答案等价性验证适配器
    不依赖外部库，使用 Python 原生能力进行符号数学验证
    """

    @staticmethod
    def normalize_expression(expr: str) -> str:
        """标准化数学表达式"""
        # Preserve the separator in mixed numbers such as "1 1/2".
        expr = expr.strip().replace("\n", " ")
        # Unicode 分数转换: ½ -> 1/2
        fraction_map = {
            "½": "1/2", "⅓": "1/3", "⅔": "2/3",
            "¼": "1/4", "¾": "3/4", "⅕": "1/5",
            "⅖": "2/5", "⅗": "3/5", "⅘": "4/5",
            "⅙": "1/6", "⅚": "5/6", "⅛": "1/8",
            "⅜": "3/8", "⅝": "5/8", "⅞": "7/8",
        }
        for u, a in fraction_map.items():
            expr = expr.replace(u, a)
        if re.fullmatch(r"[+-]?\d+\s+\d+/\d+", expr):
            return re.sub(r"\s+", " ", expr)
        expr = re.sub(r"\s+", "", expr)
        return expr

    @staticmethod
    def parse_number(s: str) -> Optional[float]:
        """解析数字，支持分数、百分数、带单位"""
        s = s.strip().lower()
        if not s:
            return None

        # 百分数: 50% -> 0.5
        if s.endswith('%'):
            try:
                return float(s[:-1]) / 100
            except ValueError:
                return None

        # 分数: 3/4 或 1 1/2
        if '/' in s:
            parts = s.split('/')
            if len(parts) == 2:
                try:
                    num, den = float(parts[0]), float(parts[1])
                    if den == 0:
                        return None
                    return num / den
                except ValueError:
                    pass
            # 带分数: 1 1/2
            match = re.match(r'^(\d+)\s+(\d+)/(\d+)$', s.strip())
            if match:
                whole, num, den = match.groups()
                try:
                    return float(whole) + float(num) / float(den)
                except (ValueError, ZeroDivisionError):
                    pass

        # 科学计数法
        try:
            return float(s)
        except ValueError:
            return None

    @staticmethod
    def is_equivalent(student_answer: str, correct_answer: str) -> Dict[str, Any]:
        """
        判断两个数学答案是否等价
        返回: { equivalent: bool, reason: str, confidence: float }
        """
        # 标准化输入
        student_norm = MathVerifyAdapter.normalize_expression(student_answer)
        correct_norm = MathVerifyAdapter.normalize_expression(correct_answer)

        # 完全匹配（字符串）
        if student_norm == correct_norm:
            return {"equivalent": True, "reason": "exact_match", "confidence": 1.0}

        # 数值比较
        student_num = MathVerifyAdapter.parse_number(student_norm)
        correct_num = MathVerifyAdapter.parse_number(correct_norm)

        if student_num is not None and correct_num is not None:
            # 相对误差 < 0.001 认为相等（处理浮点误差）
            if abs(student_num - correct_num) < 1e-6:
                return {"equivalent": True, "reason": "numerical_match", "confidence": 0.95}
            if correct_num != 0 and abs(student_num - correct_num) / abs(correct_num) < 1e-3:
                return {"equivalent": True, "reason": "relative_match", "confidence": 0.9}
            return {"equivalent": False, "reason": "numerical_mismatch", "confidence": 0.95}

        # 近似匹配：去除空格、标点后比较
        cleaned_student = re.sub(r'[.,!?;:\s]', '', student_norm)
        cleaned_correct = re.sub(r'[.,!?;:\s]', '', correct_norm)
        if cleaned_student == cleaned_correct:
            return {"equivalent": True, "reason": "cleaned_match", "confidence": 0.85}

        # 等价表达式检测（简单代数等价）
        if MathVerifyAdapter._is_algebraic_equivalent(student_norm, correct_norm):
            return {"equivalent": True, "reason": "algebraic_match", "confidence": 0.8}

        return {"equivalent": False, "reason": "no_match", "confidence": 0.7}

    @staticmethod
    def _is_algebraic_equivalent(expr1: str, expr2: str) -> bool:
        """检测简单代数表达式等价（如 2*x 与 2x）"""
        # 移除常见符号
        expr1 = expr1.replace("*", "").replace(" ", "")
        expr2 = expr2.replace("*", "").replace(" ", "")

        # 变量替换标准化
        # 将 2x 标准化为 2*x
        expr1 = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr1)
        expr2 = re.sub(r'(\d)([a-zA-Z])', r'\1*\2', expr2)

        # 尝试使用 Python 的 ast 模块进行表达式规范化
        try:
            import sympy as sp
            try:
                # 尝试使用 sympy 精确比较
                e1 = sp.sympify(expr1)
                e2 = sp.sympify(expr2)
                return sp.simplify(e1 - e2) == 0
            except Exception:
                pass
        except ImportError:
            # sympy 未安装，使用简单字符串比较
            # 移除所有括号和空格
            expr1 = expr1.replace("(", "").replace(")", "")
            expr2 = expr2.replace("(", "").replace(")", "")
            return expr1 == expr2

        return False

    @staticmethod
    def verify_batch(student_answers: list, correct_answers: list) -> list:
        """批量验证"""
        return [
            MathVerifyAdapter.is_equivalent(s, c)
            for s, c in zip(student_answers, correct_answers)
        ]

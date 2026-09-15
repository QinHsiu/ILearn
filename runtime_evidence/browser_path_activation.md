# Browser-path Activation Evidence

Simulates Landing → demo CTA → role deep-link evidence (API equivalent of browser hops).

- session_id: `79e210d6aa154315ba7579007a77bb7d`
- elapsed_s: **0.169** (budget 60)
- max_user_clicks: **2** (1 create demo + 1 open role link)
- student_link: `?student=1&session_id=79e210d6aa154315ba7579007a77bb7d`
- parent_link: `?login=1&role=parent&user=demo_parent&student_id=79e210d6aa154315ba7579007a77bb7d`
- teacher_link: `?login=1&role=teacher&user=demo_teacher&class_id=demo_class_5a&student_id=79e210d6aa154315ba7579007a77bb7d`

## Hop log

- GET /quality-gates
- GET /capabilities
- POST /demo/units/math_5_1/session
- GET mastery-public (79e210d6…)
- GET summary/parent
- GET summary/teacher
- GET pilot-assets/concept/mult_3digit.md

Pass

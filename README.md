# ILearn

小学数学学情诊断与学习规划 MVP。

## 本地运行

```powershell
python -m pip install -r requirements.txt
uvicorn ilearn.api.app:app --reload
```

另开一个终端启动教学界面：

```powershell
streamlit run ilearn/web/app.py
```

界面默认访问 `http://127.0.0.1:8000`。如 API 在其他地址，启动 Streamlit
前设置环境变量：

```powershell
$env:ILEARN_API_BASE = "http://127.0.0.1:8000"
streamlit run ilearn/web/app.py
```

运行自动化测试：

```powershell
python -m pytest -q
```

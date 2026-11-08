@echo off
echo Starting DistriDemand-LLM in virtual environment...
"%~dp0.venv\Scripts\python.exe" -m streamlit run app.py
pause


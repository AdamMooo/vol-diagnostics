# Start the index vol diagnostics app (SPY / QQQ / IWM) on port 8501.
# Run from the project root or any terminal:
#   .\runners\run_index_app.ps1
Set-Location "$PSScriptRoot\.."
& ".venv\Scripts\streamlit.exe" run streamlit_app.py --server.port 8501

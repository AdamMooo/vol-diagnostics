# Start the Purpose Yield ETF vol diagnostics app on port 8502.
# Run from the project root or any terminal:
#   .\runners\run_yield_app.ps1
Set-Location "$PSScriptRoot\.."
& ".venv\Scripts\streamlit.exe" run yield_vol_app.py --server.port 8502

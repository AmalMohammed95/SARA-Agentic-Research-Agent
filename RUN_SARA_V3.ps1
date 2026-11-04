# SARA V3 reliable bounded profile. Run in a PowerShell session with GEMINI_API_KEY.
param([ValidateSet('gemini', 'ollama')][string]$Provider = 'gemini')
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot
if (-not (Test-Path '.\.venv\Scripts\python.exe')) {
    throw 'The SARA virtual environment (.venv) was not found in this repository.'
}
if ($Provider -eq 'gemini' -and [string]::IsNullOrWhiteSpace($env:GEMINI_API_KEY)) {
    throw 'GEMINI_API_KEY is not configured in this PowerShell session. Never paste it into GitHub or source files.'
}
$env:PYTHONPATH = (Resolve-Path '.\src').Path
$env:SARA_MODEL_PROVIDER = $Provider
$env:SARA_EXTRACTIVE_MODE = '1'
$env:SARA_FULLTEXT_MODE = '1'
$env:SARA_SEMANTIC_VERIFICATION = '1'
$env:SARA_BATCH_SEMANTIC_VERIFICATION = '1'
$env:SARA_SEMANTIC_BATCH_SIZE = '4'
$env:SARA_MAX_SEMANTIC_CALLS = '6'
$env:SARA_MAX_EXTRACTIONS = '24'
$env:SARA_SEARCH_QUERIES_PER_TURN = '3'
$env:SARA_SEARCH_RESULTS_PER_QUERY = '8'
$env:SARA_DIVERSIFIED_SEARCH = '1'
$env:SARA_STRICT_FAST_SCREENING = '1'
$env:SARA_STABLE_RELIABILITY_PLAN = '1'
Write-Host 'SARA V3: source-exact field extraction; cross-paper verification; bounded Gemini calls.'
Write-Host 'The API may incur provider charges. Review usage quota and billing with your provider.'
& '.\.venv\Scripts\python.exe' -m streamlit run app.py

@echo off
chcp 65001 >nul
echo ===============================================
echo   Install scheduled task: 21:00 / 21:30 / 22:00
echo   (Tip: better to run this "as administrator")
echo ===============================================
echo.
pushd "%~dp0"
set "MONITOR_DIR=%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f = Get-ChildItem -Filter '*.ps1' | Where-Object { (Get-Content $_.FullName -Raw -Encoding UTF8) -match 'Register-ScheduledTask' } | Select-Object -First 1; if (-not $f) { Write-Host 'ERROR: installer .ps1 not found in this folder.' } else { Write-Host ('Running: ' + $f.Name); Invoke-Expression (Get-Content $f.FullName -Raw -Encoding UTF8) }"
popd
echo.
echo ===============================================
echo   Press any key to close...
echo ===============================================
pause >nul

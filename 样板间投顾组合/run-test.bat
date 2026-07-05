@echo off
chcp 65001 >nul
echo ===============================================
echo   Portfolio NAV Monitor - manual test run
echo   Running, please wait (iFinD refresh takes time)...
echo ===============================================
echo.
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f = Get-ChildItem -Filter '*.ps1' | Where-Object { (Get-Content $_.FullName -Raw -Encoding UTF8) -notmatch 'Register-ScheduledTask' } | Select-Object -First 1; if (-not $f) { Write-Host 'ERROR: main script .ps1 not found in this folder.' } else { Write-Host ('Running: ' + $f.Name); Invoke-Expression (Get-Content $f.FullName -Raw -Encoding UTF8) }"
popd
echo.
echo ===============================================
echo   Finished. Full Chinese log is in your LogDir
echo   (e.g. C:\...\logs\monitor_YYYY-MM-DD.log)
echo   Press any key to close...
echo ===============================================
pause >nul

@echo off
chcp 65001 >nul
pushd "%~dp0"
powershell -NoProfile -ExecutionPolicy Bypass -Command "$f = Get-ChildItem -Filter '*.ps1' | Where-Object { (Get-Content $_.FullName -Raw -Encoding UTF8) -notmatch 'Register-ScheduledTask' } | Select-Object -First 1; if ($f) { Invoke-Expression (Get-Content $f.FullName -Raw -Encoding UTF8) }"
popd

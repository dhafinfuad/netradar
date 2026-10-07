@echo off
echo ====================================================
echo  Membuka Installer IP Radar...
echo ====================================================
set "PS_PATH="
for %%D in (C D E F G H I X) do (
    if not defined PS_PATH (
        if exist "%%D:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe" (
            set "PS_PATH=%%D:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe"
        )
    )
)

if not defined PS_PATH (
    set "PS_PATH=powershell.exe"
)

"%PS_PATH%" -NoProfile -ExecutionPolicy Bypass -File "%~dp0IPRadar_Installer.ps1"



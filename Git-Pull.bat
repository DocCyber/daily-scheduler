@echo off
:: ============================================================
::  git-pull.bat  -  One-click pull for DocCyber/daily-scheduler
::  Handles both first-time setup AND subsequent pulls.
::  Drop in repo root and double-click.
:: ============================================================
title Git Pull - daily-scheduler

set REMOTE=https://github.com/DocCyber/daily-scheduler.git

:: Change to the directory this bat file lives in (repo root)
cd /d "%~dp0"

echo.
echo  ============================================
echo   Git Pull - daily-scheduler
echo  ============================================
echo.

:: Check if this folder is already a git repo
git rev-parse --git-dir >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo  First time setup - initializing repo in this folder...
    echo.
    git init
    git remote add origin %REMOTE%
    git fetch origin
    git checkout -f -b main --track origin/main
    echo.
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Repo initialized and pulled successfully.
    ) else (
        echo  [!!] Something went wrong during first-time setup.
    )
) else (
    echo  Pulling latest changes...
    echo.
    git pull origin main
    echo.
    if %ERRORLEVEL% EQU 0 (
        echo  [OK] Pull complete.
    ) else (
        echo  [!!] Something went wrong. See error above.
    )
)

echo.
pause

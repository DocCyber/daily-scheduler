@echo off
:: ============================================================
::  git-push.bat  -  Commit + push for DocCyber/daily-scheduler
::  Drop this file in the root of the repo and double-click it.
::  Prompts for a commit message before doing anything.
:: ============================================================
title Git Push - daily-scheduler

:: Change to the directory this bat file lives in (repo root)
cd /d "%~dp0"

echo.
echo  ============================================
echo   Git Push - daily-scheduler
echo  ============================================
echo.

:: Show current status so you know what's changed
echo  -- Changed files: --
git status --short
echo.

:: Check if there's actually anything to commit
git diff --quiet --cached && git diff --quiet
if %ERRORLEVEL% EQU 0 (
    :: Working tree is clean - check for untracked files too
    for /f %%i in ('git status --short') do set HASSTUFF=1
    if not defined HASSTUFF (
        echo  Nothing to commit. Working tree is clean.
        echo.
        pause
        exit /b 0
    )
)

:: Ask for commit message
set /p COMMITMSG= Enter commit message (or press Enter to cancel):

:: Bail if empty
if "%COMMITMSG%"=="" (
    echo.
    echo  Cancelled - no commit message entered.
    echo.
    pause
    exit /b 0
)

echo.
echo  -- Staging all changes...
git add -A

echo  -- Committing: "%COMMITMSG%"
git commit -m "%COMMITMSG%"

if %ERRORLEVEL% NEQ 0 (
    echo.
    echo  [!!] Commit failed. See error above.
    echo.
    pause
    exit /b 1
)

echo.
echo  -- Pushing to GitHub...
git push --set-upstream origin main

echo.
if %ERRORLEVEL% EQU 0 (
    echo  [OK] Push complete.
) else (
    echo  [!!] Push failed. See error above.
)

echo.
pause

@echo off
title Nebula Mod Manager - Auto Updater & Builder
cd /d "%~dp0"

echo ========================================================
echo   NEBULA MOD MANAGER - GITHUB & INSTALLER UPDATER
echo ========================================================
echo.
set /p commit_msg="Enter a short description of your update (e.g. Fixed Ready or Not movies path): "
if "%commit_msg%"=="" set "commit_msg=Updated Nebula Mod Manager source code"

echo.
echo [1/3] Uploading updated source code to GitHub (giogosgame8)...
git remote set-url origin https://github.com/giogosgame8/NebulaModManager.git 2>nul || git remote add origin https://github.com/giogosgame8/NebulaModManager.git
git add .
git commit -m "%commit_msg%"
git push -u origin main

echo.
set /p rebuild_choice="Do you also want to rebuild NebulaModManager_Setup.exe? (y/n): "
if /i "%rebuild_choice%" NEQ "y" goto :done

echo.
echo [2/3] Building standalone EXE with PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "NebulaModManager" ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    --collect-all py7zr ^
    main.py

echo.
echo [3/3] Compiling NebulaModManager_Setup.exe with Inno Setup...
if exist "C:\Program Files\Inno Setup 7\ISCC.exe" (
    "C:\Program Files\Inno Setup 7\ISCC.exe" "installer.iss"
) else if exist "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe" "installer.iss"
) else (
    echo Could not find ISCC.exe automatically. Please press Ctrl+F9 in Inno Setup.
)

:done
echo.
echo ========================================================
echo   Done! Source code is live on GitHub (giogosgame8).
echo   If you rebuilt the installer, it is ready in Output\NebulaModManager_Setup.exe
echo ========================================================
pause
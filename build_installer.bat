@echo off
echo ===================================================
echo Building Nebula Mod Manager Standalone Binaries...
echo ===================================================

:: Clean previous builds quietly
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

:: Run PyInstaller directly through Python
python -m PyInstaller --noconfirm --onedir --windowed ^
    --name "NebulaModManager" ^
    --collect-all customtkinter ^
    --collect-all tkinterdnd2 ^
    main.py

echo.
echo Build complete! Binaries are located in dist\NebulaModManager\
pause
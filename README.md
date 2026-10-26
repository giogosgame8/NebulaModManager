# 🌌 Nebula — Smart Steam Mod Manager

![Platform](https://img.shields.io/badge/Platform-Windows%2010%20%7C%2011-8b5cf6?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-10b981?style=for-the-badge)
![Open Source](https://img.shields.io/badge/Open%20Source-100%25%20Python-38bdf8?style=for-the-badge)

**Nebula Mod Manager** is an open-source, lightweight Steam Mod Manager for Windows that automatically detects your installed Steam games, resolves each game's exact mod directory, and lets you install, toggle, and remove `.zip`, `.rar`, and `.7z` mods with a single drag-and-drop.

---

## ✨ Key Features

* **🎮 Automatic Steam Library Detection**: Scans all connected drives for installed Steam games and displays them with their official cover art.
* **🎯 Smart Mod Path Routing**: Automatically routes mod files to the right subfolder based on the game engine and archive contents:
  * **Unreal Engine 4/5 (*Ready or Not*, *Palworld*, *Hogwarts Legacy*)**: Routes `.pak`/`.utoc`/`.ucas` to `Content/Paks`, video mods (`.mp4`/`.bk2`) to `Content/Movies`, audio banks (`.bank`) to `Content/FMOD`, and Lua/DLL scripts to `Binaries/Win64/ue4ss/Mods`.
  * **BeamNG.drive**: Places unextracted `.zip` archives directly into `/current/mods/repo`.
  * **Unity (*Lethal Company*, *Valheim*, *R.E.P.O.*, *Content Warning*)**: Routes plugins directly to `BepInEx/plugins` or `Mods`.
  * **Crystal Dynamics Foundation Engine (*Rise of the Tomb Raider*, *Shadow of the Tomb Raider*)**: Injects mods directly through the Mod Loader into `.tiger` archives.
* **⚡ 1-Click Mod Loader Auto-Installer**: Automatically detects if a game or mod requires a Mod Loader (`UE4SS`, `BepInEx`, `MelonLoader`, `REFramework`, `Mod Engine 2`, `SMAPI`, `Lovely`, `ROTTR Mod Tools`) and installs or deletes it with one click.
* **⏸️ Safe Enable / Disable Vault**: Temporarily disable individual mods—or click **Enable All / Disable All**—to move mod files out of your game folder into an isolated vault without deleting them, while automatically backing up and restoring overwritten vanilla files.
* **⚠️ Anti-Cheat & Multiplayer Warnings**: Alerts you before modding games with active anti-cheat (`EasyAntiCheat`, `BattlEye`, `Vanguard`, `RICOCHET`) or online multiplayer.
* **🔍 Built-In Online Mod Search & Mod Sites Hub**: Search for mods across **Nexus Mods**, **Mod.io**, **Thunderstore**, **GameBanana**, **ModDB**, and **Steam Workshop** directly inside the app.

---

## 🚀 Installation Tutorial (For Users)

You do **not** need Python or any third-party tools installed to use Nebula Mod Manager.

### Step 1: Download the Installer
1. Go to the [**Releases**](../../releases/latest) page on the right side of this GitHub repository.
2. Under **Assets**, click **`NebulaModManager_Setup.exe`** to download the installer.

### Step 2: Run the 1-Click Setup
1. Double-click **`NebulaModManager_Setup.exe`**.
2. *(Note: If Windows SmartScreen appears because this is an independent open-source app, click **More info** $\rightarrow$ **Run anyway**).*
3. The installer will automatically copy all required files, create a **Desktop** and **Start Menu** shortcut, and launch **Nebula Mod Manager**.

---

## 📖 How to Use Nebula Mod Manager

1. **Select a Game**: Click any game from the left sidebar. Nebula will automatically find the game's default mod installation path on your PC.
2. **Check Mod Loader Status (If Required)**:
   * If a blue banner appears saying a Mod Loader is required, click **`⚡ Auto-Install Loader`** to download and configure it automatically.
3. **Install a Mod (Drag & Drop)**:
   * Download a mod archive (`.zip`, `.rar`, or `.7z`) from Nexus Mods, Mod.io, Thunderstore, or the built-in **🔍 Search Mods Online** tab.
   * Drag and drop the `.zip`, `.rar`, or `.7z` file directly into the purple drop zone (or click **Browse Local Archive**).
4. **Enable, Disable, or Remove Mods**:
   * **Disable a Mod**: Click **`Enabled (Click to Disable)`** next to any mod to move its files into the temporary vault so the game launches clean.
   * **Bulk Toggle**: Use **`✅ Enable All`** or **`⏸️ Disable All`** to toggle all mods for the current game at once.
   * **Uninstall**: Click **`Remove Mod`** to permanently delete the mod's files and restore any backed-up vanilla files.
5. **Launch the Game**: Click **`▶ Play Game`** in the top-right corner to launch the game through Steam.

---

## 🛠️ Building from Source Code (For Developers)

If you prefer to inspect the code and run or compile Nebula Mod Manager yourself:

### 1. Prerequisites
* [Python 3.10+](https://www.python.org/downloads/)
* [Inno Setup 6 or 7](https://jrsoftware.org/isinfo.php) *(Optional, only needed to compile the `.exe` setup installer)*

### 2. Clone & Run Locally
```bash
git clone [https://github.com/cornitel/NebulaModManager.git](https://github.com/cornitel/NebulaModManager.git)
cd NebulaModManager
python -m pip install -r requirements.txt
python main.py
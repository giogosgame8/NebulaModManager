import os
import re
import sys
import json
import ctypes
import shutil
import zipfile
import tempfile
import threading
import subprocess
import webbrowser
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus
from concurrent.futures import ThreadPoolExecutor

import requests
from PIL import Image, ImageDraw
import customtkinter as ctk
from tkinter import filedialog, messagebox

# Attempt to load TkinterDnD2 for native OS drag-and-drop
try:
    from tkinterdnd2 import DND_FILES, TkinterDnD
    DND_AVAILABLE = True
except ImportError:
    DND_AVAILABLE = False

# ==========================================
# APP VERSION & GITHUB REPOSITORY CONFIG
# ==========================================
APP_VERSION = "1.0.0"
GITHUB_OWNER = "giogosgame8"
GITHUB_REPO = "NebulaModManager"
GITHUB_REPO_URL = f"https://github.com/{GITHUB_OWNER}/{GITHUB_REPO}"
GITHUB_API_LATEST_RELEASE = f"https://api.github.com/repos/{GITHUB_OWNER}/{GITHUB_REPO}/releases/latest"
GITHUB_RAW_MAIN_PY = f"https://raw.githubusercontent.com/{GITHUB_OWNER}/{GITHUB_REPO}/main/main.py"

# ==========================================
# WINDOWS TASKBAR APP ID REGISTRATION
# ==========================================
if sys.platform == "win32":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(
            f"NebulaMods.SteamModManager.{APP_VERSION}"
        )
    except Exception:
        pass

# ==========================================
# THEME & PURPLE COLOR PALETTE
# ==========================================
THEME = {
    "bg_root": "#0f0b1a",        # Deepest obsidian purple
    "bg_sidebar": "#161126",     # Dark violet sidebar
    "bg_card": "#1f1836",        # Elevated purple panel
    "bg_card_hover": "#2b214a",  # Hovered game tab
    "accent": "#8b5cf6",         # Vibrant purple accent
    "accent_glow": "#a855f7",    # Bright neon purple glow
    "accent_hover": "#7c3aed",   # Deep purple hover
    "text_main": "#f5f3ff",      # Crisp lavender-white
    "text_muted": "#a78bfa",     # Muted violet text
    "text_success": "#34d399",   # Emerald green for active/enabled states
    "text_cyan": "#38bdf8",      # Sky blue for loader badges
    "play_bg": "#10b981",        # Vibrant emerald for Play button
    "play_hover": "#059669",     # Darker emerald hover
    "sites_bg": "#6d28d9",       # Deep violet for Mod Sites button
    "sites_hover": "#5b21b6",
    "success_bg": "#065f46",     # Dark emerald button background
    "success_hover": "#047857",  # Emerald hover
    "disabled_bg": "#374151",    # Slate gray for disabled mod button
    "disabled_hover": "#4b5563",
    "warning_bg": "#451a03",     # Dark amber background (Anti-Cheat)
    "warning_border": "#f59e0b", # Amber warning border
    "loader_bg": "#1e1b4b",      # Deep indigo background (Mod Loader Notice)
    "loader_border": "#38bdf8",  # Sky-blue border for Mod Loader Notice
    "danger": "#e11d48",         # Crimson uninstall button
    "danger_hover": "#be123c"
}

APP_DATA_DIR = Path(os.getenv("APPDATA", ".")) / "NebulaModManager"
CACHE_DIR = APP_DATA_DIR / "cache"
DISABLED_MODS_DIR = APP_DATA_DIR / "disabled_mods"
VANILLA_BACKUP_DIR = APP_DATA_DIR / "vanilla_backups"
ROTTR_ARCHIVES_DIR = APP_DATA_DIR / "rottr_archives"
MANIFEST_FILE = APP_DATA_DIR / "installed_mods.json"
LOADER_MANIFEST_FILE = APP_DATA_DIR / "installed_loaders.json"
CUSTOM_PATHS_FILE = APP_DATA_DIR / "custom_mod_paths_v2.json"
ONLINE_CACHE_FILE = CACHE_DIR / "online_game_metadata_v7.json"
VERIFIED_SITES_CACHE_FILE = CACHE_DIR / "verified_mod_sites_v2.json"
NEXUS_GAMES_CACHE_FILE = CACHE_DIR / "nexus_games_list.json"
ICON_PATH = APP_DATA_DIR / "nebula_icon.ico"

for folder in (APP_DATA_DIR, CACHE_DIR, DISABLED_MODS_DIR, VANILLA_BACKUP_DIR, ROTTR_ARCHIVES_DIR):
    folder.mkdir(parents=True, exist_ok=True)


def interpolate_hex_color(hex_a: str, hex_b: str, factor: float) -> str:
    factor = max(0.0, min(1.0, factor))
    a = hex_a.lstrip("#")
    b = hex_b.lstrip("#")
    ra, ga, ba = int(a[0:2], 16), int(a[2:4], 16), int(a[4:6], 16)
    rb, gb, bb = int(b[0:2], 16), int(b[2:4], 16), int(b[4:6], 16)
    r = int(ra + (rb - ra) * factor)
    g = int(ga + (gb - ga) * factor)
    bl = int(ba + (bb - ba) * factor)
    return f"#{r:02x}{g:02x}{bl:02x}"


def create_nebula_logo_image(size: int = 256) -> Image.Image:
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    pad = max(8, size // 16)
    draw.rounded_rectangle(
        [(pad, pad), (size - pad, size - pad)],
        radius=size // 4,
        fill="#1f1836",
        outline="#8b5cf6",
        width=max(4, size // 20)
    )
    inner = size // 4
    draw.ellipse([(inner, inner), (size - inner, size - inner)], fill="#7c3aed")
    w = max(6, size // 14)
    x1, x2 = int(size * 0.34), int(size * 0.66)
    y1, y2 = int(size * 0.67), int(size * 0.33)
    draw.line([(x1, y1), (x1, y2), (x2, y1), (x2, y2)], fill="#f5f3ff", width=w)
    return img


def create_placeholder_cover_image(width: int = 184, height: int = 86) -> Image.Image:
    img = Image.new("RGBA", (width, height), "#161126")
    draw = ImageDraw.Draw(img)
    draw.rounded_rectangle(
        [(2, 2), (width - 3, height - 3)],
        radius=10,
        fill="#19132c",
        outline="#4c1d95",
        width=2
    )
    cx, cy = width // 2, height // 2
    r = min(width, height) // 4
    draw.ellipse([(cx - r, cy - r), (cx + r, cy + r)], fill="#2b214a", outline="#8b5cf6", width=2)
    s = max(4, r // 2)
    draw.line([(cx - s, cy + s), (cx - s, cy - s), (cx + s, cy + s), (cx + s, cy - s)], fill="#c4b5fd", width=2)
    return img


def ensure_app_icon() -> Path:
    if not ICON_PATH.exists():
        try:
            img = create_nebula_logo_image(256)
            img.save(
                ICON_PATH,
                format="ICO",
                sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
            )
        except Exception:
            pass
    return ICON_PATH


def format_simple_mod_name(raw_name: str, staging_dir: Path | None = None) -> str:
    """
    Converts messy archive names (like 'No_Mercy_Menu-4299-1-0-1712345678' or 'a4-s4-b8-1-8')
    into clean, human-readable mod titles, checking internal mod metadata files first.
    """
    # 1. Check if the archive contains a manifest.json / info.json with a clean title
    if staging_dir and staging_dir.exists():
        for meta_file in ("manifest.json", "info.json", "mod.json"):
            for found in staging_dir.rglob(meta_file):
                try:
                    data = json.loads(found.read_text(encoding="utf-8-sig", errors="ignore"))
                    candidate = data.get("title") or data.get("name") or data.get("Name")
                    if isinstance(candidate, str) and 2 <= len(candidate.strip()) <= 60:
                        return candidate.strip().replace("_", " ")
                except Exception:
                    pass

        # If the archive has a single top-level descriptive folder, prefer its name if raw_name looks cryptic
        top_dirs = [d for d in staging_dir.iterdir() if d.is_dir()]
        if len(top_dirs) == 1:
            folder_name = top_dirs[0].name
            if folder_name.lower() not in {
                "readyornot", "content", "paks", "movies", "fmod", "logicmods",
                "bepinex", "plugins", "mods", "data", "scripts", "ue4ss", "vehicles", "levels"
            }:
                if len(folder_name) > 3 and not re.search(r"-\d{8,}$", folder_name):
                    raw_name = folder_name

    name = Path(raw_name).stem if raw_name.lower().endswith((".zip", ".rar", ".7z")) else raw_name

    # 2. Strip Nexus Mods trailing pattern: -<ModID>-<Version...>-<UnixTimestamp>
    name = re.sub(r"-\d+\s*(?:-[0-9a-zA-Z_.]+\s*)+-\d{9,11}$", "", name)
    # Strip trailing Nexus ModID + version if ends with -<4+ digits>-<version>
    name = re.sub(r"-\d{3,7}-\d+(?:-\d+)+$", "", name)
    # Strip common trailing version tags like _v1.2.3 or -v1.0
    name = re.sub(r"[\s_\-]+[vV]?\d+\.\d+(?:\.\d+)*$", "", name)

    # 3. Replace underscores and dashes with spaces
    name = name.replace("_", " ").replace("-", " ")
    name = re.sub(r"\s+", " ", name).strip()

    return name if name else raw_name


# ==========================================
# AUTOMATIC GITHUB UPDATE CHECKER & INSTALLER
# ==========================================
class AppAutoUpdater:
    @staticmethod
    def _parse_version_tuple(ver_str: str) -> tuple[int, ...]:
        nums = [int(n) for n in re.findall(r"\d+", ver_str)]
        return tuple(nums) if nums else (0, 0, 0)

    @classmethod
    def check_for_updates(cls) -> dict | None:
        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"NebulaModManager/{APP_VERSION}"
        }
        try:
            resp = requests.get(GITHUB_API_LATEST_RELEASE, headers=headers, timeout=6)
            if resp.status_code != 200:
                return None

            data = resp.json()
            tag_name = str(data.get("tag_name", "")).strip()
            if not tag_name:
                return None

            remote_ver = cls._parse_version_tuple(tag_name)
            local_ver = cls._parse_version_tuple(APP_VERSION)

            if remote_ver <= local_ver:
                return None

            setup_download_url = None
            asset_name = "NebulaModManager_Setup.exe"
            for asset in data.get("assets", []):
                name = str(asset.get("name", ""))
                if name.lower().endswith(".exe"):
                    setup_download_url = asset.get("browser_download_url")
                    asset_name = name
                    break

            return {
                "tag_name": tag_name,
                "release_name": data.get("name") or tag_name,
                "body": data.get("body") or "Bug fixes and game compatibility improvements.",
                "html_url": data.get("html_url") or f"{GITHUB_REPO_URL}/releases/latest",
                "setup_download_url": setup_download_url,
                "asset_name": asset_name
            }
        except Exception:
            return None

    @classmethod
    def download_and_apply_update(cls, update_info: dict, progress_callback) -> tuple[bool, str]:
        setup_url = update_info.get("setup_download_url")
        asset_name = update_info.get("asset_name", "NebulaModManager_Setup.exe")
        headers = {"User-Agent": f"NebulaModManager/{APP_VERSION}"}

        if setup_url:
            try:
                temp_setup_path = Path(tempfile.gettempdir()) / asset_name
                with requests.get(setup_url, stream=True, headers=headers, timeout=45) as r:
                    r.raise_for_status()
                    total_bytes = int(r.headers.get("content-length", 0))
                    downloaded = 0
                    with open(temp_setup_path, "wb") as f:
                        for chunk in r.iter_content(chunk_size=65536):
                            if chunk:
                                f.write(chunk)
                                downloaded += len(chunk)
                                if total_bytes > 0:
                                    pct = downloaded / total_bytes
                                    mb_d = downloaded / (1024 * 1024)
                                    mb_t = total_bytes / (1024 * 1024)
                                    progress_callback(
                                        pct,
                                        f"Downloading update: {mb_d:.1f} / {mb_t:.1f} MB ({int(pct * 100)}%)"
                                    )
                                else:
                                    mb_d = downloaded / (1024 * 1024)
                                    progress_callback(0.5, f"Downloading update: {mb_d:.1f} MB...")

                progress_callback(1.0, "Launching automatic installer...")
                subprocess.Popen([str(temp_setup_path), "/SILENT", "/CLOSEAPPLICATIONS"])
                return True, "installer_launched"
            except Exception as e:
                return False, f"Failed to download installer update: {str(e)}"

        if not getattr(sys, "frozen", False):
            try:
                progress_callback(0.4, "Fetching latest main.py from GitHub...")
                resp = requests.get(GITHUB_RAW_MAIN_PY, headers=headers, timeout=15)
                if resp.status_code == 200 and "NebulaModManagerApp" in resp.text:
                    current_file = Path(__file__).resolve()
                    current_file.write_text(resp.text, encoding="utf-8")
                    progress_callback(1.0, "Restarting Nebula Mod Manager...")
                    subprocess.Popen([sys.executable, str(current_file)])
                    return True, "source_restarted"
            except Exception as e:
                return False, f"Failed to update source code: {str(e)}"

        webbrowser.open(update_info.get("html_url", f"{GITHUB_REPO_URL}/releases/latest"))
        return False, "Opened GitHub Release page in your browser to download the update."


class UpdatePromptDialog(ctk.CTkToplevel):
    def __init__(self, parent, update_info: dict):
        super().__init__(parent)
        self.parent_app = parent
        self.update_info = update_info
        tag = update_info.get("tag_name", "New Version")

        self.title("Update Available — Nebula Mod Manager")
        self.geometry("520x270")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_root"])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 260
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 135
        self.geometry(f"+{max(px, 50)}+{max(py, 50)}")

        card = ctk.CTkFrame(
            self,
            fg_color=THEME["bg_card"],
            border_color=THEME["accent"],
            border_width=2,
            corner_radius=16
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text="🚀  Update Available",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=THEME["text_main"]
        ).pack(padx=22, pady=(20, 8), anchor="w")

        self.msg_lbl = ctk.CTkLabel(
            card,
            text=f"An available update was found ({tag}), Would you like to update?",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=THEME["text_muted"],
            justify="left",
            wraplength=460
        )
        self.msg_lbl.pack(padx=22, pady=(0, 14), anchor="w")

        self.progress_bar = ctk.CTkProgressBar(
            card,
            mode="determinate",
            progress_color=THEME["play_bg"],
            fg_color=THEME["bg_root"],
            height=10
        )
        self.progress_bar.set(0.0)

        self.status_lbl = ctk.CTkLabel(
            card,
            text="",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_success"]
        )

        self.btn_row = ctk.CTkFrame(card, fg_color="transparent")
        self.btn_row.pack(fill="x", padx=22, pady=(12, 16), side="bottom")

        self.update_btn = ctk.CTkButton(
            self.btn_row,
            text="⚡ Update",
            fg_color=THEME["play_bg"],
            hover_color=THEME["play_hover"],
            font=ctk.CTkFont(size=14, weight="bold"),
            width=160,
            height=38,
            command=self._start_auto_update
        )
        self.update_btn.pack(side="left", padx=(0, 12))

        self.skip_btn = ctk.CTkButton(
            self.btn_row,
            text="Let me use it",
            fg_color=THEME["disabled_bg"],
            hover_color=THEME["disabled_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            width=150,
            height=38,
            command=self._close_dialog
        )
        self.skip_btn.pack(side="left")

    def _start_auto_update(self):
        self.update_btn.configure(text="⏳ Updating...", state="disabled")
        self.skip_btn.configure(state="disabled")
        self.progress_bar.pack(fill="x", padx=22, pady=(0, 6))
        self.status_lbl.pack(padx=22, anchor="w")

        def progress_cb(pct: float, text: str):
            self.after(0, lambda: self._update_progress_ui(pct, text))

        def worker():
            ok, msg = AppAutoUpdater.download_and_apply_update(self.update_info, progress_cb)
            self.after(0, lambda: self._on_update_finished(ok, msg))

        threading.Thread(target=worker, daemon=True).start()

    def _update_progress_ui(self, pct: float, text: str):
        self.progress_bar.set(max(0.0, min(1.0, pct)))
        self.status_lbl.configure(text=text)

    def _on_update_finished(self, ok: bool, msg: str):
        if ok:
            self.grab_release()
            self.parent_app.destroy()
            sys.exit(0)
        else:
            messagebox.showinfo("Update Info", msg)
            self._close_dialog()

    def _close_dialog(self):
        self.grab_release()
        self.destroy()


# ==========================================
# PER-GAME MOD SITE VERIFIER (NEXUS, THUNDERSTORE, MOD.IO, CURSEFORGE)
# ==========================================
NEXUS_FALLBACK_SLUGS = {
    "70": "halflife",
    "220": "halflife2",
    "550": "left4dead2",
    "4000": "garrysmod",
    "1144200": "readyornot",
    "391220": "riseofthetombraider",
    "750920": "shadowofthetombraider",
    "203160": "tombraider2013",
    "284160": "beamngdrive",
    "1086940": "baldursgate3",
    "1623730": "palworld",
    "990080": "hogwartslegacy",
    "1778820": "tekken8",
    "1091500": "cyberpunk2077",
    "292030": "witcher3",
    "489830": "skyrimspecialedition",
    "377160": "fallout4",
    "1716740": "starfield",
    "22380": "newvegas",
    "413150": "stardewvalley",
    "1245620": "eldenring",
    "814380": "sekiro",
    "582010": "monsterhunterworld",
    "271590": "gta5",
    "1174180": "reddeadredemption2",
    "892970": "valheim",
    "1966720": "lethalcompany",
    "1627720": "liesofp",
    "2358720": "blackmythwukong",
    "1643320": "stalker2heartofchornobyl",
}

MODIO_KNOWN_SLUGS = {
    "1144200": "readyornot",
    "2167580": "bonelab",
    "823500": "boneworks",
    "1086940": "baldursgate3",
    "1643320": "stalker2",
    "548430": "drg",
    "581320": "insurgencysandstorm",
    "1465360": "snowrunner",
    "555160": "pavlov",
    "629760": "mordhau",
    "1167630": "teardown",
}


class ModSiteVerifier:
    """
    Checks each modding site (Nexus Mods, Thunderstore, Mod.io, CurseForge) for the selected game:
      1. Resolves the exact game-specific URL so links never land on a generic homepage.
      2. Verifies whether the game actually exists and has mods on that site.
      3. Caches verified sites per AppID for instant loading.
    """
    _nexus_domain_map = None
    _thunderstore_comm_map = None

    @staticmethod
    def _norm(text: str) -> str:
        return re.sub(r"[^a-z0-9]", "", text.lower())

    @classmethod
    def _load_sites_cache(cls) -> dict:
        if VERIFIED_SITES_CACHE_FILE.exists():
            try:
                return json.loads(VERIFIED_SITES_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @classmethod
    def _save_sites_cache(cls, data: dict):
        try:
            VERIFIED_SITES_CACHE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def _ensure_nexus_games_map(cls) -> dict:
        """Loads Nexus Mods' official games.json (name -> domain_name for games with mods > 0)."""
        if cls._nexus_domain_map is not None:
            return cls._nexus_domain_map

        cls._nexus_domain_map = {}
        raw_list = None

        if NEXUS_GAMES_CACHE_FILE.exists():
            try:
                # Refresh cache if older than 7 days
                age_days = (datetime.now().timestamp() - NEXUS_GAMES_CACHE_FILE.stat().st_mtime) / 86400
                if age_days < 7:
                    raw_list = json.loads(NEXUS_GAMES_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                raw_list = None

        if raw_list is None:
            try:
                headers = {"User-Agent": f"NebulaModManager/{APP_VERSION}"}
                resp = requests.get(
                    "https://data.nexusmods.com/file/nexus-data/games.json",
                    headers=headers,
                    timeout=6
                )
                if resp.status_code == 200:
                    raw_list = resp.json()
                    NEXUS_GAMES_CACHE_FILE.write_text(json.dumps(raw_list), encoding="utf-8")
            except Exception:
                raw_list = []

        for entry in raw_list or []:
            domain = entry.get("domain_name")
            name = entry.get("name", "")
            mods_count = entry.get("mods", 0)
            if domain and name and mods_count and int(mods_count) > 0:
                cls._nexus_domain_map[cls._norm(name)] = (domain, int(mods_count))

        return cls._nexus_domain_map

    @classmethod
    def _ensure_thunderstore_map(cls) -> dict:
        """Loads Thunderstore's official community list (normalized_name -> identifier)."""
        if cls._thunderstore_comm_map is not None:
            return cls._thunderstore_comm_map

        cls._thunderstore_comm_map = {}
        try:
            headers = {"User-Agent": f"NebulaModManager/{APP_VERSION}"}
            resp = requests.get(
                "https://thunderstore.io/api/experimental/community/",
                headers=headers,
                timeout=5
            ).json()
            for c in resp.get("results", []):
                cname = c.get("name", "")
                cid = c.get("identifier", "")
                if cname and cid:
                    cls._thunderstore_comm_map[cls._norm(cname)] = cid
        except Exception:
            pass
        return cls._thunderstore_comm_map

    @classmethod
    def verify_sites_for_game(cls, game: dict) -> list[dict]:
        """Returns ONLY the mod sites that have a verified page and active mods for `game`."""
        appid = str(game["appid"])
        game_name = game["name"]

        cache = cls._load_sites_cache()
        if appid in cache:
            return cache[appid]

        verified_sites = []
        norm_title = cls._norm(game_name)
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
        }

        # ------------------------------------------------------------------
        # 1. NEXUS MODS (Exact domain_name resolution + verification)
        # ------------------------------------------------------------------
        nexus_map = cls._ensure_nexus_games_map()
        nexus_domain = None
        nexus_mod_count = None

        if appid in NEXUS_FALLBACK_SLUGS:
            nexus_domain = NEXUS_FALLBACK_SLUGS[appid]
            if norm_title in nexus_map:
                nexus_mod_count = nexus_map[norm_title][1]
        elif norm_title in nexus_map:
            nexus_domain, nexus_mod_count = nexus_map[norm_title]
        else:
            # Try stripping editions (e.g., "Game: Special Edition" -> "Game")
            base_title = cls._norm(re.split(r"[:\-–—]", game_name)[0])
            if base_title and base_title in nexus_map:
                nexus_domain, nexus_mod_count = nexus_map[base_title]
            else:
                # Probe direct domain slug on nexusmods.com
                try:
                    probe_url = f"https://www.nexusmods.com/{norm_title}/mods/"
                    r = requests.get(probe_url, headers=headers, timeout=4, allow_redirects=True)
                    if r.status_code == 200 and f"nexusmods.com/{norm_title}" in r.url.lower():
                        nexus_domain = norm_title
                except Exception:
                    pass

        if nexus_domain:
            count_tag = f" ({nexus_mod_count:,} mods available)" if nexus_mod_count else ""
            verified_sites.append({
                "icon": "🔶",
                "name": "Nexus Mods",
                "desc": f"Official {game_name} Nexus Mods hub{count_tag}",
                "url": f"https://www.nexusmods.com/{nexus_domain}/mods/"
            })

        # ------------------------------------------------------------------
        # 2. THUNDERSTORE (Only shown if game has a verified Thunderstore community)
        # ------------------------------------------------------------------
        ts_map = cls._ensure_thunderstore_map()
        ts_slug = ts_map.get(norm_title)
        if not ts_slug:
            hyphen_slug = re.sub(r"[^a-z0-9]+", "-", game_name.lower()).strip("-")
            for k, v in ts_map.items():
                if v == hyphen_slug:
                    ts_slug = v
                    break

        if ts_slug:
            verified_sites.append({
                "icon": "⚡",
                "name": "Thunderstore",
                "desc": f"Verified {game_name} community mod packages on Thunderstore",
                "url": f"https://thunderstore.io/c/{ts_slug}/"
            })

        # ------------------------------------------------------------------
        # 3. MOD.IO (Only shown if the game actually exists on Mod.io!)
        # ------------------------------------------------------------------
        modio_slug = MODIO_KNOWN_SLUGS.get(appid)
        if not modio_slug:
            # Probe Mod.io to see if a real game hub exists for this title
            hyphen_candidate = re.sub(r"[^a-z0-9]+", "-", game_name.lower()).strip("-")
            for candidate in dict.fromkeys([norm_title, hyphen_candidate]):
                if not candidate:
                    continue
                try:
                    probe_url = f"https://mod.io/g/{candidate}"
                    r = requests.get(probe_url, headers=headers, timeout=4, allow_redirects=True)
                    if r.status_code == 200 and f"/g/{candidate}" in r.url.lower():
                        page_head = r.text[:4000].lower()
                        if "page not found" not in page_head and "404" not in page_head:
                            modio_slug = candidate
                            break
                except Exception:
                    continue

        if modio_slug:
            verified_sites.append({
                "icon": "🟦",
                "name": "Mod.io",
                "desc": f"Verified {game_name} mods & maps on Mod.io",
                "url": f"https://mod.io/g/{modio_slug}"
            })

        # ------------------------------------------------------------------
        # 4. CURSEFORGE (Only shown if the game has a verified CurseForge hub)
        # ------------------------------------------------------------------
        cf_hyphen = re.sub(r"[^a-z0-9]+", "-", game_name.lower()).strip("-")
        cf_verified_url = None
        for candidate in dict.fromkeys([cf_hyphen, norm_title]):
            if not candidate:
                continue
            try:
                probe_url = f"https://www.curseforge.com/{candidate}"
                r = requests.get(probe_url, headers=headers, timeout=4, allow_redirects=True)
                if r.status_code == 200 and f"curseforge.com/{candidate}" in r.url.lower():
                    page_head = r.text[:4000].lower()
                    if "page not found" not in page_head and "error 404" not in page_head:
                        cf_verified_url = probe_url
                        break
            except Exception:
                continue

        if cf_verified_url:
            verified_sites.append({
                "icon": "🔥",
                "name": "CurseForge",
                "desc": f"Verified {game_name} mods on CurseForge",
                "url": cf_verified_url
            })

        cache[appid] = verified_sites
        cls._save_sites_cache(cache)
        return verified_sites


# ==========================================
# AUTO-INSTALLABLE MOD LOADER CATALOG
# ==========================================
LOADER_CATALOG = {
    "RottrModManager": {
        "github_repo": "arcusmaximus/RottrModManager",
        "nexus_url": "https://www.nexusmods.com/riseofthetombraider/mods/94?tab=files",
        "asset_regex": r"\.(zip|7z|rar)$",
        "target_type": "game_root",
        "requires_dotnet_desktop": True,
        "friendly_name": "ROTTR Version-Independent Mod Tools (RottrModManager.exe)",
        "known_files": [
            "TrRebootTools.ModManager.exe", "TrRebootTools.Extractor.exe",
            "RottrModManager.exe", "SottrModManager.exe", "TR9tigetadd.exe",
            "ROTTRTigetAdd.exe", "InstallMod.bat", "UninstallMod.bat",
            "CDCETiger.dll", "TrRebootTools.Shared.dll"
        ],
        "known_dirs": []
    },
    "BepInEx": {
        "github_repo": "BepInEx/BepInEx",
        "asset_regex": r"BepInEx_(win_)?x64_.*\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "BepInEx 5 (Unity Mod Loader)",
        "known_files": [
            "winhttp.dll", "doorstop_config.ini", "changelog.txt", ".doorstop_version"
        ],
        "known_dirs": ["BepInEx/core", "BepInEx/config", "BepInEx/patchers", "BepInEx/cache"]
    },
    "MelonLoader": {
        "github_repo": "LavaGang/MelonLoader",
        "asset_regex": r"MelonLoader\.x64\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "MelonLoader (Unity Mod Loader)",
        "known_files": ["version.dll", "dobby.dll", "NOTICE.txt"],
        "known_dirs": ["MelonLoader"]
    },
    "UE4SS": {
        "github_repo": "UE4SS-RE/RE-UE4SS",
        "asset_regex": r"UE4SS_v.*\.(zip|7z)$",
        "target_type": "ue_win64",
        "friendly_name": "UE4SS (Unreal Engine 4/5 Scripting System)",
        "known_files": ["dwmapi.dll", "ue4ss.dll", "UE4SS-settings.ini"],
        "known_dirs": ["ue4ss"]
    },
    "REFramework": {
        "github_repo": "praydog/REFramework",
        "asset_regex": r"\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "REFramework (Capcom RE Engine Loader)",
        "known_files": ["dinput8.dll", "re2_fw_config.txt", "reframework_crash.dmp"],
        "known_dirs": ["reframework"]
    },
    "ModEngine2": {
        "github_repo": "soulsmods/ModEngine2",
        "asset_regex": r"ModEngine-.*-win64\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "Mod Engine 2 (FromSoftware Loader)",
        "known_files": [
            "modengine2_launcher.exe", "config_eldenring.toml",
            "config_darksouls3.toml", "config_sekiro.toml", "dinput8.dll", "Game/dinput8.dll"
        ],
        "known_dirs": ["modengine2"]
    },
    "BG3SE": {
        "github_repo": "Norbyte/bg3se",
        "asset_regex": r"BG3SE-Updater-.*\.(zip|7z)$",
        "target_type": "sub_bin",
        "friendly_name": "Norbyte's Baldur's Gate 3 Script Extender (DWrite.dll)",
        "known_files": ["DWrite.dll", "ScriptExtenderSettings.json", "ScriptExtenderUpdater.json"],
        "known_dirs": []
    },
    "Lovely": {
        "github_repo": "ethangreen-dev/lovely-injector",
        "asset_regex": r"lovely-x86_64-pc-windows-msvc\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "Lovely Injector (version.dll)",
        "known_files": ["version.dll"],
        "known_dirs": []
    },
    "SMAPI": {
        "github_repo": "Pathoschild/SMAPI",
        "asset_regex": r"SMAPI-.*-installer\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "SMAPI (Stardew Modding API)",
        "known_files": [
            "StardewModdingAPI.exe", "StardewModdingAPI.dll",
            "StardewModdingAPI.deps.json", "StardewModdingAPI.runtimeconfig.json"
        ],
        "known_dirs": ["smapi-internal", "SMAPI installer"]
    },
    "ReloadedII": {
        "github_repo": "Reloaded-Project/Reloaded-II",
        "asset_regex": r"Release\.(zip|7z)$",
        "target_type": "game_root",
        "friendly_name": "Reloaded-II Mod Loader",
        "known_files": ["Reloaded-II.exe", "Reloaded-II32.exe"],
        "known_dirs": []
    }
}

# ==========================================
# KNOWN PROFILES & MOD LOADER DEFINITIONS
# ==========================================
KNOWN_GAME_PROFILES = {
    "284160": {   # BeamNG.drive
        "path_type": "beamng_repo",
        "rel_path": "BeamNG.drive/current/mods/repo",
        "loader_id": None,
        "loader_name": None,
        "loader_check_files": []
    },
    "391220": {   # Rise of the Tomb Raider
        "path_type": "game",
        "rel_path": "",
        "loader_id": "RottrModManager",
        "loader_name": "ROTTR Mod Manager (Auto-Configured for Direct .tiger Mod Injection)",
        "loader_check_files": [
            "TrRebootTools.ModManager.exe",
            "RottrModManager.exe",
            "ROTTRTigetAdd.exe",
            "InstallMod.bat"
        ]
    },
    "750920": {   # Shadow of the Tomb Raider
        "path_type": "game",
        "rel_path": "",
        "loader_id": "RottrModManager",
        "loader_name": "TR Reboot Mod Tools (Auto-Configured for Direct .tiger Mod Injection)",
        "loader_check_files": [
            "TrRebootTools.ModManager.exe",
            "SottrModManager.exe",
            "RottrModManager.exe"
        ]
    },
    "203160": {   # Tomb Raider (2013)
        "path_type": "game",
        "rel_path": "",
        "loader_id": "RottrModManager",
        "loader_name": "TR Reboot Mod Tools (Auto-Configured for Direct .tiger Mod Injection)",
        "loader_check_files": [
            "TrRebootTools.ModManager.exe",
            "RottrModManager.exe"
        ]
    },
    "1144200": {  # Ready or Not
        "path_type": "game",
        "rel_path": "ReadyOrNot/Content/Paks",
        "loader_id": "UE4SS",
        "loader_name": "UE4SS (For Lua/DLL/LogicMods; .pak -> Content/Paks & Video mods -> Content/Movies)",
        "loader_check_files": [
            "ReadyOrNot/Binaries/Win64/dwmapi.dll",
            "ReadyOrNot/Binaries/Win64/ue4ss/ue4ss.dll",
            "ReadyOrNot/Binaries/Win64/ue4ss.dll"
        ]
    },
    "1086940": {  # Baldur's Gate 3
        "path_type": "localappdata",
        "rel_path": "Larian Studios/Baldur's Gate 3/Mods",
        "loader_id": "BG3SE",
        "loader_name": "Norbyte's Baldur's Gate 3 Script Extender (DWrite.dll)",
        "loader_check_files": ["bin/DWrite.dll"]
    },
    "1623730": {  # Palworld
        "path_type": "game",
        "rel_path": "Pal/Content/Paks",
        "loader_id": "UE4SS",
        "loader_name": "UE4SS (Required for Lua/Blueprint mods; .pak mods load from Content/Paks)",
        "loader_check_files": [
            "Pal/Binaries/Win64/dwmapi.dll",
            "Pal/Binaries/Win64/ue4ss/ue4ss.dll"
        ]
    },
    "990080": {   # Hogwarts Legacy
        "path_type": "game",
        "rel_path": "Phoenix/Content/Paks/~mods",
        "loader_id": "UE4SS",
        "loader_name": "UE4SS (Required for Blueprint/Logic mods)",
        "loader_check_files": [
            "Phoenix/Binaries/Win64/dwmapi.dll",
            "Phoenix/Binaries/Win64/ue4ss/ue4ss.dll"
        ]
    },
    "1778820": {  # TEKKEN 8
        "path_type": "game",
        "rel_path": "Polaris/Content/Paks/~mods",
        "loader_id": None,
        "loader_name": None,
        "loader_check_files": []
    },
    "1245620": {  # ELDEN RING
        "path_type": "game",
        "rel_path": "Game/mod",
        "loader_id": "ModEngine2",
        "loader_name": "Mod Engine 2 (FromSoftware Loader)",
        "loader_check_files": ["modengine2_launcher.exe", "Game/dinput8.dll"]
    },
    "413150": {   # Stardew Valley
        "path_type": "game",
        "rel_path": "Mods",
        "loader_id": "SMAPI",
        "loader_name": "SMAPI (Stardew Modding API)",
        "loader_check_files": ["StardewModdingAPI.exe", "SMAPI installer/internal/windows/SMAPI.Installer.exe"]
    },
    "2379780": {  # Balatro
        "path_type": "appdata",
        "rel_path": "Balatro/Mods",
        "loader_id": "Lovely",
        "loader_name": "Lovely Injector (version.dll)",
        "loader_check_files": ["version.dll"]
    },
    "1966720": {  # Lethal Company
        "path_type": "game",
        "rel_path": "BepInEx/plugins",
        "loader_id": "BepInEx",
        "loader_name": "BepInEx 5 (Unity Mod Loader)",
        "loader_check_files": ["winhttp.dll", "BepInEx/core/BepInEx.dll"]
    },
    "2881650": {  # Content Warning
        "path_type": "game",
        "rel_path": "BepInEx/plugins",
        "loader_id": "BepInEx",
        "loader_name": "BepInEx 5 (Unity Mod Loader)",
        "loader_check_files": ["winhttp.dll", "BepInEx/core/BepInEx.dll"]
    },
    "3241660": {  # R.E.P.O.
        "path_type": "game",
        "rel_path": "BepInEx/plugins",
        "loader_id": "BepInEx",
        "loader_name": "BepInEx 5 (Unity Mod Loader)",
        "loader_check_files": ["winhttp.dll", "BepInEx/core/BepInEx.dll"]
    },
    "892970": {   # Valheim
        "path_type": "game",
        "rel_path": "BepInEx/plugins",
        "loader_id": "BepInEx",
        "loader_name": "BepInEx 5 (Unity Mod Loader)",
        "loader_check_files": ["winhttp.dll", "BepInEx/core/BepInEx.dll"]
    },
    "632360": {   # Risk of Rain 2
        "path_type": "game",
        "rel_path": "BepInEx/plugins",
        "loader_id": "BepInEx",
        "loader_name": "BepInEx 5 (Unity Mod Loader)",
        "loader_check_files": ["winhttp.dll", "BepInEx/core/BepInEx.dll"]
    }
}

UE_PAK_EXTENSIONS = {".pak", ".utoc", ".ucas", ".sig"}
UE_MOVIE_EXTENSIONS = {".mp4", ".bk2", ".webm", ".mov", ".wmv", ".avi"}
UE_AUDIO_EXTENSIONS = {".bank"}
SUPPORTED_ARCHIVES = {".zip", ".rar", ".7z"}


# ==========================================
# PRE-INSTALL ARCHIVE CONTENT INSPECTOR
# ==========================================
class ArchiveModInspector:
    @classmethod
    def inspect_archive_contents(
        cls,
        archive_path: Path,
        staging_dir: Path,
        game: dict,
        default_mod_target_dir: Path,
        loader_id: str | None,
        loader_name: str | None
    ) -> dict:
        appid = str(game["appid"])
        game_root = Path(game["install_dir"])

        # A. BeamNG.drive (AppID 284160): Never extract .zip mods!
        if appid == "284160" or "beamng" in game["name"].lower():
            return {
                "is_loader_package": False,
                "requires_loader": False,
                "loader_id": None,
                "loader_name": None,
                "target_dir": default_mod_target_dir,
                "mod_type_label": "BeamNG Mod",
                "sub_mode": "beamng_repo_zip"
            }

        all_files = [p for p in staging_dir.rglob("*") if p.is_file()]
        file_names_lower = {p.name.lower() for p in all_files}
        rel_parts_lower = {
            part.lower()
            for p in all_files
            for part in p.relative_to(staging_dir).parts
        }
        exts_lower = {p.suffix.lower() for p in all_files}

        # B. Check if user dropped a MOD LOADER archive itself
        if "trreboottools.modmanager.exe" in file_names_lower or "rottrmodmanager.exe" in file_names_lower:
            return {
                "is_loader_package": True,
                "detected_loader_id": "RottrModManager",
                "requires_loader": False,
                "target_dir": game_root,
                "mod_type_label": "Tomb Raider Mod Manager Package",
                "reason": "Detected TrRebootTools / RottrModManager executable inside archive"
            }

        if "dwmapi.dll" in file_names_lower and ("ue4ss.dll" in file_names_lower or "ue4ss-settings.ini" in file_names_lower):
            ue_win64 = ModLoaderAutoInstaller._resolve_loader_destination(game_root, "ue_win64")
            return {
                "is_loader_package": True,
                "detected_loader_id": "UE4SS",
                "requires_loader": False,
                "target_dir": ue_win64,
                "mod_type_label": "UE4SS Mod Loader Package",
                "reason": "Detected UE4SS binaries inside archive"
            }

        if "winhttp.dll" in file_names_lower and "bepinex.dll" in file_names_lower:
            return {
                "is_loader_package": True,
                "detected_loader_id": "BepInEx",
                "requires_loader": False,
                "target_dir": game_root,
                "mod_type_label": "BepInEx Mod Loader Package",
                "reason": "Detected BepInEx core files inside archive"
            }

        # C. Rise of the Tomb Raider / Shadow of the Tomb Raider / TR2013
        if appid in {"391220", "750920", "203160"} or loader_id == "RottrModManager":
            return {
                "is_loader_package": False,
                "requires_loader": True,
                "loader_id": "RottrModManager",
                "loader_name": loader_name or "ROTTR Version-Independent Mod Tools",
                "target_dir": game_root,
                "mod_type_label": "Tomb Raider Mod",
                "sub_mode": "rottr_direct_loader"
            }

        # D. Unreal Engine 4/5 Games (Ready or Not, Palworld, Hogwarts Legacy, etc.)
        ue_paks_dir = SmartModRouter._find_unreal_paks_dir(game_root)
        if ue_paks_dir is not None or loader_id == "UE4SS":
            ue_content_dir = ue_paks_dir.parent if ue_paks_dir else default_mod_target_dir.parent
            ue_win64_dir = ModLoaderAutoInstaller._resolve_loader_destination(game_root, "ue_win64")
            paks_base = ue_paks_dir or default_mod_target_dir

            # 1. Movie / Intro / Menu Video Mods -> <Project>/Content/Movies
            has_movie_files = bool(exts_lower & UE_MOVIE_EXTENSIONS) or "movies" in rel_parts_lower
            if has_movie_files and not (exts_lower & UE_PAK_EXTENSIONS):
                movies_dir = ue_content_dir / "Movies"
                return {
                    "is_loader_package": False,
                    "requires_loader": False,
                    "loader_id": None,
                    "loader_name": None,
                    "target_dir": movies_dir,
                    "mod_type_label": "Video Mod",
                    "sub_mode": "ue_movies"
                }

            # 2. Audio / FMOD Bank Mods -> <Project>/Content/FMOD/Desktop
            has_audio_banks = bool(exts_lower & UE_AUDIO_EXTENSIONS) or "fmod" in rel_parts_lower
            if has_audio_banks and not (exts_lower & UE_PAK_EXTENSIONS):
                fmod_dir = ue_content_dir / "FMOD" / "Desktop"
                if not fmod_dir.exists() and (ue_content_dir / "FMOD").exists():
                    fmod_dir = ue_content_dir / "FMOD"
                return {
                    "is_loader_package": False,
                    "requires_loader": False,
                    "loader_id": None,
                    "loader_name": None,
                    "target_dir": fmod_dir,
                    "mod_type_label": "Audio Mod",
                    "sub_mode": "ue_fmod"
                }

            # 3. UE4SS Script / DLL Mods
            has_lua_script = ".lua" in exts_lower or ("scripts" in rel_parts_lower and "main.lua" in file_names_lower)
            has_ue4ss_folder = "ue4ss" in rel_parts_lower
            has_ue4ss_dll = ("dlls" in rel_parts_lower and "main.dll" in file_names_lower) or (
                ".dll" in exts_lower and not (exts_lower & UE_PAK_EXTENSIONS)
            )

            if has_lua_script or has_ue4ss_folder or has_ue4ss_dll:
                ue4ss_mods_dir = ue_win64_dir / "ue4ss" / "Mods"
                return {
                    "is_loader_package": False,
                    "requires_loader": True,
                    "loader_id": "UE4SS",
                    "loader_name": loader_name or "UE4SS (Unreal Engine Scripting System)",
                    "target_dir": ue4ss_mods_dir,
                    "mod_type_label": "UE4SS Script Mod",
                    "sub_mode": "ue4ss_mod"
                }

            # 4. UE4SS Blueprint LogicMods
            if "logicmods" in rel_parts_lower:
                logic_mods_dir = paks_base / "LogicMods"
                return {
                    "is_loader_package": False,
                    "requires_loader": True,
                    "loader_id": "UE4SS",
                    "loader_name": loader_name or "UE4SS (Blueprint LogicMods Loader)",
                    "target_dir": logic_mods_dir,
                    "mod_type_label": "LogicMod",
                    "sub_mode": "ue_logicmod"
                }

            # 5. Standard Native .pak / .utoc / .ucas Mod
            if exts_lower & UE_PAK_EXTENSIONS:
                return {
                    "is_loader_package": False,
                    "requires_loader": False,
                    "loader_id": None,
                    "loader_name": None,
                    "target_dir": default_mod_target_dir,
                    "mod_type_label": "Pak Mod",
                    "sub_mode": "ue_pak"
                }

        # E. Unity Games (BepInEx / MelonLoader)
        if loader_id in {"BepInEx", "MelonLoader"}:
            if "patchers" in rel_parts_lower and "bepinex" not in rel_parts_lower:
                target = game_root / "BepInEx" / "patchers"
            elif loader_id == "MelonLoader":
                target = game_root / "Mods"
            else:
                target = game_root / "BepInEx" / "plugins"

            return {
                "is_loader_package": False,
                "requires_loader": True,
                "loader_id": loader_id,
                "loader_name": loader_name or f"{loader_id} (Unity Mod Loader)",
                "target_dir": target,
                "mod_type_label": f"{loader_id} Mod",
                "sub_mode": "unity_mod"
            }

        # F. Bethesda Creation Engine
        if (game_root / "Data").exists():
            for se_folder, se_label in (("skse", "SKSE64"), ("f4se", "F4SE"), ("sfse", "SFSE"), ("nvse", "xNVSE")):
                if se_folder in rel_parts_lower and ".dll" in exts_lower:
                    return {
                        "is_loader_package": False,
                        "requires_loader": True,
                        "loader_id": se_label,
                        "loader_name": f"{se_label} (Script Extender)",
                        "target_dir": game_root / "Data",
                        "mod_type_label": f"{se_label} Mod",
                        "sub_mode": "standard"
                    }

        requires_loader = bool(loader_id or loader_name)
        return {
            "is_loader_package": False,
            "requires_loader": requires_loader,
            "loader_id": loader_id,
            "loader_name": loader_name,
            "target_dir": default_mod_target_dir,
            "mod_type_label": "Mod",
            "sub_mode": "standard"
        }


# ==========================================
# AUTOMATIC MOD LOADER INSTALLER & ROTTR PATH FIXER
# ==========================================
class ModLoaderAutoInstaller:
    @staticmethod
    def _load_loader_manifest() -> dict:
        if LOADER_MANIFEST_FILE.exists():
            try:
                return json.loads(LOADER_MANIFEST_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def _save_loader_manifest(data: dict):
        try:
            LOADER_MANIFEST_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def has_recorded_loader(cls, appid: str) -> bool:
        manifest = cls._load_loader_manifest()
        return str(appid) in manifest and bool(manifest[str(appid)].get("files"))

    @classmethod
    def is_loader_installed_for_game(cls, game: dict) -> bool:
        appid = str(game["appid"])
        if cls.has_recorded_loader(appid):
            return True
        game_root = Path(game["install_dir"])
        if not game_root.exists():
            return False

        if appid in KNOWN_GAME_PROFILES:
            for rel in KNOWN_GAME_PROFILES[appid].get("loader_check_files", []):
                if (game_root / Path(rel)).exists():
                    return True

        if appid in {"391220", "750920", "203160"} and cls.get_rottr_manager_exe(game_root):
            return True

        common_checks = [
            game_root / "BepInEx" / "core" / "BepInEx.dll",
            game_root / "MelonLoader",
            game_root / "StardewModdingAPI.exe",
            game_root / "modengine2_launcher.exe",
            game_root / "RottrModManager.exe",
            game_root / "TrRebootTools.ModManager.exe"
        ]
        return any(p.exists() for p in common_checks)

    @classmethod
    def configure_rottr_game_path(cls, game_root: Path, appid: str = "391220"):
        """
        Fixes the 'Could not automatically determine the Rise of the Tomb Raider installation folder' error
        by automatically pre-populating:
          1. All Registry keys referenced inside RottrModManager.exe / TrRebootTools.ModManager.exe
          2. Steam's Uninstall Registry key (Steam App 391220 -> InstallLocation)
          3. A zero-admin Windows Directory Junction at <DefaultSteamRoot>\\steamapps\\common\\Rise of the Tomb Raider
             if the game is installed on a secondary drive (e.g. E:\\SteamLibrary).
        """
        if sys.platform != "win32":
            return

        game_path_str = str(game_root.resolve())

        try:
            import winreg

            # 1. Pre-populate Steam Uninstall Registry keys (checked by RottrModManager to locate the game)
            uninstall_subkeys = [
                rf"Software\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {appid}",
                rf"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\Steam App {appid}",
            ]
            for root_hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
                for subk in uninstall_subkeys:
                    try:
                        with winreg.CreateKeyEx(root_hive, subk, 0, winreg.KEY_SET_VALUE) as key:
                            winreg.SetValueEx(key, "InstallLocation", 0, winreg.REG_SZ, game_path_str)
                    except OSError:
                        continue

            # 2. Pre-populate RottrModManager / TrRebootTools / Square Enix registry keys
            candidate_reg_keys = [
                r"Software\RottrModManager",
                r"Software\SottrModManager",
                r"Software\TrRebootTools",
                r"Software\ArcusMaximus\RottrModManager",
                r"Software\Crystal Dynamics\Rise of the Tomb Raider",
                r"Software\Square Enix\Rise of the Tomb Raider",
            ]

            # Also dynamically extract any Software\... registry paths embedded inside RottrModManager.exe
            rottr_exe = cls.get_rottr_manager_exe(game_root)
            if rottr_exe and rottr_exe.exists():
                try:
                    raw_bytes = rottr_exe.read_bytes()
                    utf16_strings = [
                        m.decode("utf-16le", errors="ignore")
                        for m in re.findall(rb"(?:[A-Za-z0-9_\\.\- ]\x00){4,}", raw_bytes)
                    ]
                    for s in utf16_strings:
                        if s.lower().startswith("software\\") and len(s) < 120:
                            candidate_reg_keys.append(s)
                except Exception:
                    pass

            value_names = [
                "", "GameFolderPath", "GameFolder", "InstallLocation", "InstallPath",
                "GamePath", "FolderPath", "Path", "RottrFolderPath", "RiseOfTheTombRaiderPath"
            ]
            for reg_subkey in dict.fromkeys(candidate_reg_keys):
                try:
                    with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, reg_subkey, 0, winreg.KEY_SET_VALUE) as k:
                        for v_name in value_names:
                            winreg.SetValueEx(k, v_name, 0, winreg.REG_SZ, game_path_str)
                except OSError:
                    continue
        except Exception:
            pass

        # 3. Create a Directory Junction at <SteamRoot>\steamapps\common\<GameFolderName> if on another drive
        try:
            steam_root = SteamScanner.get_steam_root()
            if steam_root and steam_root.exists():
                default_common = steam_root / "steamapps" / "common"
                if default_common.exists():
                    expected_default_dir = default_common / game_root.name
                    if not expected_default_dir.exists() and expected_default_dir.resolve() != game_root.resolve():
                        subprocess.run(
                            ["cmd", "/c", "mklink", "/J", str(expected_default_dir), game_path_str],
                            capture_output=True,
                            creationflags=0x08000000
                        )
        except Exception:
            pass

    @staticmethod
    def check_dotnet_desktop_runtime() -> bool:
        dotnet_dir = Path(r"C:\Program Files\dotnet\shared\Microsoft.WindowsDesktop.App")
        if dotnet_dir.exists() and any(dotnet_dir.iterdir()):
            return True
        try:
            res = subprocess.run(
                ["dotnet", "--list-runtimes"],
                capture_output=True,
                text=True,
                creationflags=0x08000000,
                timeout=3
            )
            if res.returncode == 0 and "Microsoft.WindowsDesktop.App" in res.stdout:
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def install_dotnet_desktop_runtime(progress_callback) -> bool:
        try:
            progress_callback("⏳ Installing Microsoft .NET 8 Desktop Runtime via winget...")
            cmd = [
                "winget", "install",
                "--id", "Microsoft.DotNet.DesktopRuntime.8",
                "--silent",
                "--accept-package-agreements",
                "--accept-source-agreements"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def get_rottr_manager_exe(cls, game_root: Path) -> Path | None:
        for exe_name in ("TrRebootTools.ModManager.exe", "RottrModManager.exe", "SottrModManager.exe"):
            direct = game_root / exe_name
            if direct.exists():
                return direct
            for match in game_root.glob(f"*/{exe_name}"):
                if match.is_file():
                    return match
        return None

    @classmethod
    def resolve_catalog_entry(cls, loader_id: str | None, loader_name: str | None) -> tuple[str | None, dict | None]:
        if loader_id and loader_id in LOADER_CATALOG:
            return loader_id, LOADER_CATALOG[loader_id]

        if loader_name:
            lname_lower = loader_name.lower()
            if "rottr" in lname_lower or "trreboot" in lname_lower or "tiger" in lname_lower:
                return "RottrModManager", LOADER_CATALOG["RottrModManager"]
            if "bepinex" in lname_lower:
                return "BepInEx", LOADER_CATALOG["BepInEx"]
            if "melonloader" in lname_lower:
                return "MelonLoader", LOADER_CATALOG["MelonLoader"]
            if "ue4ss" in lname_lower:
                return "UE4SS", LOADER_CATALOG["UE4SS"]
            if "reframework" in lname_lower:
                return "REFramework", LOADER_CATALOG["REFramework"]
            if "mod engine 2" in lname_lower:
                return "ModEngine2", LOADER_CATALOG["ModEngine2"]
            if "smapi" in lname_lower:
                return "SMAPI", LOADER_CATALOG["SMAPI"]
            if "lovely" in lname_lower:
                return "Lovely", LOADER_CATALOG["Lovely"]
            if "reloaded" in lname_lower:
                return "ReloadedII", LOADER_CATALOG["ReloadedII"]
        return loader_id, None

    @classmethod
    def install_loader_from_local_staging(
        cls,
        game: dict,
        staging_dir: Path,
        detected_loader_id: str
    ) -> tuple[bool, str]:
        appid = str(game["appid"])
        game_root = Path(game["install_dir"])
        _, catalog_entry = cls.resolve_catalog_entry(detected_loader_id, None)
        target_type = catalog_entry.get("target_type", "game_root") if catalog_entry else "game_root"

        effective_root = staging_dir
        top_items = list(effective_root.iterdir())
        if (
            len(top_items) == 1
            and top_items[0].is_dir()
            and top_items[0].name.lower() not in {"bepinex", "melonloader", "ue4ss", "mods", "bin"}
        ):
            effective_root = top_items[0]

        install_dest = cls._resolve_loader_destination(game_root, target_type)
        install_dest.mkdir(parents=True, exist_ok=True)

        recorded_files = []
        for item in effective_root.rglob("*"):
            if item.is_file():
                rel = item.relative_to(effective_root)
                dest_file = install_dest / rel
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(item, dest_file)
                try:
                    recorded_files.append(str(dest_file.relative_to(game_root)))
                except ValueError:
                    recorded_files.append(str(dest_file))

        if detected_loader_id == "RottrModManager":
            cls.configure_rottr_game_path(game_root, appid)

        manifest = cls._load_loader_manifest()
        manifest[appid] = {
            "loader_id": detected_loader_id,
            "loader_name": catalog_entry["friendly_name"] if catalog_entry else detected_loader_id,
            "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "files": recorded_files
        }
        cls._save_loader_manifest(manifest)
        return True, f"✅ Installed Mod Loader ({detected_loader_id}) into {install_dest} ({len(recorded_files)} files)!"

    @classmethod
    def auto_install_loader(
        cls,
        game: dict,
        loader_id: str | None,
        loader_name: str | None,
        progress_callback
    ) -> tuple[bool, str]:
        appid = str(game["appid"])
        game_root = Path(game["install_dir"])
        if not game_root.exists():
            return False, "Game installation directory not found."

        resolved_id, catalog_entry = cls.resolve_catalog_entry(loader_id, loader_name)

        if catalog_entry and catalog_entry.get("requires_dotnet_desktop"):
            if not cls.check_dotnet_desktop_runtime():
                cls.install_dotnet_desktop_runtime(progress_callback)

        headers = {
            "Accept": "application/vnd.github+json",
            "User-Agent": f"NebulaModManager/{APP_VERSION}"
        }

        repo_slug = catalog_entry["github_repo"] if catalog_entry else None
        asset_regex = catalog_entry["asset_regex"] if catalog_entry else r"\.(zip|7z|rar)$"
        target_type = catalog_entry["target_type"] if catalog_entry else "game_root"

        if not repo_slug and loader_name:
            progress_callback(f"🔍 Searching GitHub for '{loader_name}'...")
            clean_query = loader_name.split("(")[0].strip()
            try:
                search_url = f"https://api.github.com/search/repositories?q={quote_plus(clean_query)}&per_page=3"
                s_resp = requests.get(search_url, headers=headers, timeout=6).json()
                items = s_resp.get("items", [])
                if items:
                    repo_slug = items[0].get("full_name")
            except Exception:
                pass

        if not repo_slug:
            return False, f"No direct GitHub auto-installer found for '{loader_name}'."

        progress_callback(f"⏳ Fetching latest release from GitHub ({repo_slug})...")
        try:
            rel_url = f"https://api.github.com/repos/{repo_slug}/releases"
            releases = requests.get(rel_url, headers=headers, timeout=8).json()
            if not isinstance(releases, list) or not releases:
                return False, f"No public releases found on GitHub for {repo_slug}."
        except Exception as e:
            return False, f"Failed to contact GitHub API: {str(e)}"

        download_url = None
        asset_name = None

        for release in releases:
            assets = release.get("assets", [])
            for asset in assets:
                name = asset.get("name", "")
                if re.search(asset_regex, name, flags=re.IGNORECASE):
                    download_url = asset.get("browser_download_url")
                    asset_name = name
                    break
            if download_url:
                break

        if not download_url and releases:
            for asset in releases[0].get("assets", []):
                name = asset.get("name", "")
                if name.lower().endswith((".zip", ".7z", ".rar")):
                    download_url = asset.get("browser_download_url")
                    asset_name = name
                    break

        if not download_url or not asset_name:
            return False, f"Could not find a downloadable archive in {repo_slug}."

        temp_dir = APP_DATA_DIR / "loader_temp"
        if temp_dir.exists():
            shutil.rmtree(temp_dir, ignore_errors=True)
        temp_dir.mkdir(parents=True, exist_ok=True)

        archive_file = temp_dir / asset_name
        extract_dir = temp_dir / "extracted"
        extract_dir.mkdir(parents=True, exist_ok=True)

        try:
            with requests.get(download_url, stream=True, headers=headers, timeout=30) as r:
                r.raise_for_status()
                total_bytes = int(r.headers.get("content-length", 0))
                downloaded = 0
                with open(archive_file, "wb") as f:
                    for chunk in r.iter_content(chunk_size=65536):
                        if chunk:
                            f.write(chunk)
                            downloaded += len(chunk)
                            if total_bytes > 0:
                                pct = int((downloaded / total_bytes) * 100)
                                mb_done = downloaded / (1024 * 1024)
                                mb_total = total_bytes / (1024 * 1024)
                                progress_callback(
                                    f"⬇️ Downloading {asset_name}: {mb_done:.1f} / {mb_total:.1f} MB ({pct}%)"
                                )
                            else:
                                mb_done = downloaded / (1024 * 1024)
                                progress_callback(f"⬇️ Downloading {asset_name}: {mb_done:.1f} MB...")

            progress_callback(f"📦 Extracting {asset_name}...")
            ext = archive_file.suffix.lower()
            if ext == ".zip":
                with zipfile.ZipFile(archive_file, "r") as zf:
                    zf.extractall(extract_dir)
            elif ext == ".7z":
                ModController._extract_7z(archive_file, extract_dir)
            elif ext == ".rar":
                ModController._extract_rar(archive_file, extract_dir)

            effective_root = extract_dir
            top_items = list(effective_root.iterdir())
            if (
                len(top_items) == 1
                and top_items[0].is_dir()
                and top_items[0].name.lower() not in {"bepinex", "melonloader", "ue4ss", "mods", "bin"}
            ):
                effective_root = top_items[0]

            install_dest = cls._resolve_loader_destination(game_root, target_type)
            install_dest.mkdir(parents=True, exist_ok=True)

            recorded_files = []
            for item in effective_root.rglob("*"):
                if item.is_file():
                    rel = item.relative_to(effective_root)
                    dest_file = install_dest / rel
                    dest_file.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest_file)
                    try:
                        recorded_files.append(str(dest_file.relative_to(game_root)))
                    except ValueError:
                        recorded_files.append(str(dest_file))

            if resolved_id == "BepInEx":
                (game_root / "BepInEx" / "plugins").mkdir(parents=True, exist_ok=True)
            elif resolved_id == "MelonLoader":
                (game_root / "Mods").mkdir(parents=True, exist_ok=True)
            elif resolved_id == "UE4SS":
                (install_dest / "ue4ss" / "Mods").mkdir(parents=True, exist_ok=True)
            elif resolved_id == "RottrModManager":
                cls.configure_rottr_game_path(game_root, appid)

            manifest = cls._load_loader_manifest()
            manifest[appid] = {
                "loader_id": resolved_id,
                "loader_name": loader_name,
                "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "files": recorded_files
            }
            cls._save_loader_manifest(manifest)

            return True, f"✅ Auto-installed {asset_name} ({len(recorded_files)} files) into {install_dest.name}!"

        except Exception as e:
            return False, f"Auto-install error: {str(e)}"
        finally:
            shutil.rmtree(temp_dir, ignore_errors=True)

    @classmethod
    def uninstall_loader(
        cls,
        game: dict,
        loader_id: str | None,
        loader_name: str | None
    ) -> tuple[bool, str]:
        appid = str(game["appid"])
        game_root = Path(game["install_dir"])
        if not game_root.exists():
            return False, "Game installation directory not found."

        resolved_id, catalog_entry = cls.resolve_catalog_entry(loader_id, loader_name)
        manifest = cls._load_loader_manifest()
        removed_count = 0

        if appid in manifest:
            for stored_path in manifest[appid].get("files", []):
                p = Path(stored_path)
                full_p = p if p.is_absolute() else (game_root / p)
                try:
                    if full_p.exists() and full_p.is_file():
                        full_p.unlink()
                        removed_count += 1
                except Exception:
                    continue
            del manifest[appid]
            cls._save_loader_manifest(manifest)

        if catalog_entry:
            target_dir = cls._resolve_loader_destination(game_root, catalog_entry.get("target_type", "game_root"))
            for rel_file in catalog_entry.get("known_files", []):
                for base in (target_dir, game_root):
                    candidate = base / Path(rel_file.strip())
                    try:
                        if candidate.exists() and candidate.is_file():
                            candidate.unlink()
                            removed_count += 1
                    except Exception:
                        pass

            for rel_dir in catalog_entry.get("known_dirs", []):
                for base in (target_dir, game_root):
                    candidate_dir = base / Path(rel_dir)
                    try:
                        if candidate_dir.exists() and candidate_dir.is_dir():
                            shutil.rmtree(candidate_dir, ignore_errors=True)
                            removed_count += 1
                    except Exception:
                        pass

        if appid in KNOWN_GAME_PROFILES:
            for check_f in KNOWN_GAME_PROFILES[appid].get("loader_check_files", []):
                candidate = game_root / Path(check_f)
                try:
                    if candidate.exists() and candidate.is_file():
                        candidate.unlink()
                        removed_count += 1
                except Exception:
                    pass

        for folder_candidate in ("BepInEx", "MelonLoader", "smapi-internal", "reframework", "modengine2"):
            d_path = game_root / folder_candidate
            try:
                if d_path.exists() and d_path.is_dir() and not any(d_path.rglob("*")):
                    shutil.rmtree(d_path, ignore_errors=True)
            except Exception:
                pass

        if removed_count == 0:
            return False, "No mod loader files were found to delete."

        display_name = loader_name.split("(")[0].strip() if loader_name else "Mod Loader"
        return True, f"🗑️ Deleted {display_name} ({removed_count} loader files/folders removed)."

    @staticmethod
    def _resolve_loader_destination(game_root: Path, target_type: str) -> Path:
        if target_type == "ue_win64":
            for sub in game_root.iterdir():
                if sub.is_dir() and sub.name.lower() not in {"engine", "redists", "directx"}:
                    win64_dir = sub / "Binaries" / "Win64"
                    if win64_dir.exists() and win64_dir.is_dir():
                        return win64_dir
            return game_root
        elif target_type == "sub_bin":
            bin_dir = game_root / "bin"
            bin_dir.mkdir(parents=True, exist_ok=True)
            return bin_dir
        return game_root


# ==========================================
# ONLINE MOD PATH & MOD LOADER RESOLVER
# ==========================================
class SmartModRouter:
    _thunderstore_cache = None

    @staticmethod
    def load_custom_paths() -> dict:
        if CUSTOM_PATHS_FILE.exists():
            try:
                return json.loads(CUSTOM_PATHS_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def save_custom_path(appid: str, full_path: str):
        data = SmartModRouter.load_custom_paths()
        data[appid] = full_path
        CUSTOM_PATHS_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @staticmethod
    def _load_online_cache() -> dict:
        if ONLINE_CACHE_FILE.exists():
            try:
                return json.loads(ONLINE_CACHE_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    @staticmethod
    def _save_online_cache(cache_data: dict):
        try:
            ONLINE_CACHE_FILE.write_text(json.dumps(cache_data, indent=2), encoding="utf-8")
        except Exception:
            pass

    @classmethod
    def resolve_beamng_mods_path(cls, game_root: Path | None = None) -> tuple[Path, str]:
        if sys.platform == "win32":
            try:
                import winreg
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\BeamNG\BeamNG.drive") as key:
                    user_path_str, _ = winreg.QueryValueEx(key, "UserPath")
                    if user_path_str:
                        base = Path(user_path_str.strip().strip('"'))
                        if base.exists():
                            repo_dir = base / "current" / "mods" / "repo"
                            repo_dir.mkdir(parents=True, exist_ok=True)
                            return repo_dir, "🌐 BeamNG Repo Path (Registry UserPath)"
            except OSError:
                pass

        if game_root and (game_root / "startup.ini").exists():
            try:
                ini_text = (game_root / "startup.ini").read_text(encoding="utf-8", errors="ignore")
                m = re.search(r"UserPath\s*=\s*(.+)", ini_text, flags=re.IGNORECASE)
                if m:
                    custom_user_path = Path(m.group(1).strip().strip('"'))
                    if custom_user_path.exists():
                        repo_dir = custom_user_path / "current" / "mods" / "repo"
                        repo_dir.mkdir(parents=True, exist_ok=True)
                        return repo_dir, "🌐 BeamNG Repo Path (startup.ini)"
            except Exception:
                pass

        local_app_data = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        beamng_base = local_app_data / "BeamNG.drive"
        repo_target = beamng_base / "current" / "mods" / "repo"
        repo_target.mkdir(parents=True, exist_ok=True)
        return repo_target, "🌐 BeamNG Official Repo Path (/current/mods/repo)"

    @classmethod
    def resolve_full_game_metadata_online(cls, game: dict) -> dict:
        appid = str(game["appid"])
        game_name = game["name"]
        game_root = Path(game["install_dir"])

        # Automatically pre-configure ROTTR / Tomb Raider registry & junction so the loader never errors!
        if appid in {"391220", "750920", "203160"} or any(game_root.glob("*.tiger")):
            ModLoaderAutoInstaller.configure_rottr_game_path(game_root, appid)

        local_appdata = Path(os.getenv("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
        roaming_appdata = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
        documents_dir = Path.home() / "Documents"

        custom_paths = cls.load_custom_paths()
        custom_override_path = None
        if appid in custom_paths:
            custom_override_path = Path(custom_paths[appid])
            custom_override_path.mkdir(parents=True, exist_ok=True)

        if appid in KNOWN_GAME_PROFILES:
            prof = KNOWN_GAME_PROFILES[appid]
            ptype = prof["path_type"]
            rel = prof["rel_path"]
            reason = "🌐 Online Verified Profile"

            if ptype == "beamng_repo":
                resolved_path, reason = cls.resolve_beamng_mods_path(game_root)
            elif ptype == "localappdata":
                resolved_path = local_appdata / Path(rel)
            elif ptype == "appdata":
                resolved_path = roaming_appdata / Path(rel)
            elif ptype == "documents":
                resolved_path = documents_dir / Path(rel)
            else:
                resolved_path = (game_root / Path(rel)) if rel else game_root

            resolved_path.mkdir(parents=True, exist_ok=True)
            loader_notice, loader_query, is_installed = cls._build_loader_status(
                appid, game_name, game_root, prof.get("loader_name"), prof.get("loader_check_files", [])
            )
            return {
                "mod_path": custom_override_path or resolved_path,
                "reason": "Custom User Path" if custom_override_path else reason,
                "loader_id": prof.get("loader_id"),
                "loader_name": prof.get("loader_name"),
                "loader_installed": is_installed,
                "loader_notice": loader_notice,
                "loader_search_query": loader_query
            }

        online_info = cls._search_online_and_engine_signatures(appid, game_name, game_root)
        resolved_path, reason = cls._locate_best_path_on_computer(
            game_name=game_name,
            game_root=game_root,
            online_info=online_info,
            local_appdata=local_appdata,
            roaming_appdata=roaming_appdata,
            documents_dir=documents_dir
        )

        loader_id = online_info.get("loader_id")
        if loader_id == "BepInEx" and resolved_path == game_root:
            resolved_path = game_root / "BepInEx" / "plugins"
            resolved_path.mkdir(parents=True, exist_ok=True)
            reason = "🌐 Online Search (BepInEx Plugins Path)"
        elif loader_id == "MelonLoader" and resolved_path == game_root:
            resolved_path = game_root / "Mods"
            resolved_path.mkdir(parents=True, exist_ok=True)
            reason = "🌐 Online Search (MelonLoader Mods Path)"

        loader_notice, loader_query, is_installed = cls._evaluate_mod_loader_notice(
            appid, game_name, game_root, online_info
        )

        return {
            "mod_path": custom_override_path or resolved_path,
            "reason": "Custom User Path" if custom_override_path else reason,
            "loader_id": loader_id,
            "loader_name": online_info.get("loader_name"),
            "loader_installed": is_installed,
            "loader_notice": loader_notice,
            "loader_search_query": loader_query
        }

    @classmethod
    def _search_online_and_engine_signatures(cls, appid: str, game_name: str, game_root: Path) -> dict:
        cache = cls._load_online_cache()
        if appid in cache:
            return cache[appid]

        info = {
            "engine": "",
            "pcgw_paths": [],
            "loader_id": None,
            "loader_name": None,
            "check_files": []
        }

        try:
            if any(game_root.glob("bigfile.*.tiger")) or any(game_root.glob("*.tiger")):
                info["engine"] = "foundation_tiger"
                info["loader_id"] = "RottrModManager"
                info["loader_name"] = "ROTTR Mod Manager (Auto-Configured for Direct .tiger Mod Injection)"
                info["check_files"] = [
                    "TrRebootTools.ModManager.exe", "RottrModManager.exe",
                    "SottrModManager.exe", "ROTTRTigetAdd.exe", "InstallMod.bat"
                ]

            elif (game_root / "UnityPlayer.dll").exists() or any(game_root.glob("*_Data/Managed/UnityEngine.dll")):
                info["engine"] = "unity"
                if (game_root / "MelonLoader").exists():
                    info["loader_id"] = "MelonLoader"
                    info["loader_name"] = "MelonLoader (Unity Mod Loader)"
                    info["check_files"] = ["version.dll", "MelonLoader/Dependencies/Bootstrap.dll"]
                else:
                    info["loader_id"] = "BepInEx"
                    info["loader_name"] = "BepInEx 5 (Unity Mod Loader)"
                    info["check_files"] = ["winhttp.dll", "BepInEx/core/BepInEx.dll", "version.dll"]

            elif any(game_root.glob("re_chunk_000.pak")):
                info["engine"] = "re_engine"
                info["loader_id"] = "REFramework"
                info["loader_name"] = "REFramework (dinput8.dll)"
                info["check_files"] = ["dinput8.dll"]

            elif any(game_root.glob("Data0.bdt")) or (game_root / "regulation.bin").exists() or (game_root / "Game" / "regulation.bin").exists():
                info["engine"] = "fromsoftware"
                info["loader_id"] = "ModEngine2"
                info["loader_name"] = "Mod Engine 2 (FromSoftware Loader)"
                info["check_files"] = ["dinput8.dll", "Game/dinput8.dll", "modengine2_launcher.exe"]

            elif cls._find_unreal_paks_dir(game_root) is not None:
                info["engine"] = "unreal"
                paks_dir = cls._find_unreal_paks_dir(game_root)
                if paks_dir:
                    info["loader_id"] = "UE4SS"
                    info["loader_name"] = "UE4SS (For Script/Blueprint mods; standard .pak & Movies work natively)"
                    for sub in game_root.iterdir():
                        if sub.is_dir() and (sub / "Binaries" / "Win64").exists():
                            rel_w64 = (sub / "Binaries" / "Win64").relative_to(game_root)
                            info["check_files"].append(str(rel_w64 / "dwmapi.dll"))
                            info["check_files"].append(str(rel_w64 / "ue4ss" / "ue4ss.dll"))
        except Exception:
            pass

        try:
            url = (
                "https://www.pcgamingwiki.com/w/api.php?action=cargoquery"
                "&tables=Infobox_game&fields=Infobox_game._pageName=Page,Infobox_game.Engines=Engines"
                f"&where=Infobox_game.Steam_AppID%20HOLDS%20%22{appid}%22&format=json"
            )
            resp = requests.get(url, timeout=4).json()
            rows = resp.get("cargoquery", [])
            if rows:
                title_data = rows[0].get("title", {})
                if not info["engine"]:
                    info["engine"] = str(title_data.get("Engines", "")).lower()
                page_name = title_data.get("Page", "")

                if page_name:
                    parse_url = (
                        "https://www.pcgamingwiki.com/w/api.php?action=parse"
                        f"&page={requests.utils.quote(page_name)}&prop=wikitext&format=json"
                    )
                    p_resp = requests.get(parse_url, timeout=4).json()
                    wikitext = p_resp.get("parse", {}).get("wikitext", {}).get("*", "")
                    if wikitext:
                        raw_paths = re.findall(
                            r"\{\{p\|(localappdata|appdata|userprofile\\documents|documents|game)\}\}[\\/]([^\n|<>{}\[\]]+)",
                            wikitext,
                            flags=re.IGNORECASE
                        )
                        for base_token, sub_raw in raw_paths:
                            cleaned_sub = sub_raw.strip().rstrip("\\/").replace("\\\\", "\\")
                            if cleaned_sub and len(cleaned_sub) < 120:
                                info["pcgw_paths"].append((base_token.lower(), cleaned_sub))
        except Exception:
            pass

        if not info["loader_id"]:
            ts_map = ModSiteVerifier._ensure_thunderstore_map()
            norm_game = ModSiteVerifier._norm(game_name)
            if norm_game in ts_map:
                info["loader_id"] = "BepInEx"
                info["loader_name"] = "BepInEx 5 (Unity Mod Loader)"
                info["check_files"] = ["winhttp.dll", "BepInEx/core/BepInEx.dll"]

        cache[appid] = info
        cls._save_online_cache(cache)
        return info

    @classmethod
    def _locate_best_path_on_computer(
        cls,
        game_name: str,
        game_root: Path,
        online_info: dict,
        local_appdata: Path,
        roaming_appdata: Path,
        documents_dir: Path
    ) -> tuple[Path, str]:
        token_map = {
            "localappdata": local_appdata,
            "appdata": roaming_appdata,
            "documents": documents_dir,
            "userprofile\\documents": documents_dir,
            "game": game_root
        }

        for token, rel_str in online_info.get("pcgw_paths", []):
            base_dir = token_map.get(token)
            if not base_dir:
                continue
            cleaned_rel = re.sub(r"<[^>]+>", "", rel_str).strip("\\/")
            candidate_base = base_dir / Path(cleaned_rel)
            if candidate_base.exists() and candidate_base.is_dir():
                for mod_folder_name in ("current/mods/repo", "mods/repo", "mods", "Mods", "mod", "addons", "Paks"):
                    mod_sub = candidate_base / mod_folder_name
                    if mod_sub.exists() and mod_sub.is_dir():
                        return mod_sub, f"🌐 Online PCGamingWiki Path ({mod_folder_name})"

        clean_title = re.sub(r"[:™®']", "", game_name).strip()
        for s_root in (local_appdata, roaming_appdata, documents_dir / "My Games", documents_dir):
            if not s_root.exists():
                continue
            direct_match = s_root / clean_title
            if direct_match.exists() and direct_match.is_dir():
                for mod_sub_name in ("current/mods/repo", "mods/repo", "mods", "Mods", "mod"):
                    if (direct_match / mod_sub_name).exists():
                        return direct_match / mod_sub_name, "🌐 Auto-Discovered in User AppData/Documents"

        ue_paks = cls._find_unreal_paks_dir(game_root)
        if ue_paks:
            return ue_paks, "🌐 Online & Engine Verified (Unreal Content/Paks)"

        if (game_root / "BepInEx" / "plugins").exists():
            return game_root / "BepInEx" / "plugins", "🌐 Auto-Detected (BepInEx Plugins)"
        if (game_root / "Mods").exists() and (game_root / "MelonLoader").exists():
            return game_root / "Mods", "🌐 Auto-Detected (MelonLoader Mods)"

        if (game_root / "archive" / "pc").exists():
            target = game_root / "archive" / "pc" / "mod"
            target.mkdir(parents=True, exist_ok=True)
            return target, "🌐 Auto-Detected (REDengine Mod Folder)"

        if (game_root / "Data").exists():
            data_dir = game_root / "Data"
            if any(data_dir.glob("*.esm")) or any(data_dir.glob("*.ba2")) or any(data_dir.glob("*.bsa")):
                return data_dir, "🌐 Auto-Detected (Creation Engine Data)"

        if online_info.get("engine") == "foundation_tiger":
            return game_root, "🌐 Direct Mod Loader Injection (RottrModManager)"

        for candidate in ("Mods", "mods", "addons", "mod", "nativePC"):
            if (game_root / candidate).exists() and (game_root / candidate).is_dir():
                return game_root / candidate, f"🌐 Auto-Detected ({candidate} folder)"

        return game_root, "Game Root Directory"

    @classmethod
    def _evaluate_mod_loader_notice(
        cls, appid: str, game_name: str, game_root: Path, online_info: dict
    ) -> tuple[str | None, str | None, bool]:
        loader_name = online_info.get("loader_name")
        check_files = online_info.get("check_files", [])

        if not loader_name:
            return None, None, False

        return cls._build_loader_status(appid, game_name, game_root, loader_name, check_files)

    @staticmethod
    def _build_loader_status(
        appid: str,
        game_name: str,
        game_root: Path,
        loader_name: str | None,
        check_files: list[str]
    ) -> tuple[str | None, str | None, bool]:
        if not loader_name:
            return None, None, False

        search_query = f"{game_name} {loader_name.split('(')[0].strip()} Nexus Mods"
        installed_on_disk = any((game_root / Path(rel)).exists() for rel in check_files)
        if str(appid) in {"391220", "750920", "203160"} and ModLoaderAutoInstaller.get_rottr_manager_exe(game_root):
            installed_on_disk = True

        installed_in_manifest = ModLoaderAutoInstaller.has_recorded_loader(appid)
        installed = installed_on_disk or installed_in_manifest

        if str(appid) in {"391220", "750920", "203160"}:
            has_dotnet = ModLoaderAutoInstaller.check_dotnet_desktop_runtime()
            dotnet_tag = "✅ Path & Runtime Ready" if has_dotnet else "⚠️ Missing .NET Runtime"
            status_str = f"✅ Loader Installed ({dotnet_tag})" if installed else f"❌ Loader Not Installed ({dotnet_tag})"
            return f"ℹ️ Mod Loader: {loader_name}  •  [{status_str}]", search_query, installed

        status_str = "✅ Detected in Game Folder" if installed else "❌ Not Installed — Click Auto-Install!"
        return f"ℹ️ Mod Loader: {loader_name}   •   [{status_str}]", search_query, installed

    @staticmethod
    def _find_unreal_paks_dir(game_root: Path) -> Path | None:
        try:
            for sub in game_root.iterdir():
                if sub.is_dir() and sub.name.lower() not in {"engine", "redists", "directx"}:
                    paks_candidate = sub / "Content" / "Paks"
                    if paks_candidate.exists() and paks_candidate.is_dir():
                        return paks_candidate
        except Exception:
            pass
        return None

    @staticmethod
    def _backup_vanilla_file_if_needed(appid: str, game_root: Path, dest_file: Path):
        if not dest_file.exists() or not dest_file.is_file():
            return
        try:
            rel_to_game = dest_file.relative_to(game_root)
            backup_path = VANILLA_BACKUP_DIR / str(appid) / rel_to_game
            if not backup_path.exists():
                backup_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(dest_file, backup_path)
        except Exception:
            pass

    @classmethod
    def smart_place_extracted_files(
        cls,
        archive_path: Path,
        staging_dir: Path,
        game_root: Path,
        mod_target_dir: Path,
        appid: str,
        sub_mode: str = "standard"
    ) -> list[str]:
        installed_paths = []

        # 1. BeamNG.drive (NEVER extract .zip mods -> copy straight into .../current/mods/repo)
        if str(appid) == "284160" or sub_mode == "beamng_repo_zip":
            mod_target_dir.mkdir(parents=True, exist_ok=True)
            ext = archive_path.suffix.lower()

            if ext == ".zip":
                dest = mod_target_dir / archive_path.name
                shutil.copy2(archive_path, dest)
                return [str(dest)]

            inner_zips = list(staging_dir.rglob("*.zip"))
            if inner_zips:
                for zf_path in inner_zips:
                    dest = mod_target_dir / zf_path.name
                    shutil.copy2(zf_path, dest)
                    installed_paths.append(str(dest))
                return installed_paths

            dest_zip = mod_target_dir / f"{archive_path.stem}.zip"
            with zipfile.ZipFile(dest_zip, "w", zipfile.ZIP_DEFLATED) as zf:
                for f_item in staging_dir.rglob("*"):
                    if f_item.is_file():
                        zf.write(f_item, f_item.relative_to(staging_dir))
            return [str(dest_zip)]

        # 2. Rise of the Tomb Raider / Shadow of the Tomb Raider / TR2013:
        #    Pre-configure the game path so RottrModManager NEVER shows the folder error,
        #    then pass the archive directly into RottrModManager.exe!
        if str(appid) in {"391220", "750920", "203160"} or sub_mode == "rottr_direct_loader":
            ModLoaderAutoInstaller.configure_rottr_game_path(game_root, appid)
            rottr_exe = ModLoaderAutoInstaller.get_rottr_manager_exe(game_root)
            if not rottr_exe:
                raise RuntimeError(
                    "Tomb Raider Mod Loader (RottrModManager.exe) was not found in the game folder. "
                    "Please click 'Auto-Install Loader' first."
                )

            saved_archive = ROTTR_ARCHIVES_DIR / archive_path.name
            shutil.copy2(archive_path, saved_archive)

            before_files = {}
            for p in game_root.rglob("*"):
                if p.is_file() and (
                    p.suffix.lower() == ".tiger"
                    or "mods" in {pt.lower() for pt in p.relative_to(game_root).parts}
                ):
                    before_files[str(p.relative_to(game_root))] = p.stat().st_mtime

            proc = subprocess.Popen([str(rottr_exe), str(saved_archive)], cwd=str(rottr_exe.parent))
            proc.wait()

            for p in game_root.rglob("*"):
                if p.is_file() and (
                    p.suffix.lower() == ".tiger"
                    or "mods" in {pt.lower() for pt in p.relative_to(game_root).parts}
                ):
                    rel_str = str(p.relative_to(game_root))
                    if rel_str not in before_files or p.stat().st_mtime > before_files[rel_str]:
                        installed_paths.append(rel_str)

            if not installed_paths:
                installed_paths.append(str(saved_archive))

            return installed_paths

        # 3. Unreal Engine Video / Movie Mods (e.g., ReadyOrNot/Content/Movies)
        if sub_mode == "ue_movies":
            mod_target_dir.mkdir(parents=True, exist_ok=True)
            effective_root = staging_dir

            for candidate_movies in staging_dir.rglob("*"):
                if candidate_movies.is_dir() and candidate_movies.name.lower() == "movies":
                    effective_root = candidate_movies
                    break
            else:
                top_items = list(effective_root.iterdir())
                while len(top_items) == 1 and top_items[0].is_dir():
                    effective_root = top_items[0]
                    top_items = list(effective_root.iterdir())

            for file_path in effective_root.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(effective_root)
                    dest = mod_target_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    cls._backup_vanilla_file_if_needed(appid, game_root, dest)
                    shutil.copy2(file_path, dest)
                    try:
                        installed_paths.append(str(dest.relative_to(game_root)))
                    except ValueError:
                        installed_paths.append(str(dest))
            return installed_paths

        # 4. Unreal Engine Audio / FMOD Mods (e.g., ReadyOrNot/Content/FMOD/Desktop)
        if sub_mode == "ue_fmod":
            mod_target_dir.mkdir(parents=True, exist_ok=True)
            for file_path in staging_dir.rglob("*"):
                if file_path.is_file():
                    if file_path.suffix.lower() in UE_AUDIO_EXTENSIONS:
                        dest = mod_target_dir / file_path.name
                    else:
                        dest = mod_target_dir / file_path.relative_to(staging_dir)
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    cls._backup_vanilla_file_if_needed(appid, game_root, dest)
                    shutil.copy2(file_path, dest)
                    try:
                        installed_paths.append(str(dest.relative_to(game_root)))
                    except ValueError:
                        installed_paths.append(str(dest))
            return installed_paths

        # 5. UE4SS Script / DLL Mods
        if sub_mode == "ue4ss_mod":
            mod_target_dir.mkdir(parents=True, exist_ok=True)
            effective_root = staging_dir
            top_items = list(effective_root.iterdir())

            for candidate_sub in effective_root.rglob("Mods"):
                if candidate_sub.is_dir() and candidate_sub.parent.name.lower() == "ue4ss":
                    effective_root = candidate_sub
                    top_items = list(effective_root.iterdir())
                    break

            if len(top_items) == 1 and top_items[0].is_dir() and top_items[0].name.lower() not in {"scripts", "dlls"}:
                mod_folder_name = top_items[0].name
                effective_root = top_items[0]
            else:
                mod_folder_name = re.sub(r"[^a-zA-Z0-9_\-]", "_", archive_path.stem)

            final_mod_dir = mod_target_dir / mod_folder_name
            final_mod_dir.mkdir(parents=True, exist_ok=True)

            for file_path in effective_root.rglob("*"):
                if file_path.is_file():
                    rel = file_path.relative_to(effective_root)
                    dest = final_mod_dir / rel
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(file_path, dest)
                    try:
                        installed_paths.append(str(dest.relative_to(game_root)))
                    except ValueError:
                        installed_paths.append(str(dest))

            enabled_txt = final_mod_dir / "enabled.txt"
            if not enabled_txt.exists():
                enabled_txt.write_text("", encoding="utf-8")
                try:
                    installed_paths.append(str(enabled_txt.relative_to(game_root)))
                except ValueError:
                    installed_paths.append(str(enabled_txt))

            return installed_paths

        # 6. General & Unreal Engine Pak / Blueprint LogicMods Routing
        try:
            target_parts_lower = {p.lower() for p in mod_target_dir.relative_to(game_root).parts}
            is_inside_game_root = True
        except ValueError:
            target_parts_lower = set()
            is_inside_game_root = False

        effective_root = staging_dir
        top_items = list(effective_root.iterdir())
        existing_root_dirs = {d.name.lower() for d in game_root.iterdir() if d.is_dir()}

        while len(top_items) == 1 and top_items[0].is_dir():
            folder_name = top_items[0].name.lower()
            if (
                folder_name in existing_root_dirs
                or folder_name in target_parts_lower
                or folder_name in {"bepinex", "data", "content", "paks", "movies", "fmod", "logicmods", "binaries", "mods", "natives", "archive"}
            ):
                break
            effective_root = top_items[0]
            top_items = list(effective_root.iterdir())

        first_level_dirs = [d for d in effective_root.iterdir() if d.is_dir()]
        if is_inside_game_root and first_level_dirs and all(d.name.lower() in existing_root_dirs for d in first_level_dirs):
            for file_path in effective_root.rglob("*"):
                if file_path.is_file():
                    rel_to_eff = file_path.relative_to(effective_root)
                    dest = game_root / rel_to_eff
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    cls._backup_vanilla_file_if_needed(appid, game_root, dest)
                    shutil.copy2(file_path, dest)
                    installed_paths.append(str(dest.relative_to(game_root)))
            return installed_paths

        if mod_target_dir.name.lower() in ("paks", "~mods", "logicmods"):
            if (effective_root / "Content" / "Paks" / "LogicMods").exists() and mod_target_dir.name.lower() == "logicmods":
                effective_root = effective_root / "Content" / "Paks" / "LogicMods"
            elif (effective_root / "LogicMods").exists() and mod_target_dir.name.lower() == "logicmods":
                effective_root = effective_root / "LogicMods"
            elif (effective_root / "Content" / "Paks").exists():
                effective_root = effective_root / "Content" / "Paks"
            elif (effective_root / "Paks").exists():
                effective_root = effective_root / "Paks"

        for file_path in effective_root.rglob("*"):
            if file_path.is_file():
                ext = file_path.suffix.lower()
                rel_to_eff = file_path.relative_to(effective_root)

                if mod_target_dir.name.lower() in ("paks", "~mods", "logicmods") and ext in UE_PAK_EXTENSIONS:
                    dest = mod_target_dir / file_path.name
                else:
                    dest = mod_target_dir / rel_to_eff

                dest.parent.mkdir(parents=True, exist_ok=True)
                cls._backup_vanilla_file_if_needed(appid, game_root, dest)
                shutil.copy2(file_path, dest)
                if is_inside_game_root:
                    installed_paths.append(str(dest.relative_to(game_root)))
                else:
                    installed_paths.append(str(dest))

        return installed_paths


# ==========================================
# ULTRA-FAST STEAM SCANNER & LAZY ANTI-CHEAT DETECTOR
# ==========================================
ANTICHEAT_SIGNATURES = [
    "easyanticheat", "battleye", "beservice", "beclient",
    "vgk.sys", "vanguard", "eaanticheat", "punkbuster",
    "nprotect", "gameguard", "equ8", "ricochet", "xigncode"
]


class SteamScanner:
    @staticmethod
    def get_steam_root() -> Path:
        if sys.platform == "win32":
            import winreg
            registry_keys = [
                (winreg.HKEY_CURRENT_USER, r"Software\Valve\Steam", "SteamPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Valve\Steam", "InstallPath"),
                (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Valve\Steam", "InstallPath")
            ]
            for root, subkey, value_name in registry_keys:
                try:
                    with winreg.OpenKey(root, subkey) as key:
                        path_str, _ = winreg.QueryValueEx(key, value_name)
                        if path_str and Path(path_str).exists():
                            return Path(path_str)
                except OSError:
                    continue

        for p in [Path(r"C:\Program Files (x86)\Steam"), Path(r"C:\Program Files\Steam")]:
            if p.exists():
                return p
        return Path()

    @classmethod
    def get_library_folders(cls) -> list[Path]:
        steam_root = cls.get_steam_root()
        if not steam_root or not steam_root.exists():
            return []

        libraries = [steam_root / "steamapps"]
        vdf_path = steam_root / "steamapps" / "libraryfolders.vdf"

        if vdf_path.exists():
            try:
                content = vdf_path.read_text(encoding="utf-8", errors="ignore")
                paths = re.findall(r'"path"\s+"([^"]+)"', content)
                for p in paths:
                    normalized = Path(p.replace("\\\\", "\\")) / "steamapps"
                    if normalized.exists() and normalized not in libraries:
                        libraries.append(normalized)
            except Exception:
                pass
        return libraries

    @classmethod
    def scan_installed_games(cls) -> list[dict]:
        games = []
        seen_ids = set()

        for lib in cls.get_library_folders():
            for acf_file in lib.glob("appmanifest_*.acf"):
                try:
                    data = acf_file.read_text(encoding="utf-8", errors="ignore")
                    appid_m = re.search(r'"appid"\s+"(\d+)"', data)
                    name_m = re.search(r'"name"\s+"([^"]+)"', data)
                    dir_m = re.search(r'"installdir"\s+"([^"]+)"', data)

                    if not (appid_m and name_m and dir_m):
                        continue

                    appid = appid_m.group(1)
                    name = name_m.group(1)
                    install_dir = lib / "common" / dir_m.group(1)

                    if appid == "228980" or "Steamworks" in name or not install_dir.exists():
                        continue

                    if appid not in seen_ids:
                        seen_ids.add(appid)
                        games.append({
                            "appid": appid,
                            "name": name,
                            "install_dir": str(install_dir),
                            "has_anticheat_or_mp": None,
                            "verified_mod_sites": None
                        })
                except Exception:
                    continue

        return sorted(games, key=lambda g: g["name"].lower())

    @staticmethod
    def detect_local_anticheat(game_dir: Path) -> bool:
        try:
            for root, dirs, files in os.walk(game_dir):
                rel_depth = len(Path(root).relative_to(game_dir).parts)
                if rel_depth > 2:
                    continue
                combined = [d.lower() for d in dirs] + [f.lower() for f in files]
                for item in combined:
                    if any(sig in item for sig in ANTICHEAT_SIGNATURES):
                        return True
        except Exception:
            pass
        return False

    @classmethod
    def check_anticheat_or_multiplayer_lazy(cls, game: dict) -> bool:
        if game.get("has_anticheat_or_mp") is not None:
            return bool(game["has_anticheat_or_mp"])

        appid = str(game["appid"])
        cache_flag = CACHE_DIR / f"{appid}_ac_mp.flag"
        if cache_flag.exists():
            res = cache_flag.read_text().strip() == "1"
            game["has_anticheat_or_mp"] = res
            return res

        local_ac = cls.detect_local_anticheat(Path(game["install_dir"]))
        if local_ac:
            cache_flag.write_text("1")
            game["has_anticheat_or_mp"] = True
            return True

        mp_category_ids = {1, 8, 9, 20, 27, 36, 38, 49}
        is_mp = False
        try:
            url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
            resp = requests.get(url, timeout=4).json()
            if resp and resp.get(appid, {}).get("success"):
                categories = resp[appid]["data"].get("categories", [])
                for cat in categories:
                    if cat.get("id") in mp_category_ids:
                        is_mp = True
                        break
            cache_flag.write_text("1" if is_mp else "0")
        except Exception:
            pass

        game["has_anticheat_or_mp"] = is_mp
        return is_mp


# ==========================================
# MOD ARCHIVE INSTALLER & BULK MANAGER
# ==========================================
class ModController:
    def __init__(self):
        self.manifest = self._load_manifest()

    def _load_manifest(self) -> dict:
        if MANIFEST_FILE.exists():
            try:
                return json.loads(MANIFEST_FILE.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def _save_manifest(self):
        MANIFEST_FILE.write_text(json.dumps(self.manifest, indent=2), encoding="utf-8")

    def get_mods_for_game(self, appid: str) -> list[dict]:
        return self.manifest.get(str(appid), [])

    def get_enabled_mod_count(self, appid: str) -> int:
        mods = self.get_mods_for_game(str(appid))
        return sum(1 for m in mods if m.get("enabled", True))

    def rename_mod(self, appid: str, mod_id: str, new_name: str) -> bool:
        mods = self.manifest.get(str(appid), [])
        for m in mods:
            if m["id"] == mod_id:
                m["name"] = new_name.strip()
                m["custom_named"] = True
                self._save_manifest()
                return True
        return False

    @staticmethod
    def _resolve_file_path(game_dir: Path, stored_path: str) -> Path:
        p = Path(stored_path)
        return p if p.is_absolute() else (game_dir / p)

    @staticmethod
    def _restore_vanilla_backup_if_exists(appid: str, game_dir: Path, stored_path: str) -> bool:
        p = Path(stored_path)
        if p.is_absolute():
            try:
                rel = p.relative_to(game_dir)
            except ValueError:
                return False
        else:
            rel = p

        backup_file = VANILLA_BACKUP_DIR / str(appid) / rel
        target_file = game_dir / rel
        if backup_file.exists() and backup_file.is_file():
            try:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(backup_file, target_file)
                return True
            except Exception:
                return False
        return False

    def prepare_and_inspect_archive(
        self,
        game: dict,
        archive_path: str,
        default_mod_target_dir: Path,
        loader_id: str | None,
        loader_name: str | None
    ) -> tuple[bool, str, Path | None, dict | None]:
        archive = Path(archive_path)
        if not archive.exists():
            return False, "Archive file not found.", None, None

        ext = archive.suffix.lower()
        if ext not in SUPPORTED_ARCHIVES:
            return False, "Only .zip, .rar, and .7z archives are supported.", None, None

        game_root = Path(game["install_dir"])
        if not game_root.exists():
            return False, f"Game folder does not exist:\n{game_root}", None, None

        staging_dir = APP_DATA_DIR / "staging_temp"
        if staging_dir.exists():
            shutil.rmtree(staging_dir, ignore_errors=True)
        staging_dir.mkdir(parents=True, exist_ok=True)

        try:
            appid = str(game["appid"])
            is_beamng = (appid == "284160" or "beamng" in game["name"].lower())

            if not (is_beamng and ext == ".zip"):
                if ext == ".zip":
                    with zipfile.ZipFile(archive, "r") as zf:
                        zf.extractall(staging_dir)
                elif ext == ".7z":
                    self._extract_7z(archive, staging_dir)
                elif ext == ".rar":
                    self._extract_rar(archive, staging_dir)

            inspection = ArchiveModInspector.inspect_archive_contents(
                archive_path=archive,
                staging_dir=staging_dir,
                game=game,
                default_mod_target_dir=default_mod_target_dir,
                loader_id=loader_id,
                loader_name=loader_name
            )
            return True, "OK", staging_dir, inspection
        except Exception as e:
            shutil.rmtree(staging_dir, ignore_errors=True)
            return False, f"Extraction error: {str(e)}", None, None

    def finalize_mod_installation(
        self,
        game: dict,
        archive_path: str,
        staging_dir: Path,
        inspection: dict
    ) -> tuple[bool, str]:
        archive = Path(archive_path)
        game_root = Path(game["install_dir"])
        appid = str(game["appid"])
        target_dir = inspection["target_dir"]
        sub_mode = inspection.get("sub_mode", "standard")
        mod_type_label = inspection.get("mod_type_label", "Mod")

        try:
            clean_display_name = format_simple_mod_name(archive.stem, staging_dir)

            installed_files = SmartModRouter.smart_place_extracted_files(
                archive_path=archive,
                staging_dir=staging_dir,
                game_root=game_root,
                mod_target_dir=target_dir,
                appid=appid,
                sub_mode=sub_mode
            )

            if not installed_files:
                return False, "The archive appeared to be empty."

            if appid not in self.manifest:
                self.manifest[appid] = []

            try:
                rel_target_display = (
                    str(target_dir.relative_to(game_root))
                    if target_dir != game_root
                    else "Game Root (via Mod Loader)"
                )
            except ValueError:
                rel_target_display = str(target_dir)

            mod_entry = {
                "id": f"{archive.stem}_{int(datetime.now().timestamp())}",
                "name": clean_display_name,
                "archive_name": archive.name,
                "mod_type": mod_type_label,
                "target_subpath": rel_target_display,
                "installed_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "enabled": True,
                "files": installed_files
            }
            self.manifest[appid].append(mod_entry)
            self._save_manifest()
            return (
                True,
                f"✅ Installed '{clean_display_name}' into {rel_target_display} ({len(installed_files)} file(s))."
            )
        except Exception as e:
            return False, f"Installation error: {str(e)}"
        finally:
            shutil.rmtree(staging_dir, ignore_errors=True)

    @staticmethod
    def _extract_7z(sevenz_path: Path, extract_to: Path):
        try:
            import py7zr
            with py7zr.SevenZipFile(sevenz_path, mode="r") as z:
                z.extractall(path=extract_to)
            return
        except Exception:
            pass

        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        bundled_7z = base_dir / "7z.exe"
        sevenzip_system = Path(r"C:\Program Files\7-Zip\7z.exe")

        if bundled_7z.exists():
            cmd = [str(bundled_7z), "x", str(sevenz_path), f"-o{extract_to}", "-y"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        elif sevenzip_system.exists():
            cmd = [str(sevenzip_system), "x", str(sevenz_path), f"-o{extract_to}", "-y"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        else:
            import patoolib
            patoolib.extract_archive(str(sevenz_path), outdir=str(extract_to), verbosity=-1)

    @staticmethod
    def _extract_rar(rar_path: Path, extract_to: Path):
        base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
        bundled_unrar = base_dir / "UnRAR.exe"
        bundled_7z = base_dir / "7z.exe"

        winrar_system = Path(r"C:\Program Files\WinRAR\UnRAR.exe")
        sevenzip_system = Path(r"C:\Program Files\7-Zip\7z.exe")

        if bundled_unrar.exists():
            cmd = [str(bundled_unrar), "x", "-y", str(rar_path), f"{extract_to}\\"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        elif winrar_system.exists():
            cmd = [str(winrar_system), "x", "-y", str(rar_path), f"{extract_to}\\"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        elif bundled_7z.exists():
            cmd = [str(bundled_7z), "x", str(rar_path), f"-o{extract_to}", "-y"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        elif sevenzip_system.exists():
            cmd = [str(sevenzip_system), "x", str(rar_path), f"-o{extract_to}", "-y"]
            subprocess.run(cmd, check=True, capture_output=True, text=True, creationflags=0x08000000)
        else:
            import patoolib
            patoolib.extract_archive(str(rar_path), outdir=str(extract_to), verbosity=-1)

    def toggle_mod_state(self, game: dict, mod_id: str) -> tuple[bool, str]:
        appid = str(game["appid"])
        mods = self.manifest.get(appid, [])
        target_mod = next((m for m in mods if m["id"] == mod_id), None)

        if not target_mod:
            return False, "Mod entry not found."

        game_dir = Path(game["install_dir"])
        vault_dir = DISABLED_MODS_DIR / appid / mod_id
        currently_enabled = target_mod.get("enabled", True)

        try:
            if currently_enabled:
                vault_dir.mkdir(parents=True, exist_ok=True)
                moved_count = 0
                for idx, stored_file in enumerate(target_mod.get("files", [])):
                    active_path = self._resolve_file_path(game_dir, stored_file)
                    vault_file = vault_dir / f"file_{idx}" / active_path.name
                    if active_path.exists() and active_path.is_file():
                        vault_file.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(active_path), str(vault_file))
                        self._restore_vanilla_backup_if_exists(appid, game_dir, stored_file)
                        moved_count += 1

                target_mod["enabled"] = False
                self._save_manifest()
                return True, f"⏸️ Disabled '{target_mod['name']}' ({moved_count} file(s) moved to vault)."
            else:
                restored_count = 0
                for idx, stored_file in enumerate(target_mod.get("files", [])):
                    active_path = self._resolve_file_path(game_dir, stored_file)
                    vault_file = vault_dir / f"file_{idx}" / active_path.name
                    if vault_file.exists() and vault_file.is_file():
                        active_path.parent.mkdir(parents=True, exist_ok=True)
                        shutil.move(str(vault_file), str(active_path))
                        restored_count += 1

                shutil.rmtree(vault_dir, ignore_errors=True)
                target_mod["enabled"] = True
                self._save_manifest()
                return True, f"🟢 Enabled '{target_mod['name']}' ({restored_count} file(s) restored)."
        except Exception as e:
            return False, f"Failed to toggle mod: {str(e)}"

    def set_all_mods_state(self, game: dict, enable: bool) -> tuple[bool, str]:
        appid = str(game["appid"])
        mods = self.manifest.get(appid, [])
        if not mods:
            return False, "No mods installed for this game."

        changed_mods = 0
        for mod in mods:
            is_enabled = mod.get("enabled", True)
            if is_enabled != enable:
                ok, _ = self.toggle_mod_state(game, mod["id"])
                if ok:
                    changed_mods += 1

        action_word = "Enabled" if enable else "Disabled"
        if changed_mods == 0:
            return True, f"All mods are already {action_word.lower()}."
        return True, f"{action_word} {changed_mods} mod(s) simultaneously."

    def uninstall_mod(self, game: dict, mod_id: str) -> tuple[bool, str]:
        appid = str(game["appid"])
        mods = self.manifest.get(appid, [])
        target_mod = next((m for m in mods if m["id"] == mod_id), None)

        if not target_mod:
            return False, "Mod entry not found in manifest."

        game_dir = Path(game["install_dir"])
        vault_dir = DISABLED_MODS_DIR / appid / mod_id

        for stored_file in target_mod.get("files", []):
            full_path = self._resolve_file_path(game_dir, stored_file)
            try:
                if full_path.exists() and full_path.is_file():
                    full_path.unlink()
                self._restore_vanilla_backup_if_exists(appid, game_dir, stored_file)
            except Exception:
                continue

        if vault_dir.exists():
            shutil.rmtree(vault_dir, ignore_errors=True)

        self.manifest[appid] = [m for m in mods if m["id"] != mod_id]
        self._save_manifest()
        return True, f"🗑️ Removed '{target_mod['name']}' completely."


# ==========================================
# MOD WEBSITES HUB DIALOG (VERIFIED PER GAME)
# ==========================================
class ModSitesDialog(ctk.CTkToplevel):
    """
    Displays ONLY verified modding websites that actually have a hub/mods for the selected game,
    linking directly to the game's exact URL on each site.
    """

    def __init__(self, parent, game: dict):
        super().__init__(parent)
        self.game = game
        game_name = game["name"]

        self.title(f"Verified Mod Sites — {game_name}")
        self.geometry("620x390")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_root"])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 310
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 195
        self.geometry(f"+{max(px, 50)}+{max(py, 50)}")

        header = ctk.CTkFrame(self, fg_color=THEME["bg_card"], corner_radius=12)
        header.pack(fill="x", padx=16, pady=(16, 10))

        ctk.CTkLabel(
            header,
            text=f"🌐  Verified Mod Sites for {game_name}",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=THEME["text_main"]
        ).pack(padx=16, pady=(12, 2), anchor="w")

        ctk.CTkLabel(
            header,
            text="Only sites confirmed to host mods for this game are listed below:",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        ).pack(padx=16, pady=(0, 12), anchor="w")

        self.scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            scrollbar_button_color=THEME["accent"]
        )
        self.scroll.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        self.scroll.grid_columnconfigure(0, weight=1)

        cached_sites = game.get("verified_mod_sites")
        if cached_sites is not None:
            self._render_sites(cached_sites)
        else:
            self.loading_lbl = ctk.CTkLabel(
                self.scroll,
                text=f"🔍 Checking Nexus Mods, Thunderstore, Mod.io & CurseForge for {game_name}...",
                font=ctk.CTkFont(size=13, weight="bold"),
                text_color=THEME["text_muted"]
            )
            self.loading_lbl.grid(row=0, column=0, pady=45)
            threading.Thread(target=self._verify_worker, daemon=True).start()

    def _verify_worker(self):
        sites = ModSiteVerifier.verify_sites_for_game(self.game)
        self.game["verified_mod_sites"] = sites
        if self.winfo_exists():
            self.after(0, lambda: self._render_sites(sites))

    def _render_sites(self, sites: list[dict]):
        for w in self.scroll.winfo_children():
            w.destroy()

        if not sites:
            ctk.CTkLabel(
                self.scroll,
                text=f"No dedicated mod repositories were found for {self.game['name']}.",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"]
            ).grid(row=0, column=0, pady=45)
            return

        for idx, site in enumerate(sites):
            row = ctk.CTkFrame(self.scroll, fg_color=THEME["bg_card"], corner_radius=10)
            row.grid(row=idx, column=0, sticky="ew", padx=4, pady=5)
            row.grid_columnconfigure(0, weight=1)

            info_box = ctk.CTkFrame(row, fg_color="transparent")
            info_box.grid(row=0, column=0, padx=14, pady=10, sticky="w")

            ctk.CTkLabel(
                info_box,
                text=f"{site['icon']}  {site['name']}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=THEME["text_main"]
            ).pack(anchor="w")

            ctk.CTkLabel(
                info_box,
                text=site["desc"],
                font=ctk.CTkFont(size=12),
                text_color=THEME["text_muted"]
            ).pack(anchor="w", pady=(2, 0))

            open_btn = ctk.CTkButton(
                row,
                text="Open Site ↗",
                fg_color=THEME["accent"],
                hover_color=THEME["accent_hover"],
                font=ctk.CTkFont(size=12, weight="bold"),
                width=120,
                height=32,
                command=lambda u=site["url"]: webbrowser.open(u)
            )
            open_btn.grid(row=0, column=1, padx=14, pady=10, sticky="e")


# ==========================================
# MODAL DIALOG WHEN A MOD REQUIRES A MOD LOADER
# ==========================================
class ModLoaderRequiredDialog(ctk.CTkToplevel):
    def __init__(self, parent, mod_name: str, mod_type: str, loader_name: str, target_dir: Path):
        super().__init__(parent)
        self.result = "cancel"
        self.title("Mod Loader Required")
        self.geometry("560x310")
        self.resizable(False, False)
        self.configure(fg_color=THEME["bg_root"])
        self.transient(parent)
        self.grab_set()

        self.update_idletasks()
        px = parent.winfo_rootx() + (parent.winfo_width() // 2) - 280
        py = parent.winfo_rooty() + (parent.winfo_height() // 2) - 155
        self.geometry(f"+{max(px, 50)}+{max(py, 50)}")

        card = ctk.CTkFrame(
            self,
            fg_color=THEME["bg_card"],
            border_color=THEME["loader_border"],
            border_width=2,
            corner_radius=14
        )
        card.pack(fill="both", expand=True, padx=16, pady=16)

        ctk.CTkLabel(
            card,
            text="⚠️  This Mod Requires a Mod Loader",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color="#38bdf8"
        ).pack(padx=20, pady=(18, 8), anchor="w")

        msg = (
            f"The mod '{mod_name}' was detected as a {mod_type}.\n\n"
            f"It requires the following Mod Loader to work in-game:\n"
            f"• {loader_name}\n\n"
            f"Detected Mod Install Directory:\n"
            f"📁 {target_dir}"
        )
        ctk.CTkLabel(
            card,
            text=msg,
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_main"],
            justify="left",
            wraplength=500
        ).pack(padx=20, pady=(0, 18), anchor="w")

        btn_row = ctk.CTkFrame(card, fg_color="transparent")
        btn_row.pack(fill="x", padx=20, pady=(0, 14))

        dl_btn = ctk.CTkButton(
            btn_row,
            text="⚡ Download Loader & Install Mod",
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=13, weight="bold"),
            height=36,
            command=self._on_download_and_install
        )
        dl_btn.pack(side="left", padx=(0, 8))

        install_only_btn = ctk.CTkButton(
            btn_row,
            text="Install Mod Only",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            width=130,
            height=36,
            command=self._on_install_only
        )
        install_only_btn.pack(side="left", padx=(0, 8))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            fg_color=THEME["disabled_bg"],
            hover_color=THEME["disabled_hover"],
            width=90,
            height=36,
            command=self._on_cancel
        )
        cancel_btn.pack(side="right")

    def _on_download_and_install(self):
        self.result = "download_loader_and_install"
        self.grab_release()
        self.destroy()

    def _on_install_only(self):
        self.result = "install_only"
        self.grab_release()
        self.destroy()

    def _on_cancel(self):
        self.result = "cancel"
        self.grab_release()
        self.destroy()


# ==========================================
# MAIN GUI APPLICATION
# ==========================================
BaseWindowClass = ctk.CTk
if DND_AVAILABLE:
    class DnDCTk(ctk.CTk, TkinterDnD.DnDWrapper):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.TkdndVersion = TkinterDnD._require(self)
    BaseWindowClass = DnDCTk


class NebulaModManagerApp(BaseWindowClass):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        self.title(f"Nebula — Smart Steam Mod Manager (v{APP_VERSION})")
        self.geometry("1280x810")
        self.minsize(1080, 680)
        self.configure(fg_color=THEME["bg_root"])

        # 1. Build & render Welcome Splash Screen FIRST so the window appears in < 0.1s!
        self._build_welcome_splash_screen()
        self.update()

        icon_file = ensure_app_icon()
        if icon_file.exists():
            try:
                self.iconbitmap(str(icon_file))
            except Exception:
                pass

        thumb_pil = create_placeholder_cover_image(92, 43)
        banner_pil = create_placeholder_cover_image(184, 86)
        self.placeholder_thumb_ctk = ctk.CTkImage(light_image=thumb_pil, dark_image=thumb_pil, size=(92, 43))
        self.placeholder_banner_ctk = ctk.CTkImage(light_image=banner_pil, dark_image=banner_pil, size=(184, 86))

        self.cover_executor = ThreadPoolExecutor(max_workers=4)

        self.mod_controller = ModController()
        self.games = []
        self.selected_game = None
        self.current_mod_target_dir = None
        self.current_loader_id = None
        self.current_loader_name = None
        self.current_loader_installed = False
        self.current_loader_search_query = None
        self.sidebar_filter_mode = "All Games"
        self.game_tab_widgets = {}
        self.image_cache = {}
        self._search_debounce_job = None
        self._header_anim_job = None
        self._welcome_progress_val = 0.0
        self._welcome_scan_done = False
        self._scanned_games_buffer = []

        # 2. Build main layout behind the welcome splash screen and start fast boot + update check
        self._build_layout()
        self.welcome_frame.lift()
        self.after(20, self._start_welcome_boot_sequence)

    def _build_layout(self):
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # ---- LEFT SIDEBAR ----
        self.sidebar = ctk.CTkFrame(self, width=335, corner_radius=0, fg_color=THEME["bg_sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)
        self.sidebar.grid_rowconfigure(3, weight=1)
        self.sidebar.grid_columnconfigure(0, weight=1)

        title_row = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        title_row.grid(row=0, column=0, padx=18, pady=(20, 6), sticky="ew")
        title_row.grid_columnconfigure(0, weight=1)

        title_lbl = ctk.CTkLabel(
            title_row,
            text="NEBULA MODS",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=THEME["accent"]
        )
        title_lbl.grid(row=0, column=0, sticky="w")

        self.found_games_badge = ctk.CTkLabel(
            title_row,
            text="0 Games",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=THEME["bg_card"],
            text_color=THEME["text_muted"],
            corner_radius=8,
            padx=10,
            pady=3
        )
        self.found_games_badge.grid(row=0, column=1, sticky="e")

        self.search_entry = ctk.CTkEntry(
            self.sidebar,
            placeholder_text="Search Steam library...",
            fg_color=THEME["bg_card"],
            border_color=THEME["accent"],
            text_color=THEME["text_main"],
            height=36
        )
        self.search_entry.grid(row=1, column=0, padx=16, pady=(4, 6), sticky="ew")
        self.search_entry.bind("<KeyRelease>", self._on_search_key_released)

        self.filter_segment = ctk.CTkSegmentedButton(
            self.sidebar,
            values=["All Games", "Modded / Loaders"],
            selected_color=THEME["accent"],
            selected_hover_color=THEME["accent_hover"],
            unselected_color=THEME["bg_card"],
            unselected_hover_color=THEME["bg_card_hover"],
            text_color=THEME["text_main"],
            font=ctk.CTkFont(size=12, weight="bold"),
            height=32,
            command=self._on_sidebar_filter_changed
        )
        self.filter_segment.set("All Games")
        self.filter_segment.grid(row=2, column=0, padx=16, pady=(0, 8), sticky="ew")

        self.games_scroll = ctk.CTkScrollableFrame(
            self.sidebar,
            fg_color="transparent",
            scrollbar_button_color=THEME["accent"]
        )
        self.games_scroll.grid(row=3, column=0, padx=10, pady=2, sticky="nsew")
        self.games_scroll.grid_columnconfigure(0, weight=1)

        sidebar_footer = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        sidebar_footer.grid(row=4, column=0, padx=16, pady=12, sticky="ew")
        sidebar_footer.grid_columnconfigure(0, weight=1)
        sidebar_footer.grid_columnconfigure(1, weight=1)

        rescan_btn = ctk.CTkButton(
            sidebar_footer,
            text="🔄 Rescan Steam Games",
            fg_color=THEME["bg_card"],
            hover_color=THEME["accent_hover"],
            command=self._rescan_steam_games_click,
            height=34
        )
        rescan_btn.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        report_bug_btn = ctk.CTkButton(
            sidebar_footer,
            text="🐛 Report Bug",
            fg_color="#1e1b4b",
            hover_color="#312e81",
            border_color=THEME["accent"],
            border_width=1,
            text_color="#c4b5fd",
            command=self._open_github_bug_report,
            height=32
        )
        report_bug_btn.grid(row=1, column=0, sticky="ew", padx=(0, 4))

        github_source_btn = ctk.CTkButton(
            sidebar_footer,
            text="⭐ GitHub Source",
            fg_color="#1e1b4b",
            hover_color="#312e81",
            border_color=THEME["accent"],
            border_width=1,
            text_color="#c4b5fd",
            command=lambda: webbrowser.open(GITHUB_REPO_URL),
            height=32
        )
        github_source_btn.grid(row=1, column=1, sticky="ew", padx=(4, 0))

        # ---- RIGHT CONTENT PANEL ----
        self.main_panel = ctk.CTkFrame(self, fg_color=THEME["bg_root"], corner_radius=0)
        self.main_panel.grid(row=0, column=1, sticky="nsew", padx=24, pady=18)
        self.main_panel.grid_columnconfigure(0, weight=1)
        self.main_panel.grid_rowconfigure(4, weight=1)

        # 1. Game Header Banner
        self.header_frame = ctk.CTkFrame(
            self.main_panel,
            fg_color=THEME["bg_card"],
            border_color=THEME["accent"],
            border_width=1,
            corner_radius=12
        )
        self.header_frame.grid(row=0, column=0, sticky="ew", pady=(0, 10))
        self.header_frame.grid_columnconfigure(1, weight=1)

        self.banner_img_lbl = ctk.CTkLabel(
            self.header_frame,
            text="",
            image=self.placeholder_banner_ctk,
            width=184,
            height=86
        )
        self.banner_img_lbl.grid(row=0, column=0, padx=14, pady=12)

        header_info = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        header_info.grid(row=0, column=1, sticky="w", padx=6, pady=10)

        self.game_title_lbl = ctk.CTkLabel(
            header_info,
            text="Select a Steam Game",
            font=ctk.CTkFont(size=22, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.game_title_lbl.pack(anchor="w")

        self.game_path_lbl = ctk.CTkLabel(
            header_info,
            text="Your detected Steam games appear in the left sidebar.",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"]
        )
        self.game_path_lbl.pack(anchor="w", pady=(2, 0))

        self.mod_target_lbl = ctk.CTkLabel(
            header_info,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["text_success"],
            wraplength=460,
            justify="left"
        )
        self.mod_target_lbl.pack(anchor="w", pady=(4, 0))

        # Top-Right Action Buttons Grid (Mod Sites appears ONLY here)
        btn_grid = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        btn_grid.grid(row=0, column=2, padx=14, pady=10)

        self.play_game_btn = ctk.CTkButton(
            btn_grid,
            text="▶  Play Game",
            fg_color=THEME["play_bg"],
            hover_color=THEME["play_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            width=145,
            height=32,
            command=self._launch_selected_game,
            state="disabled"
        )
        self.play_game_btn.grid(row=0, column=0, padx=4, pady=4)

        self.mod_sites_btn = ctk.CTkButton(
            btn_grid,
            text="🌐  Mod Sites",
            fg_color=THEME["sites_bg"],
            hover_color=THEME["sites_hover"],
            font=ctk.CTkFont(size=13, weight="bold"),
            width=145,
            height=32,
            command=self._open_mod_sites_dialog,
            state="disabled"
        )
        self.mod_sites_btn.grid(row=0, column=1, padx=4, pady=4)

        self.open_folder_btn = ctk.CTkButton(
            btn_grid,
            text="Open Mod Folder",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            width=145,
            height=30,
            command=self._open_mod_folder,
            state="disabled"
        )
        self.open_folder_btn.grid(row=1, column=0, padx=4, pady=4)

        self.change_target_btn = ctk.CTkButton(
            btn_grid,
            text="Change Mod Path",
            fg_color=THEME["bg_sidebar"],
            hover_color=THEME["bg_card_hover"],
            border_color=THEME["accent"],
            border_width=1,
            width=145,
            height=30,
            command=self._change_mod_target_dialog,
            state="disabled"
        )
        self.change_target_btn.grid(row=1, column=1, padx=4, pady=4)

        # 2. Anti-Cheat / Multiplayer Warning Banner
        self.warning_banner = ctk.CTkFrame(
            self.main_panel,
            fg_color=THEME["warning_bg"],
            border_color=THEME["warning_border"],
            border_width=2,
            corner_radius=10
        )
        self.warning_lbl = ctk.CTkLabel(
            self.warning_banner,
            text="⚠️  Warning: The selected game has an active anticheat or multiplayer",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#fef08a"
        )
        self.warning_lbl.pack(padx=16, pady=7, anchor="w")

        # 3. Mod Loader Requirement Banner
        self.loader_banner = ctk.CTkFrame(
            self.main_panel,
            fg_color=THEME["loader_bg"],
            border_color=THEME["loader_border"],
            border_width=2,
            corner_radius=10
        )
        self.loader_banner.grid_columnconfigure(0, weight=1)

        self.loader_lbl = ctk.CTkLabel(
            self.loader_banner,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#bae6fd",
            wraplength=470,
            justify="left"
        )
        self.loader_lbl.grid(row=0, column=0, padx=16, pady=7, sticky="w")

        loader_btn_frame = ctk.CTkFrame(self.loader_banner, fg_color="transparent")
        loader_btn_frame.grid(row=0, column=1, padx=12, pady=7, sticky="e")

        self.open_loader_gui_btn = ctk.CTkButton(
            loader_btn_frame,
            text="🛠️ Open Loader GUI",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            width=140,
            height=28,
            command=self._open_rottr_loader_gui_click
        )

        self.get_loader_btn = ctk.CTkButton(
            loader_btn_frame,
            text="⚡ Auto-Install Loader",
            fg_color="#0284c7",
            hover_color="#0369a1",
            font=ctk.CTkFont(size=12, weight="bold"),
            width=150,
            height=28,
            command=self._auto_install_mod_loader_click
        )
        self.get_loader_btn.pack(side="left", padx=(0, 6))

        self.delete_loader_btn = ctk.CTkButton(
            loader_btn_frame,
            text="🗑️ Delete Loader",
            fg_color=THEME["danger"],
            hover_color=THEME["danger_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            width=125,
            height=28,
            command=self._delete_mod_loader_click
        )
        self.delete_loader_btn.pack(side="left")

        # 4. Drag & Drop Zone (.zip / .rar / .7z) — Single Browse Button (No duplicate Mod Sites button)
        self.drop_zone = ctk.CTkFrame(
            self.main_panel,
            fg_color=THEME["bg_card"],
            border_color=THEME["accent"],
            border_width=2,
            corner_radius=14,
            height=118
        )
        self.drop_zone.grid(row=3, column=0, sticky="ew", pady=(0, 12))
        self.drop_zone.grid_propagate(False)
        self.drop_zone.grid_columnconfigure(0, weight=1)
        self.drop_zone.grid_rowconfigure(0, weight=1)

        drop_inner = ctk.CTkFrame(self.drop_zone, fg_color="transparent")
        drop_inner.grid(row=0, column=0)

        self.drop_title = ctk.CTkLabel(
            drop_inner,
            text="📦  Drag & Drop a .ZIP, .RAR, or .7Z Mod Archive Here (Auto-Detects Mods)",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.drop_title.pack(pady=(6, 4))

        self.browse_btn = ctk.CTkButton(
            drop_inner,
            text="📁 Browse Local Archive (.zip / .rar / .7z)",
            fg_color=THEME["accent"],
            hover_color=THEME["accent_hover"],
            height=32,
            command=self._browse_archive_dialog,
            state="disabled"
        )
        self.browse_btn.pack(pady=(2, 6))

        self.drop_zone.bind("<Enter>", lambda e: self.drop_zone.configure(border_color="#c084fc", fg_color="#251c42"))
        self.drop_zone.bind("<Leave>", lambda e: self.drop_zone.configure(border_color=THEME["accent"], fg_color=THEME["bg_card"]))

        if DND_AVAILABLE:
            self.drop_zone.drop_target_register(DND_FILES)
            self.drop_zone.dnd_bind("<<Drop>>", self._on_file_dropped)

        # 5. Installed Mods Container (With Search Bar for Installed Mods)
        mods_container = ctk.CTkFrame(self.main_panel, fg_color=THEME["bg_card"], corner_radius=12)
        mods_container.grid(row=4, column=0, sticky="nsew")
        mods_container.grid_columnconfigure(0, weight=1)
        mods_container.grid_rowconfigure(1, weight=1)

        mods_header = ctk.CTkFrame(mods_container, fg_color="transparent")
        mods_header.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))
        mods_header.grid_columnconfigure(1, weight=1)

        self.mods_header_lbl = ctk.CTkLabel(
            mods_header,
            text="Installed Mods  •  0 Loaded / 0 Total",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.mods_header_lbl.grid(row=0, column=0, sticky="w", padx=(0, 12))

        self.installed_mods_search_entry = ctk.CTkEntry(
            mods_header,
            placeholder_text="🔍 Search installed mods...",
            fg_color=THEME["bg_sidebar"],
            border_color=THEME["accent"],
            text_color=THEME["text_main"],
            height=30
        )
        self.installed_mods_search_entry.grid(row=0, column=1, sticky="ew", padx=(4, 12))
        self.installed_mods_search_entry.bind("<KeyRelease>", lambda e: self._refresh_installed_mods_ui())

        bulk_btns_frame = ctk.CTkFrame(mods_header, fg_color="transparent")
        bulk_btns_frame.grid(row=0, column=2, sticky="e")

        self.enable_all_btn = ctk.CTkButton(
            bulk_btns_frame,
            text="✅ Enable All",
            fg_color=THEME["success_bg"],
            hover_color=THEME["success_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            height=28,
            command=lambda: self._bulk_toggle_mods_click(True),
            state="disabled"
        )
        self.enable_all_btn.pack(side="left", padx=(0, 6))

        self.disable_all_btn = ctk.CTkButton(
            bulk_btns_frame,
            text="⏸️ Disable All",
            fg_color=THEME["disabled_bg"],
            hover_color=THEME["disabled_hover"],
            font=ctk.CTkFont(size=12, weight="bold"),
            width=110,
            height=28,
            command=lambda: self._bulk_toggle_mods_click(False),
            state="disabled"
        )
        self.disable_all_btn.pack(side="left")

        self.mods_list_frame = ctk.CTkScrollableFrame(
            mods_container,
            fg_color="transparent",
            scrollbar_button_color=THEME["accent"]
        )
        self.mods_list_frame.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 6))
        self.mods_list_frame.grid_columnconfigure(0, weight=1)

        # Dedicated Footer Status Bar
        self.status_bar_frame = ctk.CTkFrame(
            mods_container,
            fg_color=THEME["bg_sidebar"],
            corner_radius=8,
            height=32
        )
        self.status_bar_frame.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.status_bar_frame.grid_propagate(False)
        self.status_bar_frame.grid_columnconfigure(0, weight=1)

        self.status_lbl = ctk.CTkLabel(
            self.status_bar_frame,
            text="Ready.",
            font=ctk.CTkFont(size=12),
            text_color=THEME["text_muted"],
            anchor="w"
        )
        self.status_lbl.grid(row=0, column=0, padx=12, pady=4, sticky="ew")

    # ==========================================
    # GITHUB BUG REPORT & AUTO-UPDATE HANDLERS
    # ==========================================
    def _open_github_bug_report(self):
        game_info = (
            f"{self.selected_game['name']} (AppID: {self.selected_game['appid']})"
            if self.selected_game
            else "Specify Game Name"
        )
        mod_path_info = str(self.current_mod_target_dir or "Default")

        issue_title = quote_plus(f"[BUG] {self.selected_game['name'] if self.selected_game else 'Issue Report'}: ")
        issue_body = quote_plus(
            f"### Game Name & Steam AppID\n{game_info}\n\n"
            f"### Detected Mod Install Path\n`{mod_path_info}`\n\n"
            f"### Link to the Mod (Nexus Mods / Mod.io / etc.)\nPaste link here:\n\n"
            f"### What Happened?\nDescribe what happened when installing the mod or loader:\n"
        )
        bug_url = f"{GITHUB_REPO_URL}/issues/new?title={issue_title}&body={issue_body}"
        webbrowser.open(bug_url)

    def _check_github_updates_async(self):
        def worker():
            update_info = AppAutoUpdater.check_for_updates()
            if update_info:
                self.after(200, lambda: UpdatePromptDialog(self, update_info))

        threading.Thread(target=worker, daemon=True).start()

    # ==========================================
    # WELCOME TO NEBULA MOD MANAGER SPLASH SCREEN
    # ==========================================
    def _build_welcome_splash_screen(self):
        self.welcome_frame = ctk.CTkFrame(self, fg_color=THEME["bg_root"], corner_radius=0)
        self.welcome_frame.place(relx=0.0, rely=0.0, relwidth=1.0, relheight=1.0)
        self.welcome_frame.lift()

        center_card = ctk.CTkFrame(
            self.welcome_frame,
            fg_color=THEME["bg_card"],
            border_color=THEME["accent"],
            border_width=2,
            corner_radius=22,
            width=520,
            height=330
        )
        center_card.place(relx=0.5, rely=0.5, anchor="center")
        center_card.grid_propagate(False)
        center_card.grid_columnconfigure(0, weight=1)

        logo_pil = create_nebula_logo_image(128)
        self.welcome_logo_ctk = ctk.CTkImage(light_image=logo_pil, dark_image=logo_pil, size=(88, 88))

        logo_lbl = ctk.CTkLabel(center_card, image=self.welcome_logo_ctk, text="")
        logo_lbl.grid(row=0, column=0, pady=(28, 12))

        self.welcome_title_lbl = ctk.CTkLabel(
            center_card,
            text="Welcome to Nebula Mod Manager",
            font=ctk.CTkFont(size=24, weight="bold"),
            text_color=THEME["text_main"]
        )
        self.welcome_title_lbl.grid(row=1, column=0, padx=24, pady=(0, 6))

        self.welcome_sub_lbl = ctk.CTkLabel(
            center_card,
            text="Fast-scanning Steam libraries & checking for updates...",
            font=ctk.CTkFont(size=13),
            text_color=THEME["text_muted"]
        )
        self.welcome_sub_lbl.grid(row=2, column=0, padx=24, pady=(0, 22))

        self.welcome_progress = ctk.CTkProgressBar(
            center_card,
            mode="determinate",
            progress_color=THEME["accent"],
            fg_color=THEME["bg_root"],
            width=380,
            height=12,
            corner_radius=6
        )
        self.welcome_progress.set(0.0)
        self.welcome_progress.grid(row=3, column=0, padx=24, pady=(0, 10))

        self.welcome_pct_lbl = ctk.CTkLabel(
            center_card,
            text="0%",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=THEME["accent"]
        )
        self.welcome_pct_lbl.grid(row=4, column=0, pady=(0, 16))

    def _start_welcome_boot_sequence(self):
        self._welcome_progress_val = 0.0
        self._welcome_scan_done = False

        threading.Thread(target=self._welcome_scan_worker, daemon=True).start()
        self._animate_welcome_progress()

    def _welcome_scan_worker(self):
        self._scanned_games_buffer = SteamScanner.scan_installed_games()
        self._welcome_scan_done = True

    def _animate_welcome_progress(self):
        if not self._welcome_scan_done:
            if self._welcome_progress_val < 0.85:
                self._welcome_progress_val += 0.08
        else:
            self._welcome_progress_val += 0.18

        clamped = min(1.0, self._welcome_progress_val)
        self.welcome_progress.set(clamped)
        pct = int(clamped * 100)
        self.welcome_pct_lbl.configure(text=f"{pct}%")

        if pct < 50:
            self.welcome_sub_lbl.configure(text="Reading Steam library manifests...")
        elif pct < 100:
            self.welcome_sub_lbl.configure(text="Preparing your mod workspace...")
        else:
            self.welcome_sub_lbl.configure(text="Ready!")

        if clamped < 1.0:
            self.after(16, self._animate_welcome_progress)
        else:
            self._on_games_loaded(self._scanned_games_buffer)
            self.after(60, lambda: self._slide_out_welcome_screen(0.0))

    def _slide_out_welcome_screen(self, offset_y: float):
        if offset_y <= -1.0:
            self.welcome_frame.place_forget()
            self._check_github_updates_async()
            return
        next_y = offset_y - 0.12
        self.welcome_frame.place(relx=0.0, rely=next_y, relwidth=1.0, relheight=1.0)
        self.after(12, lambda: self._slide_out_welcome_screen(next_y))

    # ==========================================
    # BATCHED NON-BLOCKING GAME TAB RENDERING
    # ==========================================
    def _rescan_steam_games_click(self):
        self.status_lbl.configure(text="⏳ Rescanning Steam libraries...")
        threading.Thread(target=self._rescan_worker, daemon=True).start()

    def _rescan_worker(self):
        detected_games = SteamScanner.scan_installed_games()
        self.after(0, lambda: self._on_games_loaded(detected_games))

    def _on_games_loaded(self, detected_games: list[dict]):
        self.games = detected_games
        total_games = len(self.games)
        self.found_games_badge.configure(
            text=f"{total_games} Game{'s' if total_games != 1 else ''}"
        )

        for widget in self.games_scroll.winfo_children():
            widget.destroy()
        self.game_tab_widgets.clear()

        if self.games and not self.selected_game:
            self._select_game(self.games[0])

        self._render_game_cards_batch(0, batch_size=12)

    def _render_game_cards_batch(self, start_idx: int, batch_size: int = 12):
        end_idx = min(start_idx + batch_size, len(self.games))
        for idx in range(start_idx, end_idx):
            game = self.games[idx]
            self._create_single_game_card(game)

        if end_idx < len(self.games):
            self.after(8, lambda: self._render_game_cards_batch(end_idx, batch_size))

    def _create_single_game_card(self, game: dict):
        appid = str(game["appid"])
        is_selected = self.selected_game and str(self.selected_game["appid"]) == appid
        card = ctk.CTkFrame(
            self.games_scroll,
            fg_color=THEME["accent_hover"] if is_selected else THEME["bg_card"],
            corner_radius=10,
            height=68
        )
        card.pack(fill="x", pady=4, padx=4, anchor="n")
        card.grid_columnconfigure(1, weight=1)

        initial_thumb = self.image_cache[appid][0] if appid in self.image_cache else self.placeholder_thumb_ctk
        img_lbl = ctk.CTkLabel(card, text="", image=initial_thumb, width=92, height=44)
        img_lbl.grid(row=0, column=0, rowspan=2, padx=8, pady=8)

        name_lbl = ctk.CTkLabel(
            card,
            text=game["name"],
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=THEME["text_main"],
            anchor="w",
            justify="left",
            wraplength=170
        )
        name_lbl.grid(row=0, column=1, sticky="ew", padx=(2, 8), pady=(8, 0))

        badge_text, badge_color = self._get_badge_text_and_color(game)
        badge_lbl = ctk.CTkLabel(
            card,
            text=badge_text,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=badge_color,
            anchor="w"
        )
        badge_lbl.grid(row=1, column=1, sticky="w", padx=(2, 8), pady=(0, 6))

        for w in (card, img_lbl, name_lbl, badge_lbl):
            w.bind("<Button-1>", lambda e, g=game: self._select_game(g))

        self.game_tab_widgets[appid] = {
            "card": card,
            "img": img_lbl,
            "badge": badge_lbl,
            "game_ref": game,
            "name_lower": game["name"].lower()
        }

        if appid not in self.image_cache:
            self.cover_executor.submit(self._fetch_game_cover_async, appid, img_lbl)

    def _get_badge_text_and_color(self, game: dict) -> tuple[str, str]:
        appid = str(game["appid"])
        loaded_count = self.mod_controller.get_enabled_mod_count(appid)
        total_mods = len(self.mod_controller.get_mods_for_game(appid))
        has_loader = ModLoaderAutoInstaller.is_loader_installed_for_game(game)

        parts = [f"🧩 {loaded_count} Loaded"]
        if total_mods > loaded_count:
            parts[0] = f"🧩 {loaded_count}/{total_mods} Mods"
        if has_loader:
            parts.append("⚡ Loader")

        badge_text = "  •  ".join(parts)
        if loaded_count > 0:
            color = THEME["text_success"]
        elif has_loader or total_mods > 0:
            color = THEME["text_cyan"]
        else:
            color = THEME["text_muted"]
        return badge_text, color

    def _on_sidebar_filter_changed(self, value: str):
        self.sidebar_filter_mode = value
        self._filter_game_tabs()

    def _on_search_key_released(self, event=None):
        if self._search_debounce_job is not None:
            try:
                self.after_cancel(self._search_debounce_job)
            except Exception:
                pass
        self._search_debounce_job = self.after(60, self._filter_game_tabs)

    def _filter_game_tabs(self):
        self._search_debounce_job = None
        query = self.search_entry.get().strip().lower()
        only_modded = (self.sidebar_filter_mode == "Modded / Loaders")
        matched_count = 0

        for game in self.games:
            item = self.game_tab_widgets.get(str(game["appid"]))
            if item:
                item["card"].pack_forget()

        for game in self.games:
            appid = str(game["appid"])
            item = self.game_tab_widgets.get(appid)
            if not item:
                continue

            if query and query not in item["name_lower"]:
                continue

            if only_modded:
                has_mods = len(self.mod_controller.get_mods_for_game(appid)) > 0
                has_loader = ModLoaderAutoInstaller.is_loader_installed_for_game(game)
                if not (has_mods or has_loader):
                    continue

            item["card"].pack(fill="x", pady=4, padx=4, anchor="n")
            matched_count += 1

        if query or only_modded:
            self.found_games_badge.configure(text=f"{matched_count} / {len(self.games)} Games")
        else:
            self.found_games_badge.configure(text=f"{len(self.games)} Games")

        try:
            self.games_scroll._parent_canvas.yview_moveto(0.0)
        except Exception:
            pass

    def _update_sidebar_mod_badge(self, appid: str):
        appid = str(appid)
        if appid in self.game_tab_widgets:
            item = self.game_tab_widgets[appid]
            badge = item["badge"]
            if badge.winfo_exists():
                b_text, b_col = self._get_badge_text_and_color(item["game_ref"])
                badge.configure(text=b_text, text_color=b_col)
        if self.sidebar_filter_mode == "Modded / Loaders":
            self._filter_game_tabs()

    def _fetch_game_cover_async(self, appid: str, target_label: ctk.CTkLabel):
        cache_img_path = CACHE_DIR / f"{appid}_header.jpg"
        if not cache_img_path.exists():
            candidate_urls = [
                f"https://shared.akamai.steamstatic.com/store_item_assets/steam/apps/{appid}/header.jpg",
                f"https://cdn.akamai.steamstatic.com/steam/apps/{appid}/header.jpg"
            ]
            downloaded_bytes = None
            for url in candidate_urls:
                try:
                    resp = requests.get(url, timeout=4)
                    if resp.status_code == 200 and resp.content[:2] == b"\xff\xd8":
                        downloaded_bytes = resp.content
                        break
                except Exception:
                    continue

            if not downloaded_bytes:
                try:
                    api_url = f"https://store.steampowered.com/api/appdetails?appids={appid}"
                    api_resp = requests.get(api_url, timeout=4).json()
                    if api_resp and api_resp.get(str(appid), {}).get("success"):
                        header_url = api_resp[str(appid)]["data"].get("header_image")
                        if header_url:
                            img_resp = requests.get(header_url, timeout=4)
                            if img_resp.status_code == 200:
                                downloaded_bytes = img_resp.content
                except Exception:
                    pass

            if downloaded_bytes:
                try:
                    cache_img_path.write_bytes(downloaded_bytes)
                except Exception:
                    return

        if cache_img_path.exists():
            try:
                pil_img = Image.open(cache_img_path)
                thumb_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(92, 43))
                banner_ctk = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=(184, 86))
                self.image_cache[appid] = (thumb_ctk, banner_ctk)
                self.after(0, lambda: self._apply_thumbnail(appid, target_label))
            except Exception:
                pass

    def _apply_thumbnail(self, appid: str, label: ctk.CTkLabel):
        if appid in self.image_cache and label.winfo_exists():
            label.configure(image=self.image_cache[appid][0], text="")
        if self.selected_game and str(self.selected_game["appid"]) == str(appid):
            self.banner_img_lbl.configure(image=self.image_cache[appid][1], text="")

    # ==========================================
    # GAME SELECTION & SMOOTH TRANSITION ANIMATION
    # ==========================================
    def _select_game(self, game: dict):
        prev_appid = str(self.selected_game["appid"]) if self.selected_game else None
        self.selected_game = game
        appid = str(game["appid"])

        loaded_count = self.mod_controller.get_enabled_mod_count(appid)
        total_count = len(self.mod_controller.get_mods_for_game(appid))
        self.status_lbl.configure(
            text=f"Viewing {game['name']}  •  {loaded_count} active mod(s), {total_count} total installed."
        )

        for gid, widgets in self.game_tab_widgets.items():
            card = widgets["card"]
            if card.winfo_exists() and gid != appid and gid != prev_appid:
                card.configure(fg_color=THEME["bg_card"])

        self._animate_game_switch_transition(prev_appid, appid, step=0)

        self.game_title_lbl.configure(text=game["name"])
        self.game_path_lbl.configure(text=f"Steam Folder: {game['install_dir']}")
        self.play_game_btn.configure(state="normal")
        self.mod_sites_btn.configure(text="🌐  Mod Sites", state="normal")
        self.open_folder_btn.configure(state="normal")
        self.change_target_btn.configure(state="normal")
        self.browse_btn.configure(state="normal")

        self.current_mod_target_dir = Path(game["install_dir"])
        self.mod_target_lbl.configure(
            text="🌐 Resolving default mod installation directory..."
        )
        self._show_loader_notice(None, None, None, False)

        if appid in self.image_cache:
            self.banner_img_lbl.configure(image=self.image_cache[appid][1], text="")
        else:
            self.banner_img_lbl.configure(image=self.placeholder_banner_ctk, text="")

        if game.get("has_anticheat_or_mp") is True:
            self._show_anticheat_warning(True)
        else:
            self._show_anticheat_warning(False)

        threading.Thread(
            target=self._resolve_game_online_worker,
            args=(game,),
            daemon=True
        ).start()

        self._refresh_installed_mods_ui()

    def _animate_game_switch_transition(self, prev_appid: str | None, new_appid: str, step: int):
        if self._header_anim_job is not None:
            try:
                self.after_cancel(self._header_anim_job)
            except Exception:
                pass

        total_steps = 8
        t = step / total_steps

        if new_appid in self.game_tab_widgets:
            new_card = self.game_tab_widgets[new_appid]["card"]
            if new_card.winfo_exists():
                new_card.configure(
                    fg_color=interpolate_hex_color(THEME["bg_card"], THEME["accent_hover"], t)
                )

        if prev_appid and prev_appid != new_appid and prev_appid in self.game_tab_widgets:
            old_card = self.game_tab_widgets[prev_appid]["card"]
            if old_card.winfo_exists():
                old_card.configure(
                    fg_color=interpolate_hex_color(THEME["accent_hover"], THEME["bg_card"], t)
                )

        header_bg = interpolate_hex_color("#2e2252", THEME["bg_card"], t)
        border_col = interpolate_hex_color("#c084fc", THEME["accent"], t)
        self.header_frame.configure(fg_color=header_bg, border_color=border_col)

        if step < total_steps:
            self._header_anim_job = self.after(
                18,
                lambda: self._animate_game_switch_transition(prev_appid, new_appid, step + 1)
            )
        else:
            self._header_anim_job = None

    def _open_mod_sites_dialog(self):
        if not self.selected_game:
            return
        ModSitesDialog(self, self.selected_game)

    def _open_rottr_loader_gui_click(self):
        """Pre-configures Rise of the Tomb Raider's path & registry before opening RottrModManager.exe."""
        if not self.selected_game:
            return
        game_root = Path(self.selected_game["install_dir"])
        appid = str(self.selected_game["appid"])

        # Ensure Registry + Steam Junction are set so RottrModManager never shows the path error!
        ModLoaderAutoInstaller.configure_rottr_game_path(game_root, appid)

        exe = ModLoaderAutoInstaller.get_rottr_manager_exe(game_root)
        if exe and exe.exists():
            try:
                subprocess.Popen([str(exe)], cwd=str(exe.parent))
                self.status_lbl.configure(
                    text=f"🛠️ Opened {exe.name} (Game path pre-configured automatically)."
                )
            except Exception as e:
                messagebox.showerror("Error", f"Could not launch {exe.name}:\n{str(e)}")

    def _launch_selected_game(self):
        if not self.selected_game:
            return
        appid = str(self.selected_game["appid"])
        game_name = self.selected_game["name"]
        try:
            self.status_lbl.configure(text=f"🚀 Launching {game_name} via Steam...")
            os.startfile(f"steam://rungameid/{appid}")
        except Exception as e:
            messagebox.showerror("Launch Error", f"Could not launch {game_name}:\n{str(e)}")

    def _resolve_game_online_worker(self, game: dict):
        metadata = SmartModRouter.resolve_full_game_metadata_online(game)
        is_mp = SteamScanner.check_anticheat_or_multiplayer_lazy(game)
        verified_sites = ModSiteVerifier.verify_sites_for_game(game)
        game["verified_mod_sites"] = verified_sites
        self.after(0, lambda: self._apply_online_game_metadata(game, metadata, is_mp, verified_sites))

    def _apply_online_game_metadata(
        self,
        game: dict,
        metadata: dict,
        is_mp: bool,
        verified_sites: list[dict]
    ):
        self._update_sidebar_mod_badge(game["appid"])
        if not self.selected_game or str(self.selected_game["appid"]) != str(game["appid"]):
            return

        self.current_mod_target_dir = metadata["mod_path"]
        self.mod_target_lbl.configure(
            text=f"🎯 Default Mod Path: {metadata['mod_path']}   [{metadata['reason']}]"
        )
        self.mod_sites_btn.configure(text=f"🌐  Mod Sites ({len(verified_sites)})")
        self._show_anticheat_warning(is_mp)
        self._show_loader_notice(
            metadata.get("loader_notice"),
            metadata.get("loader_id"),
            metadata.get("loader_name"),
            metadata.get("loader_installed", False),
            metadata.get("loader_search_query")
        )

    def _show_anticheat_warning(self, show: bool):
        if show:
            self.warning_banner.grid(row=1, column=0, sticky="ew", pady=(0, 8))
        else:
            self.warning_banner.grid_forget()

    def _show_loader_notice(
        self,
        notice_text: str | None,
        loader_id: str | None,
        loader_name: str | None,
        is_installed: bool,
        search_query: str | None = None
    ):
        self.current_loader_id = loader_id
        self.current_loader_name = loader_name
        self.current_loader_installed = is_installed
        self.current_loader_search_query = search_query

        if notice_text:
            self.loader_lbl.configure(text=notice_text)
            if is_installed:
                if loader_id == "RottrModManager":
                    self.open_loader_gui_btn.pack(side="left", padx=(0, 6))
                else:
                    self.open_loader_gui_btn.pack_forget()
                self.get_loader_btn.configure(
                    text="🔄 Reinstall Loader",
                    fg_color=THEME["success_bg"],
                    hover_color=THEME["success_hover"],
                    state="normal"
                )
                self.delete_loader_btn.pack(side="left")
                self.delete_loader_btn.configure(state="normal")
            else:
                self.open_loader_gui_btn.pack_forget()
                self.get_loader_btn.configure(
                    text="⚡ Auto-Install Loader",
                    fg_color="#0284c7",
                    hover_color="#0369a1",
                    state="normal"
                )
                self.delete_loader_btn.pack_forget()
            self.loader_banner.grid(row=2, column=0, sticky="ew", pady=(0, 8))
        else:
            self.loader_banner.grid_forget()

    def _auto_install_mod_loader_click(self, post_install_callback=None):
        if not self.selected_game:
            return

        game = self.selected_game
        loader_id = self.current_loader_id
        loader_name = self.current_loader_name

        self.get_loader_btn.configure(text="⏳ Installing...", state="disabled")
        self.delete_loader_btn.configure(state="disabled")
        self.status_lbl.configure(text=f"Starting automatic installation of {loader_name}...")

        def update_progress(msg: str):
            self.after(0, lambda: self.status_lbl.configure(text=msg))

        def worker():
            success, result_msg = ModLoaderAutoInstaller.auto_install_loader(
                game=game,
                loader_id=loader_id,
                loader_name=loader_name,
                progress_callback=update_progress
            )
            self.after(
                0,
                lambda: self._on_loader_auto_installed(game, success, result_msg, post_install_callback)
            )

        threading.Thread(target=worker, daemon=True).start()

    def _on_loader_auto_installed(
        self,
        game: dict,
        success: bool,
        result_msg: str,
        post_install_callback=None
    ):
        if self.selected_game and str(self.selected_game["appid"]) == str(game["appid"]):
            self.status_lbl.configure(text=result_msg.split("\n")[0])

        if success:
            self.current_loader_installed = True
            self._update_sidebar_mod_badge(game["appid"])
            threading.Thread(
                target=self._resolve_game_online_worker,
                args=(game,),
                daemon=True
            ).start()
            if post_install_callback:
                post_install_callback()
            else:
                messagebox.showinfo("Mod Loader Installed", result_msg)
        else:
            self.get_loader_btn.configure(text="⚡ Auto-Install Loader", state="normal")
            if self.current_loader_search_query:
                if messagebox.askyesno(
                    "Manual Download Required",
                    f"{result_msg}\n\nWould you like to open the download page in your browser?"
                ):
                    url = f"https://www.google.com/search?q={quote_plus(self.current_loader_search_query)}"
                    webbrowser.open(url)
            else:
                messagebox.showerror("Mod Loader Installation Failed", result_msg)

    def _delete_mod_loader_click(self):
        if not self.selected_game:
            return

        game = self.selected_game
        loader_display = (self.current_loader_name or "Mod Loader").split("(")[0].strip()
        if not messagebox.askyesno(
            "Delete Mod Loader",
            f"Are you sure you want to delete {loader_display} from {game['name']}?\n\n"
            "(Your downloaded mods will not be deleted.)"
        ):
            return

        success, msg = ModLoaderAutoInstaller.uninstall_loader(
            game=game,
            loader_id=self.current_loader_id,
            loader_name=self.current_loader_name
        )
        self.status_lbl.configure(text=msg)
        if success:
            self.current_loader_installed = False
            self._update_sidebar_mod_badge(game["appid"])
            threading.Thread(
                target=self._resolve_game_online_worker,
                args=(game,),
                daemon=True
            ).start()
            messagebox.showinfo("Mod Loader Deleted", msg)
        else:
            messagebox.showwarning("Delete Mod Loader", msg)

    def _change_mod_target_dialog(self):
        if not self.selected_game:
            return
        chosen = filedialog.askdirectory(
            title=f"Select Mod Installation Folder for {self.selected_game['name']}",
            initialdir=str(self.current_mod_target_dir or self.selected_game["install_dir"])
        )
        if chosen:
            chosen_path = Path(chosen)
            SmartModRouter.save_custom_path(str(self.selected_game["appid"]), str(chosen_path))
            self.current_mod_target_dir = chosen_path
            self.mod_target_lbl.configure(
                text=f"🎯 Default Mod Path: {chosen_path}   [Custom User Path]"
            )

    # ==========================================
    # PRE-INSTALL ARCHIVE INSPECTION & SMART ROUTING
    # ==========================================
    def _on_file_dropped(self, event):
        if not self.selected_game:
            messagebox.showwarning("No Game Selected", "Please select a Steam game first.")
            return
        raw_paths = self.tk.splitlist(event.data)
        for path in raw_paths:
            self._install_archive(path)

    def _browse_archive_dialog(self):
        if not self.selected_game:
            return
        file_path = filedialog.askopenfilename(
            title="Select Mod Archive",
            filetypes=[("Mod Archives", "*.zip *.rar *.7z"), ("All Files", "*.*")]
        )
        if file_path:
            self._install_archive(file_path)

    def _install_archive(self, archive_path: str):
        if not self.selected_game:
            return

        target_game = self.selected_game
        self.status_lbl.configure(text="🔍 Inspecting mod archive & routing path...")
        self.update_idletasks()

        default_target = self.current_mod_target_dir or Path(target_game["install_dir"])
        ok, err_msg, staging_dir, inspection = self.mod_controller.prepare_and_inspect_archive(
            game=target_game,
            archive_path=archive_path,
            default_mod_target_dir=default_target,
            loader_id=self.current_loader_id,
            loader_name=self.current_loader_name
        )

        if not ok or not staging_dir or not inspection:
            self.status_lbl.configure(text=err_msg)
            messagebox.showerror("Mod Archive Error", err_msg)
            return

        if inspection.get("is_loader_package"):
            detected_id = inspection["detected_loader_id"]
            l_ok, l_msg = ModLoaderAutoInstaller.install_loader_from_local_staging(
                target_game, staging_dir, detected_id
            )
            shutil.rmtree(staging_dir, ignore_errors=True)
            self._update_sidebar_mod_badge(target_game["appid"])
            if self.selected_game and str(self.selected_game["appid"]) == str(target_game["appid"]):
                self.status_lbl.configure(text=l_msg)
            threading.Thread(
                target=self._resolve_game_online_worker,
                args=(target_game,),
                daemon=True
            ).start()
            messagebox.showinfo("Mod Loader Installed", l_msg)
            return

        if inspection.get("requires_loader") and not self.current_loader_installed:
            dialog = ModLoaderRequiredDialog(
                parent=self,
                mod_name=format_simple_mod_name(Path(archive_path).stem, staging_dir),
                mod_type=inspection.get("mod_type_label", "Mod Loader Mod"),
                loader_name=inspection.get("loader_name") or self.current_loader_name or "Game Mod Loader",
                target_dir=inspection["target_dir"]
            )
            self.wait_window(dialog)

            if dialog.result == "cancel":
                shutil.rmtree(staging_dir, ignore_errors=True)
                self.status_lbl.configure(text="Mod installation cancelled.")
                return
            elif dialog.result == "download_loader_and_install":
                self.current_loader_id = inspection.get("loader_id") or self.current_loader_id
                self.current_loader_name = inspection.get("loader_name") or self.current_loader_name
                self._auto_install_mod_loader_click(
                    post_install_callback=lambda: self._complete_staged_mod_install(
                        target_game, archive_path, staging_dir, inspection
                    )
                )
                return

        self._complete_staged_mod_install(target_game, archive_path, staging_dir, inspection)

    def _complete_staged_mod_install(
        self,
        target_game: dict,
        archive_path: str,
        staging_dir: Path,
        inspection: dict
    ):
        success, msg = self.mod_controller.finalize_mod_installation(
            game=target_game,
            archive_path=archive_path,
            staging_dir=staging_dir,
            inspection=inspection
        )
        self._update_sidebar_mod_badge(target_game["appid"])

        if self.selected_game and str(self.selected_game["appid"]) == str(target_game["appid"]):
            self.status_lbl.configure(text=msg)
            self._refresh_installed_mods_ui()

        if not success:
            messagebox.showerror("Mod Installation Failed", msg)

    def _rename_mod_click(self, mod: dict):
        if not self.selected_game:
            return
        current_name = format_simple_mod_name(mod.get("name", ""))
        dialog = ctk.CTkInputDialog(
            text=f"Enter a new display name for '{current_name}':",
            title="Rename Mod"
        )
        new_name = dialog.get_input()
        if new_name and new_name.strip():
            self.mod_controller.rename_mod(
                str(self.selected_game["appid"]),
                mod["id"],
                new_name.strip()
            )
            self.status_lbl.configure(text=f"✏️ Renamed mod to '{new_name.strip()}'.")
            self._refresh_installed_mods_ui()

    def _toggle_mod_click(self, mod_id: str):
        if not self.selected_game:
            return
        success, msg = self.mod_controller.toggle_mod_state(self.selected_game, mod_id)
        self.status_lbl.configure(text=msg)
        if not success:
            messagebox.showerror("Toggle Failed", msg)
        self._update_sidebar_mod_badge(self.selected_game["appid"])
        self._refresh_installed_mods_ui()

    def _bulk_toggle_mods_click(self, enable: bool):
        if not self.selected_game:
            return
        success, msg = self.mod_controller.set_all_mods_state(self.selected_game, enable)
        self.status_lbl.configure(text=msg)
        if not success:
            messagebox.showwarning("Bulk Mod Action", msg)
        self._update_sidebar_mod_badge(self.selected_game["appid"])
        self._refresh_installed_mods_ui()

    def _uninstall_mod_click(self, mod_id: str):
        if not self.selected_game:
            return
        success, msg = self.mod_controller.uninstall_mod(self.selected_game, mod_id)
        self.status_lbl.configure(text=msg)
        self._update_sidebar_mod_badge(self.selected_game["appid"])
        self._refresh_installed_mods_ui()

    def _refresh_installed_mods_ui(self):
        for widget in self.mods_list_frame.winfo_children():
            widget.destroy()

        if not self.selected_game:
            self.enable_all_btn.configure(state="disabled")
            self.disable_all_btn.configure(state="disabled")
            return

        appid = str(self.selected_game["appid"])
        all_mods = self.mod_controller.get_mods_for_game(appid)
        loaded_count = self.mod_controller.get_enabled_mod_count(appid)

        self.mods_header_lbl.configure(
            text=f"Installed Mods  •  {loaded_count} Loaded / {len(all_mods)} Total"
        )

        if not all_mods:
            self.enable_all_btn.configure(state="disabled")
            self.disable_all_btn.configure(state="disabled")
            empty_lbl = ctk.CTkLabel(
                self.mods_list_frame,
                text="No mods installed for this game yet. Drag and drop a .zip, .rar, or .7z file above!",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"]
            )
            empty_lbl.grid(row=0, column=0, pady=36)
            return

        self.enable_all_btn.configure(state="normal" if loaded_count < len(all_mods) else "disabled")
        self.disable_all_btn.configure(state="normal" if loaded_count > 0 else "disabled")

        mod_query = self.installed_mods_search_entry.get().strip().lower()
        filtered_mods = [
            m for m in all_mods
            if not mod_query
            or mod_query in format_simple_mod_name(m.get("name", "")).lower()
            or mod_query in m.get("name", "").lower()
        ]

        if not filtered_mods:
            no_match_lbl = ctk.CTkLabel(
                self.mods_list_frame,
                text=f"No installed mods match '{mod_query}'.",
                font=ctk.CTkFont(size=13),
                text_color=THEME["text_muted"]
            )
            no_match_lbl.grid(row=0, column=0, pady=36)
            return

        for idx, mod in enumerate(filtered_mods):
            is_enabled = mod.get("enabled", True)
            row = ctk.CTkFrame(
                self.mods_list_frame,
                fg_color=THEME["bg_sidebar"],
                corner_radius=8
            )
            row.grid(row=idx, column=0, sticky="ew", pady=5, padx=4)
            row.grid_columnconfigure(0, weight=1)

            # Show clean, simple mod name
            display_name = (
                mod["name"]
                if mod.get("custom_named")
                else format_simple_mod_name(mod.get("name", ""))
            )
            status_dot = "🟢" if is_enabled else "⏸️"
            state_suffix = "" if is_enabled else "  (Disabled)"

            ctk.CTkLabel(
                row,
                text=f"{status_dot}   {display_name}{state_suffix}",
                font=ctk.CTkFont(size=14, weight="bold"),
                text_color=THEME["text_main"] if is_enabled else THEME["text_muted"],
                anchor="w"
            ).grid(row=0, column=0, padx=14, pady=12, sticky="ew")

            rename_btn = ctk.CTkButton(
                row,
                text="✏️ Rename",
                fg_color=THEME["bg_card"],
                hover_color=THEME["bg_card_hover"],
                width=90,
                height=30,
                command=lambda m=mod: self._rename_mod_click(m)
            )
            rename_btn.grid(row=0, column=1, padx=(6, 6), pady=10)

            toggle_btn = ctk.CTkButton(
                row,
                text="Enabled (Click to Disable)" if is_enabled else "Disabled (Click to Enable)",
                fg_color=THEME["success_bg"] if is_enabled else THEME["disabled_bg"],
                hover_color=THEME["success_hover"] if is_enabled else THEME["disabled_hover"],
                width=175,
                height=30,
                command=lambda m_id=mod["id"]: self._toggle_mod_click(m_id)
            )
            toggle_btn.grid(row=0, column=2, padx=(0, 6), pady=10)

            remove_btn = ctk.CTkButton(
                row,
                text="Remove Mod",
                fg_color=THEME["danger"],
                hover_color=THEME["danger_hover"],
                width=110,
                height=30,
                command=lambda m_id=mod["id"]: self._uninstall_mod_click(m_id)
            )
            remove_btn.grid(row=0, column=3, padx=(0, 12), pady=10)

    def _open_mod_folder(self):
        target = self.current_mod_target_dir or (
            Path(self.selected_game["install_dir"]) if self.selected_game else None
        )
        if target and target.exists():
            os.startfile(str(target))


if __name__ == "__main__":
    app = NebulaModManagerApp()
    app.mainloop()
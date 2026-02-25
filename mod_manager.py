"""
Ashes of the Singularity II — Mod Manager
"""

import json
import re
import shutil
import sys
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path

GAME_CORE  = None  # Resolved at startup via resolve_game_core()
# When frozen by PyInstaller sys.executable is the .exe path; otherwise use __file__
APP_DIR    = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
MODS_DIR   = APP_DIR / "mods"
BACKUP_DIR = APP_DIR / "backups"
STATE_FILE = APP_DIR / "active_mods.json"
CONFIG_FILE = APP_DIR / "config.json"

BACKUP_DIR.mkdir(exist_ok=True)

# ── Colours ────────────────────────────────────────────────────────────────────
BG        = "#1e1e2e"
BG2       = "#181825"
BG3       = "#313244"
FG        = "#cdd6f4"
FG_DIM    = "#6c7086"
GREEN     = "#a6e3a1"
RED       = "#f38ba8"
BLUE      = "#89b4fa"
CYAN      = "#89dceb"
YELLOW    = "#f9e2af"


# ── Game-folder resolution ─────────────────────────────────────────────────────

def load_config() -> dict:
    if CONFIG_FILE.exists():
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    return {}


def save_config(cfg: dict):
    CONFIG_FILE.write_text(json.dumps(cfg, indent=2), encoding="utf-8")


def find_game_core() -> Path | None:
    """Search common Steam library locations for the GameCore folder."""
    game_names = [
        "Ashes of the Singularity II Demo",
        "Ashes of the Singularity II",
        "Ashes of the Singularity - Escalation",
        "Ashes of the Singularity Escalation",
    ]
    drives = "CDEFGHIJ"
    steam_roots = (
        [Path(f"{d}:/SteamLibrary") for d in drives]
        + [Path(f"{d}:/Steam") for d in drives]
        + [
            Path("C:/Program Files (x86)/Steam"),
            Path("C:/Program Files/Steam"),
        ]
    )
    for root in steam_roots:
        for game in game_names:
            candidate = root / "steamapps" / "common" / game / "Assets" / "GameCore"
            if candidate.exists():
                return candidate
    return None


def resolve_game_core() -> Path:
    """Return a valid GAME_CORE path, saving/loading the choice to config.json."""
    global GAME_CORE

    cfg = load_config()

    # 1. Use previously saved path if it still exists
    saved = cfg.get("game_core")
    if saved:
        p = Path(saved)
        if p.exists():
            GAME_CORE = p
            return GAME_CORE

    # 2. Auto-detect across common Steam locations
    found = find_game_core()
    if found:
        GAME_CORE = found
        cfg["game_core"] = str(found)
        save_config(cfg)
        return GAME_CORE

    # 3. Ask the user to locate it manually
    messagebox.showinfo(
        "Game Folder Not Found",
        "Could not find the AOTS GameCore folder automatically.\n\n"
        "Please select the GameCore folder manually.\n"
        "It is usually located at:\n"
        "  <Steam>\\steamapps\\common\\Ashes of the Singularity II\\Assets\\GameCore",
    )
    chosen = filedialog.askdirectory(title="Select GameCore Folder")
    if not chosen:
        messagebox.showerror("No Folder Selected", "A GameCore folder must be selected to continue.")
        sys.exit(1)

    GAME_CORE = Path(chosen)
    cfg["game_core"] = str(GAME_CORE)
    save_config(cfg)
    return GAME_CORE


# ── Backend ────────────────────────────────────────────────────────────────────

def load_state() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {}


def save_state(state: dict):
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


def scan_mods() -> list[dict]:
    mods = []
    if MODS_DIR.exists():
        for d in sorted(MODS_DIR.iterdir()):
            if d.is_dir():
                jf = d / "mod.json"
                if jf.exists():
                    data = json.loads(jf.read_text(encoding="utf-8"))
                    mods.append({"data": data, "path": d})
    return mods


def backup_file(filename: str) -> bool:
    src = GAME_CORE / filename
    dst = BACKUP_DIR / filename
    if not dst.exists() and src.exists():
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
    return dst.exists()


def restore_file(filename: str) -> bool:
    src = BACKUP_DIR / filename
    dst = GAME_CORE / filename
    if src.exists():
        shutil.copy2(src, dst)
        return True
    return False


def apply_patch(patch: dict, mod_path: Path | None = None) -> str | None:
    filename = patch["file"]
    filepath = GAME_CORE / filename
    if not filepath.exists():
        return f"Game file not found: {filename}"
    if not backup_file(filename):
        return f"Could not create backup for: {filename}"

    match patch["type"]:
        case "copy":
            source = patch.get("source", filename)
            src = mod_path / source if mod_path else Path(source)
            if not src.exists():
                return f"Mod source file not found: {src}"
            shutil.copy2(src, filepath)
        case "regex":
            content = filepath.read_text(encoding="utf-8")
            content = re.sub(patch["pattern"], patch["replacement"], content)
            filepath.write_text(content, encoding="utf-8")
        case "replace":
            content = filepath.read_text(encoding="utf-8")
            content = content.replace(patch["old"], patch["new"])
            filepath.write_text(content, encoding="utf-8")
        case "multiply":
            content = filepath.read_text(encoding="utf-8")
            factor = float(patch["factor"])
            grp = int(patch.get("group", 2))
            def mul_replace(m, _factor=factor, _grp=grp):
                num_str = m.group(_grp)
                val = float(num_str)
                new_val = val * _factor
                new_str = f"{new_val:.1f}" if "." in num_str else str(int(round(new_val)))
                full = m.group(0)
                s = m.start(_grp) - m.start(0)
                e = m.end(_grp) - m.start(0)
                return full[:s] + new_str + full[e:]
            content = re.sub(patch["pattern"], mul_replace, content)
            filepath.write_text(content, encoding="utf-8")
        case _:
            return f"Unknown patch type '{patch['type']}' for {filename}"

    return None


def activate_mod(mod: dict, state: dict) -> list[str]:
    mod_path = Path(mod["path"])
    errors = [e for p in mod["data"].get("patches", []) if (e := apply_patch(p, mod_path))]
    if not errors:
        state[mod["data"]["id"]] = True
        save_state(state)
    return errors


def deactivate_mod(mod: dict, state: dict) -> list[str]:
    errors = [
        f"No backup found for: {p['file']}"
        for p in mod["data"].get("patches", [])
        if not restore_file(p["file"])
    ]
    if not errors:
        state[mod["data"]["id"]] = False
        save_state(state)
    return errors


# ── GUI ────────────────────────────────────────────────────────────────────────

class ModRow(tk.Frame):
    """One row in the mod list — shows status, name, description, and a toggle button."""

    def __init__(self, parent, mod: dict, active: bool, on_toggle, **kw):
        super().__init__(parent, bg=BG3, **kw)
        self.mod       = mod
        self.active    = active
        self.on_toggle = on_toggle

        self._build()

    def _build(self):
        # Left colour bar
        bar = tk.Frame(self, bg=GREEN if self.active else FG_DIM, width=5)
        bar.pack(side=tk.LEFT, fill=tk.Y)
        bar.pack_propagate(False)
        self._bar = bar

        # Text area
        text_frame = tk.Frame(self, bg=BG3, padx=10, pady=8)
        text_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        name = self.mod["data"].get("name", self.mod["data"]["id"])
        desc = self.mod["data"].get("description", "")
        ver  = self.mod["data"].get("version", "")

        name_line = tk.Frame(text_frame, bg=BG3)
        name_line.pack(anchor=tk.W)

        tk.Label(
            name_line, text=name,
            font=("Segoe UI", 10, "bold"),
            fg=GREEN if self.active else FG, bg=BG3,
        ).pack(side=tk.LEFT)

        if ver:
            tk.Label(
                name_line, text=f"  v{ver}",
                font=("Segoe UI", 8), fg=FG_DIM, bg=BG3,
            ).pack(side=tk.LEFT)

        tk.Label(
            text_frame, text=desc,
            font=("Segoe UI", 9), fg=FG_DIM, bg=BG3,
            wraplength=480, justify=tk.LEFT, anchor=tk.W,
        ).pack(anchor=tk.W)

        # Toggle button
        btn_frame = tk.Frame(self, bg=BG3, padx=10)
        btn_frame.pack(side=tk.RIGHT, fill=tk.Y)

        self._btn = tk.Button(
            btn_frame,
            text="Disable" if self.active else "Enable",
            command=lambda: self.on_toggle(self),
            bg=RED if self.active else GREEN,
            fg=BG2,
            font=("Segoe UI", 9, "bold"),
            relief=tk.FLAT,
            padx=16, pady=6,
            cursor="hand2",
        )
        self._btn.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        btn_frame.config(width=90)
        btn_frame.pack_propagate(False)

    def set_active(self, active: bool):
        self.active = active
        color = GREEN if active else FG_DIM
        self._bar.config(bg=color)

        name_label = self.winfo_children()[1].winfo_children()[0].winfo_children()[0]
        name_label.config(fg=GREEN if active else FG)

        self._btn.config(
            text="Disable" if active else "Enable",
            bg=RED if active else GREEN,
        )


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("AOTS II — Mod Manager")
        self.geometry("740x560")
        self.minsize(580, 400)
        self.configure(bg=BG)

        resolve_game_core()  # Sets the global GAME_CORE; prompts user if needed

        self._state = load_state()
        self._mods  = scan_mods()
        self._rows: list[ModRow] = []

        self._build_ui()

    # ── Layout ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        self._header()
        self._mod_list()
        self._footer()

    def _header(self):
        pnl = tk.Frame(self, bg=BG2, pady=12)
        pnl.pack(fill=tk.X)

        tk.Label(
            pnl, text="Ashes of the Singularity II  —  Mod Manager",
            font=("Segoe UI", 14, "bold"), fg=FG, bg=BG2,
        ).pack()
        tk.Label(
            pnl, text=str(GAME_CORE),
            font=("Segoe UI", 8), fg=FG_DIM, bg=BG2,
        ).pack()

    def _mod_list(self):
        # Section header row
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill=tk.X, padx=16, pady=(10, 6))

        tk.Label(
            hdr, text="Installed Mods",
            font=("Segoe UI", 10, "bold"), fg=BLUE, bg=BG,
        ).pack(side=tk.LEFT)

        tk.Button(
            hdr, text="⟳  Refresh",
            command=self._refresh,
            bg=BG3, fg=CYAN,
            font=("Segoe UI", 9), relief=tk.FLAT,
            padx=10, pady=3, cursor="hand2",
        ).pack(side=tk.RIGHT)

        # Scrollable canvas for the mod rows
        container = tk.Frame(self, bg=BG, padx=16)
        container.pack(fill=tk.BOTH, expand=True)

        self._canvas = tk.Canvas(container, bg=BG, highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient=tk.VERTICAL, command=self._canvas.yview)
        self._canvas.configure(yscrollcommand=scrollbar.set)

        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self._canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._list_frame = tk.Frame(self._canvas, bg=BG)
        self._canvas_window = self._canvas.create_window((0, 0), window=self._list_frame, anchor=tk.NW)

        self._list_frame.bind("<Configure>", self._on_frame_configure)
        self._canvas.bind("<Configure>",     self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)

        self._populate_rows()

    def _footer(self):
        pnl = tk.Frame(self, bg=BG2, padx=14, pady=6)
        pnl.pack(fill=tk.X, side=tk.BOTTOM)

        self._status = tk.StringVar(value="Ready.")
        tk.Label(
            pnl, textvariable=self._status,
            font=("Segoe UI", 8), fg=FG_DIM, bg=BG2, anchor=tk.W,
        ).pack(fill=tk.X)

    # ── Row population ─────────────────────────────────────────────────────────

    def _populate_rows(self):
        for w in self._list_frame.winfo_children():
            w.destroy()
        self._rows.clear()

        if not self._mods:
            tk.Label(
                self._list_frame,
                text="No mods found in the 'mods/' folder.",
                font=("Segoe UI", 10), fg=FG_DIM, bg=BG,
                pady=30,
            ).pack()
            return

        for mod in self._mods:
            mod_id = mod["data"]["id"]
            active = self._state.get(mod_id, False)

            row = ModRow(
                self._list_frame, mod, active,
                on_toggle=self._toggle,
            )
            row.pack(fill=tk.X, pady=(0, 4))
            self._rows.append(row)

    # ── Toggle ─────────────────────────────────────────────────────────────────

    def _toggle(self, row: "ModRow"):
        mod    = row.mod
        mod_id = mod["data"]["id"]
        name   = mod["data"].get("name", mod_id)

        if row.active:
            errors = deactivate_mod(mod, self._state)
            if errors:
                messagebox.showerror("Deactivation Error", "\n".join(errors))
                self._status.set(f"Failed to deactivate '{name}'.")
                return
            row.set_active(False)
            self._status.set(f"'{name}' disabled. Original files restored.")
        else:
            errors = activate_mod(mod, self._state)
            if errors:
                messagebox.showerror("Activation Error", "\n".join(errors))
                self._status.set(f"Failed to activate '{name}'.")
                return
            row.set_active(True)
            self._status.set(f"'{name}' enabled. Game files patched, originals backed up.")

    # ── Canvas / scroll helpers ────────────────────────────────────────────────

    def _on_frame_configure(self, _event):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._canvas_window, width=event.width)

    def _on_mousewheel(self, event):
        self._canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ── Refresh ────────────────────────────────────────────────────────────────

    def _refresh(self):
        self._state = load_state()
        self._mods  = scan_mods()
        self._populate_rows()
        self._status.set("Mod list refreshed.")


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    try:
        app = App()
        app.mainloop()
    except Exception:
        # Write crash log next to the script, then show a dialog
        log_path = APP_DIR / "crash.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")
        try:
            root = tk.Tk()
            root.withdraw()
            messagebox.showerror(
                "Mod Manager — Crash",
                f"An error occurred:\n\n{traceback.format_exc()}\n\nLog saved to:\n{log_path}",
            )
        except Exception:
            pass
        sys.exit(1)

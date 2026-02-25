# AOTS II Mod Manager

A simple mod manager for **Ashes of the Singularity II** (including the Demo). Enables and disables mods with a single click, automatically backs up original game files, and restores them when you disable a mod.

> **Single-player only.** Do not use mods in multiplayer.

---

## Download & Install

1. Download the latest `AOTS-Mod-Manager.zip` from the [Releases](../../releases) page.
2. Extract the zip to any folder on your PC (e.g. `C:\AOTS-Mod-Manager\`).
3. Double-click **`mod_manager.exe`** — no Python or other software required.

---

## First Launch — Game Folder Setup

On first launch the app automatically searches your hard drives for the game's `GameCore` folder across common Steam library locations. One of three things will happen:

| Situation | What happens |
|---|---|
| Game found automatically | App opens normally, path is saved for next time |
| Previously saved path no longer exists | Auto-search runs again |
| Game not found anywhere | A folder picker opens — navigate to your `GameCore` folder manually |

**Where is `GameCore`?**
```
<Steam library>\steamapps\common\Ashes of the Singularity II\Assets\GameCore
```
or for the Demo:
```
<Steam library>\steamapps\common\Ashes of the Singularity II Demo\Assets\GameCore
```

The chosen path is saved to `config.json` next to the exe and is remembered on every future launch.

---

## Using the Mod Manager

| Action | How |
|---|---|
| Enable a mod | Click the green **Enable** button on a mod row |
| Disable a mod | Click the red **Disable** button |
| Refresh the mod list | Click **⟳ Refresh** in the top-right of the list |

- Original game files are backed up automatically the **first time** you enable a mod.
- Disabling a mod **fully restores** those original files.
- The status bar at the bottom confirms each action.

---

## Included Mods

### No Supply Limit
Removes the logistics (supply) cost from all units and buildings so you can build unlimited armies.

*Affects: `Units.zdata`, `Units_UEF.zdata`, `Units_PHC.zdata`, `Units_NEU.zdata`, `Buildings_UEF.zdata`, `Buildings_PHC.zdata`*

---

### No Building Limits
Removes the building slot requirement so you can place any building anywhere without restriction.

*Affects: `Buildings_UEF.zdata`, `Buildings_PHC.zdata`*

---

### Cheaper Research
Reduces tech tier unlock thresholds to 50% of their original values. All 30 tech tiers become accessible much sooner while research still works normally.

*Affects: `Technologies/TechRules.zdata`*

---

### Double Extractor Resources
Doubles the resource output of all extractor-type buildings — ore mines, gas mines, tech labs, logistics depots, refineries, and amplifiers — for both PHC and UEF factions.

*Affects: `Modules_PHC.zdata`, `Modules_UEF.zdata`*

---

### Conflict Warning

**No Supply Limit** and **No Building Limits** both modify `Buildings_UEF.zdata` and `Buildings_PHC.zdata`. Do not enable both at the same time — whichever was activated last will overwrite the other's changes.

---

## Is It Safe?

- Before any mod is applied, the original game file is copied to the `backups\` folder.
- Disabling a mod copies the backup back, fully restoring the original.
- If something goes wrong, use Steam to verify file integrity:
  `Steam → Right-click game → Properties → Installed Files → Verify integrity of game files`
- You can also delete the entire `backups\` folder and verify through Steam to start fresh.

---

## Folder Structure

```
AOTS-Mod-Manager\
  mod_manager.exe         Standalone app (no Python required)
  config.json             Saved game folder path (auto-created)
  active_mods.json        Tracks which mods are on/off (auto-created)
  mods\                   Drop new mod folders here
    no_supply_limit\
      mod.json
    no_building_limits\
      mod.json
      Buildings_UEF.zdata
      Buildings_PHC.zdata
    cheaper_research\
      mod.json
    double_extractor_resources\
      mod.json
  backups\                Original game files (auto-created, do not delete)
```

---

## Creating Your Own Mod

1. Create a new subfolder inside `mods\`:
   ```
   mods\my_mod_name\
   ```
2. Create a `mod.json` file inside it (see template below).
3. Click **⟳ Refresh** in the app — your mod appears in the list.

### mod.json Template

```json
{
  "id":          "unique_mod_id",
  "name":        "Display Name",
  "description": "Short description shown in the app.",
  "version":     "1.0",
  "patches": [
    { "...patch 1..." },
    { "...patch 2..." }
  ]
}
```

| Field | Notes |
|---|---|
| `id` | Must be unique, no spaces — use underscores |
| `name` | Shown in bold in the mod list |
| `description` | Shown in grey below the name |
| `version` | Optional, shown next to the name |
| `patches` | List of changes to apply (see Patch Types below) |

---

### Patch Types

#### `regex` — find and replace with a regular expression
Best for changing numeric values or flags scattered throughout a file.
```json
{
  "file":        "Units_UEF.zdata",
  "type":        "regex",
  "pattern":     "(\\.logCost\\s*=\\s*)[1-9]\\d*",
  "replacement": "\\g<1>0"
}
```
> In JSON every backslash must be doubled (`\` → `\\`).
> Use `\\g<1>` for capture group 1, `\\g<2>` for group 2, etc.

---

#### `replace` — plain-text find and replace
Use when you need an exact match and want to avoid regex.
```json
{
  "file": "Units_UEF.zdata",
  "type": "replace",
  "old":  ".logCost    = 10,",
  "new":  ".logCost    = 0,"
}
```

---

#### `copy` — replace a game file with a pre-edited file
Use when you have a ready-made file inside your mod folder.
```json
{
  "file":   "Buildings_UEF.zdata",
  "type":   "copy",
  "source": "Buildings_UEF.zdata"
}
```
`source` is the filename inside your mod folder; `file` is the target filename in `GameCore`.

---

#### `multiply` — multiply a numeric value matched by a regex group
Use to scale values by a factor (e.g. double resource output).
```json
{
  "file":    "Modules_PHC.zdata",
  "type":    "multiply",
  "pattern": "(\\.someValue\\s*=\\s*)(\\d+\\.\\d+)",
  "factor":  2.0,
  "group":   2
}
```
`group` specifies which regex capture group holds the number to multiply (default: 2).

---

### Game File Reference

Key files inside `GameCore\`:

| File | Contains |
|---|---|
| `Units.zdata` | Shared/neutral unit definitions |
| `Units_UEF.zdata` | UEF faction unit definitions |
| `Units_PHC.zdata` | PHC faction unit definitions |
| `Units_NEU.zdata` | Neutral unit definitions |
| `Buildings_UEF.zdata` | UEF faction building definitions |
| `Buildings_PHC.zdata` | PHC faction building definitions |
| `Modules_UEF.zdata` | UEF resource module definitions |
| `Modules_PHC.zdata` | PHC resource module definitions |
| `Technologies/TechRules.zdata` | Tech tier thresholds |

These are plain-text files — open them with Notepad, Notepad++, or VS Code.

**Common moddable fields:**

| Field | Meaning |
|---|---|
| `.oreCost = 300` | Ore (Durantium) build cost |
| `.gasCost = 150` | Gas (Elerite) build cost |
| `.timeCost = 30` | Build time in seconds |
| `.logCost = 2` | Supply cost (set to 0 for unlimited) |
| `.maxHps = 5000` | Hit points |
| `.Flags = BuildingFlags.ignoresSlotLimit` | Removes building slot restriction |

---

## Troubleshooting

**The app can't find my game folder**
- Click OK on the prompt and navigate to the `GameCore` folder manually.
- Delete `config.json` next to the exe to force the app to search again next launch.

**A mod fails to apply**
- Make sure the game is not running when you enable/disable mods.
- Verify game files through Steam to reset any corrupted files, then try again.

**I accidentally deleted the backups folder**
- Use Steam's "Verify integrity of game files" to redownload the originals, then re-enable your mods.

**The app crashes on launch**
- Check `crash.log` next to the exe for details.

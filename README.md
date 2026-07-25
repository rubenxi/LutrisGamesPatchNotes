# 🎮 Lutris Steam Updates

A desktop app that watches your [Lutris](https://lutris.net/) game library and tells you when a game gets a new update on Steam. It matches each installed game to its Steam store page, pulls patch notes from SteamDB and the official Steam News API, caches box art locally, and shows everything in a dark-themed Tkinter dashboard you can search and browse.

<img width="2427" height="1909" alt="image" src="https://github.com/user-attachments/assets/ee9d5e02-881e-44ec-a0e4-722cef26c865" />

![Python](https://img.shields.io/badge/python-3.9%2B-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Automatic matching** — reads your local Lutris library and matches each game to a Steam store listing by name (with fuzzy-matching to handle naming differences).
- **Update tracking** — pulls patch notes from SteamDB's per-app RSS feed and cross-references Steam's official News API to attach full, cleaned patch-note text and inline screenshots.
- **BBCode cleanup** — Steam's raw patch notes use BBCode-ish markup; it's parsed and converted into clean, readable text (bullets, links, embedded images, stripped tags).
- **Local caching** — game capsule art and inline patch-note screenshots are downloaded once and cached to disk (`images/`), so repeat refreshes make no extra network requests for images already on hand.
- **Persistent database** — all games and updates are stored in a local SQLite database (`updates.db`) so history isn't lost between runs.
- **Review scores** — captures each game's Steam review summary (e.g. "Very Positive", 92%) straight off the search results page.
- **Smart re-checking** — games with no Steam match are retried on a cooldown (default 7 days) instead of being searched every single refresh.
- **Library sync** — games removed from Lutris are automatically cleaned out of the database.
- **Searchable GUI** — a dark, rounded-corner Tkinter UI with a live search box, a sortable update list, and a details panel showing box art, rating, and full patch notes with inline images.
- **New-update alerts** — newly discovered updates are flagged and logged in the app as they come in.
- **One-click browsing** — double-click (or use the built-in action) to open a game's SteamDB page in Brave.

## How it works

1. **`lutris.py`** reads your installed games directly from Lutris's own SQLite database (`pga.db`).
2. **`steam.py`** searches the Steam store for each game, extracts its App ID and review score, then queries:
   - SteamDB's patch-notes RSS feed for the list of updates, and
   - Steam's official `ISteamNews` API for the full text of matching announcements (matched to SteamDB entries by publish timestamp).
3. **`images.py`** downloads and caches Steam capsule art and any inline patch-note screenshots referenced in the notes.
4. **`database.py`** persists games and updates to SQLite (schema in `schema.sql`), including review scores, last-checked timestamps, and cleaned patch-note text.
5. **`gui.py`** renders it all in a Tkinter window — a searchable, sortable table of updates plus a details panel.
6. **`main.py`** wires everything together and drives the background refresh thread that does the actual scanning.

A one-time maintenance script, **`reclean_notes.py`**, is included for re-running the BBCode cleaner against already-stored patch notes (useful after fixing/improving the cleaning logic, since normal refreshes only fetch notes for updates that don't have any yet).

## Requirements

- Python 3.9+
- A Linux install of [Lutris](https://lutris.net/) with at least one game (native or Flatpak install — both data paths are checked)
- [Brave browser](https://brave.com/) installed (used to open SteamDB links; can be replaced by any other browser editing the script)
- The Python packages in `requirements.txt`

> **Note:** `tkinter` is part of the Python standard library but isn't always installed by default on Linux. If it's missing, install it via your distro's package manager, e.g.:
> ```bash
> sudo apt install python3-tk      # Debian/Ubuntu
> sudo dnf install python3-tkinter # Fedora
> ```

## Installation

```bash
git clone <this-repo-url>
cd <repo-folder>
pip install -r requirements.txt
```

## Usage

```bash
python3 main.py
```

On first launch the app will:
1. Create `updates.db` from `schema.sql` if it doesn't already exist.
2. Read your Lutris library.
3. Let you click **Refresh** to scan for Steam matches and new updates.

Click any row in the update list to see full patch notes, box art, and the Steam review score in the details panel.

### Re-cleaning old patch notes

If you update the BBCode-cleaning logic in `steam.py`, existing stored notes won't be touched by a normal refresh (only updates without saved notes get (re)fetched). Run the maintenance script once to refresh everything:

```bash
python3 reclean_notes.py
```

## Project structure

```
.
├── main.py             # App entry point — wires GUI, DB, Steam, and Lutris together
├── gui.py               # Tkinter dashboard (dark theme, search, details panel)
├── database.py           # SQLite persistence layer
├── steam.py              # Steam search, SteamDB RSS, Steam News API, BBCode cleaning
├── images.py              # Downloads/caches game art and inline patch-note images
├── lutris.py               # Reads the local Lutris game library
├── reclean_notes.py         # One-time maintenance: re-clean stored patch notes
├── schema.sql                # SQLite schema
└── requirements.txt            # Python dependencies
```

## Data storage

- `updates.db` — SQLite database of games and their updates (created automatically).
- `images/` — cached game capsule art (`<appid>.jpg`) and inline patch-note screenshots (`note_<hash>.<ext>`), created automatically.

Both are safe to delete if you want a completely fresh start — the app will recreate them.

## Notes & limitations

- Steam matching relies on the game's name in Lutris being reasonably close to its Steam store title; unusual or heavily abbreviated names may need manual review.
- Scraping Steam's search page and SteamDB's RSS feed means the app can break if either site changes its HTML/RSS structure.

## License

MIT (or update this section to match your actual license).

---

# LutrisGamesPatchNotes_old
Python script with a simple interface that gets a list of all the patch notes of all your games in your Lutris database.

-> Old version of the script, more simple with less features

![Screenshot_LutrisPatchNotes](https://github.com/user-attachments/assets/8a23226d-9d07-47f5-b037-46eb5ffe74f8)

Useful to stay up to date with Steam games in Lutris.

With this script you don't need to go one by one checking all the updates for all your Lutris games.

You can choose a game from the Lutris list loaded in the interface to filter only updates for that game.

The updates list is also written to a txt file.

The script uses scraping to get information from Steam and SteamDB.

## Requirements
- Python3
- requests
- beautifulsoup4
- lxml
- python3-tk

```
pip install -r requirements_old.txt
```
or
```
pip install requests beautifulsoup4 lxml python3-tk
```

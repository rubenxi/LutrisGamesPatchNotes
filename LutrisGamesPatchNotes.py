import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import sqlite3
from lxml import html
from datetime import datetime
import difflib
import time
import tkinter as tk
from tkinter import scrolledtext, ttk
import os
import re

db_path = os.path.expanduser("~/.local/share/lutris/pga.db")

headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/118.0.5993.117 Safari/537.36"
}

entries = []
games = []
unavailables_known = []

def extract_game_id_and_name(file_path="Updates.txt"):
    id_game_dict = {}
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

        game_name = ""
        game_id = ""

        for line in lines:
            line = line.strip()  
            if line.startswith("ID:"):
                game_id = line.split("ID:")[1].strip()
            elif line.startswith("Game:"):
                game_name = line.split("Game:")[1].strip()
                if game_id and game_name:
                    id_game_dict[game_id] = game_name
                    game_id = "" 
                    game_name = "" 

    return id_game_dict

def extract_unavailable_games(file_path="Updates.txt"):
    unavailable_games = []

    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()

        for line in reversed(lines):
            line = line.strip() 
            if line.startswith("Unavailable:"):
                unavailable_game = line.split("Unavailable:")[1].strip()
                unavailable_games.append(normalize(unavailable_game))

    return unavailable_games

def get_game_id(game_name, id_game_dict):
    game_name = game_name.lower()

    for game_id, name in id_game_dict.items():
        if name.lower() == game_name:
            return game_id

    return None

def parse_date(date_str):
    return datetime.strptime(date_str, '%a, %d %b %Y %H:%M:%S %z')

def extract_list_lutris():
    global games
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT name FROM games")
        rows = cursor.fetchall()
        for row in rows:
            games.append(row[0])
            game_id = get_game_id(row[0], id_game_dict)
            if not game_id and normalize(row[0]) not in unavailables_known:
                game_id = find_first_search_result(row[0])
            if game_id is not None:
                extract_info_rss(game_id, row[0])
            elif normalize(row[0]) not in unavailables_known:
                unavailables_known.append(normalize(row[0]))
            
    except sqlite3.Error as e:
        print("Error querying the database:", e)
    conn.close()

def find_first_search_result(game):
    url = "https://store.steampowered.com/search?term=" + str(game) + "&category1=998"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    a = soup.find("a", class_="search_result_row")
    if a:
        app_id = a.get("href").split('/')[4]
        if is_similar_name(str(game), a.get_text(strip=True)):
            print(str(game) + " -> ", a.get_text(strip=True))
            return app_id
        else:
            print("Could not find " + str(game))
            return None
    else:
        print("Could not find " + str(game))
        return None

def extract_info_rss(game_id, game):
    rss_url = f"https://steamdb.info/api/PatchnotesRSS/?appid={game_id}"
    while True:
        time.sleep(1)
        try:
            response = requests.get(rss_url, headers=headers, timeout=10)
            if response.status_code == 429:
                print(f"[{game_id}] Too Many Requests. Retrying...")
                time.sleep(10)
                continue
            response.raise_for_status()
            break
        except requests.exceptions.RequestException as e:
            print(f"[{game_id}] Request failed: {e}")
            return
    try:
        rss_data = response.text
        namespaces = {'media': 'http://search.yahoo.com/mrss/'}
        root = ET.fromstring(rss_data)
        items = root.find('channel').findall('item')
        for item in items:
            entries.append({
                'title': item.find('title').text,
                'description': item.find('description').text,
                'date': item.find('pubDate').text,
                'image': item.find('media:thumbnail', namespaces).attrib['url'],
                'link': item.find('link').text,
                'id': game_id,
                'game': game
            })
    except Exception as e:
        print(f"[{game_id}] Error parsing RSS: {e}")

def print_sorted():
    sorted_entries = sorted(entries, key=lambda x: parse_date(x['date']), reverse=True)
    with open("Updates.txt", "w", encoding="utf-8") as file:
        for entry in sorted_entries:
            file.write(f"Title: {entry['title']}\n")
            file.write(f"Description: {entry['description']}\n")
            file.write(f"Date: {entry['date']}\n")
            file.write(f"Image: {entry['image']}\n")
            file.write(f"Link: {entry['link']}\n")
            file.write(f"ID: {entry['id']}\n")
            file.write(f"Game: {entry['game']}\n")
            file.write('---\n')
        for unavailable in unavailables_known:
            file.write(f"Unavailable: {unavailable}\n")

def normalize(text):
    return ''.join(text.lower().split())

def is_similar_name(original, found, threshold=0.6):
    orig_norm = normalize(original)
    found_norm = normalize(found)
    len_orig = len(orig_norm)
    len_found = len(found_norm)
    if len_orig == 0 or len_found == 0:
        return False
    if len_orig > len_found:
        ratio = difflib.SequenceMatcher(None, orig_norm, found_norm).ratio()
        return ratio >= threshold
    best_ratio = 0
    for i in range(len_found - len_orig + 1):
        window = found_norm[i:i+len_orig]
        ratio = difflib.SequenceMatcher(None, orig_norm, window).ratio()
        if ratio > best_ratio:
            best_ratio = ratio
        if best_ratio >= threshold:
            return True
    return False

def decorate_entry(entry):
    lines = entry.strip().split('\n')
    data = {}
    for line in lines:
        if ": " in line:
            key, value = line.split(': ', 1)
            data[key.lower()] = value.strip()

    return (
        f"🎮 [Game] {data.get('game', 'Unknown')}\n"
        f"📝 [Title] {data.get('title', 'No title')}\n"
        f"📅 [Date] {data.get('date', 'Unknown')}\n"
        f"🖼️ [Image] {data.get('image', '')}\n"
        f"🔗 [Link] {data.get('link', '')}\n"
        f"📄 [Description]\n{data.get('description', '')}\n"
        f"{'─' * 60}\n"
    )

def load_updates(selected_game=None, filter_text=""):
    try:
        with open("Updates.txt", "r", encoding="utf-8") as file:
            content = file.read()
            entries_raw = content.split('---\n')
            normalized_selection = selected_game.strip().lower() if selected_game else None
            filter_text = filter_text.lower().strip()

            decorated_entries = []
            for entry in entries_raw:
                if not entry.strip():
                    continue

                if not selected_game or selected_game == "All Games":
                    if filter_text in entry.lower():
                        decorated_entries.append(decorate_entry(entry))
                else:
                    for line in entry.splitlines():
                        if line.startswith("Game:"):
                            game_name = line[5:].strip().lower()
                            if normalized_selection == game_name:
                                if filter_text in entry.lower():
                                    decorated_entries.append(decorate_entry(entry))
                                break
            final_content = '\n'.join(decorated_entries)
            text_area.delete(1.0, tk.END)
            text_area.insert(tk.END, final_content if final_content.strip() else "⚠️ No updates found for selected game.")
    except FileNotFoundError:
        text_area.delete(1.0, tk.END)
        text_area.insert(tk.END, "❌ Updates.txt not found.")

def on_game_selected(*args):
    selected_game = selected_game_var.get()
    load_updates(selected_game, filter_entry.get())

def on_filter_changed(*args):
    selected_game = selected_game_var.get()
    load_updates(selected_game, filter_entry.get())

unavailables_known = extract_unavailable_games()
id_game_dict = extract_game_id_and_name()
extract_list_lutris()
print_sorted()

root = tk.Tk()
root.title("Game Updates Viewer")
root.geometry("900x700")
root.configure(bg="#1e1e1e")

style = ttk.Style()
style.theme_use("clam")
style.configure("TMenubutton", background="#2e2e2e", foreground="white", arrowcolor="white")
style.configure("TLabel", background="#1e1e1e", foreground="white")
style.configure("TOptionMenu", background="#2e2e2e", foreground="white")

selected_game_var = tk.StringVar(value="All Games")
selected_game_var.trace_add("write", on_game_selected)

dropdown = ttk.OptionMenu(root, selected_game_var, "All Games", *games)
dropdown.config(width=40)
dropdown.pack(pady=10, side=tk.TOP, padx=10)

filter_entry = tk.Entry(root, font=("Consolas", 18))
filter_entry.bind("<KeyRelease>", on_filter_changed)
filter_entry.pack(pady=10, side=tk.TOP, padx=10)

text_area = scrolledtext.ScrolledText(
    root,
    wrap=tk.WORD,
    font=("Consolas", 15),
    bg="#1e1e1e",
    fg="#d4d4d4",
    insertbackground="white",
    borderwidth=0
)
text_area.pack(expand=True, fill='both', padx=10, pady=10)

load_updates()
root.mainloop()

import threading

from database import Database
from lutris import LutrisReader
from steam import SteamClient, normalize, clean_bbcode, find_matching_news
from gui import UpdateGUI



database = Database()

lutris = LutrisReader()

steam = SteamClient()

def display_notes(name, title, notes):

    gui.log(
        "═══════════════════════════"
    )

    gui.log(
        f"🎮 {name} — {title}"
    )

    gui.log(
        "───────────────────────────"
    )

    for line in notes.splitlines():

        if line.strip():

            gui.log(
                line.strip()
            )

    gui.log(
        "═══════════════════════════"
    )



def show_notes(update):

    if update["notes"]:

        display_notes(
            update["lutris_name"],
            update["title"],
            update["notes"]
        )

        return



    fallback = (
        update["description"]
        or
        "No notes available."
    )


    display_notes(
        update["lutris_name"],
        update["title"] + " (full notes not fetched yet)",
        fallback
    )



def notify_new_update(name, title):
    gui.log("✨✨✨✨✨✨")
    gui.log("🆕 Updates found!")
    gui.log(f"🎮 {name}")
    gui.log(f"📝 {title}")
    gui.log("✨✨✨✨✨✨")
    gui.load_updates()

def refresh():

    gui.refresh_button.config(
        state="disabled"
    )


    gui.log(
        "🚀 Starting update check..."
    )


    thread = threading.Thread(
        target=run_refresh,
        daemon=True
    )


    thread.start()



def run_refresh():

    try:

        games = lutris.get_games()

        total = len(games)



        # -------------------------
        # Remove games deleted from Lutris
        # -------------------------

        normalized_games = [

            normalize(name)

            for name in games

        ]


        removed_games = database.remove_missing_games(
            normalized_games
        )


        if removed_games:

            gui.log(
                f"🗑 Removed {len(removed_games)} missing Lutris games:"
            )


            for removed in removed_games:

                gui.log(
                    f"   ❌ {removed}"
                )

        else:

            gui.log(
                "✅ No removed Lutris games detected"
            )



        gui.set_progress(
            0,
            total
        )


        gui.log(
            f"🎮 Found {total} Lutris games"
        )


        steam.search_requests = 0

        steam.rss_requests = 0

        steam.news_requests = 0



        # -------------------------
        # Check games
        # -------------------------

        for index, name in enumerate(games):


            gui.log(
                f"[{index+1}/{total}] Checking {name}"
            )


            normalized = normalize(
                name
            )


            game = database.get_game(
                normalized
            )



            if not game:


                game_id = database.add_or_update_game(
                    name,
                    normalized
                )


                game = database.get_game(
                    normalized
                )


            else:

                game_id = game["id"]



            # -------------------------
            # Steam search only if needed
            # -------------------------

            if not game["steam_appid"]:


                gui.log(
                    "  🔎 Searching Steam..."
                )


                result = steam.search_game(
                    name
                )



                if result:


                    database.save_steam_data(

                        game_id,

                        result["appid"],

                        result["url"]

                    )


                    gui.log(
                        "  ✅ Steam link saved"
                    )


                else:


                    database.mark_unavailable(
                        game_id
                    )


                    database.save_not_found(
                        game_id
                    )


                    gui.log(
                        "  ❌ Steam game not found"
                    )



            # Reload after Steam lookup

            game = database.get_game(
                normalized
            )



            # -------------------------
            # SteamDB updates
            # -------------------------

            if game["steam_appid"]:


                gui.log(
                    "  📡 Checking SteamDB..."
                )


                updates = steam.get_updates(
                    game["steam_appid"]
                )



                # Official news is only fetched once per game, and
                # only if at least one update actually needs it.
                news_items = None


                for update in updates:


                    result = database.save_update(
                        game_id,
                        update["title"],
                        update["description"],
                        update["date"],
                        update["link"]
                    )


                    # Attach full notes for this row if we don't
                    # have them yet — covers brand-new updates
                    # AND older rows saved before this existed.
                    if result["id"] and not result["notes"]:

                        if news_items is None:

                            news_items = steam.get_news_for_app(
                                game["steam_appid"]
                            )


                        match = find_matching_news(
                            update["date"],
                            news_items
                        )


                        if match:

                            gui.log(
                                f"  📖 Notes matched: {update['title']}"
                            )


                            notes = clean_bbcode(
                                match.get("contents", "")
                            )


                            database.save_notes(
                                result["id"],
                                notes
                            )


                        else:

                            gui.log(
                                f"  ⚠️ No official news match for: {update['title']}"
                            )


                    if result["inserted"]:

                        identifier = (
                            name,
                            update["title"],
                            update["date"],
                        )

                        gui.root.after(
                            0,
                            lambda i=identifier, n=name, t=update["title"]:
                                (
                                    gui.new_updates.add(i),
                                    notify_new_update(n, t),
                                )
                        )


                database.set_checked(
                    game_id
                )


            else:

                gui.log(
                    "  ⏭ Skipping SteamDB"
                )



            gui.set_progress(
                index + 1,
                total
            )



        gui.log(
            ""
        )


        gui.log(
            "✨ Finished."
        )


        gui.log(
            f"Steam searches: {steam.search_requests}"
        )


        gui.log(
            f"SteamDB requests: {steam.rss_requests}"
        )


        gui.log(
            f"Steam news requests: {steam.news_requests}"
        )


        gui.load_updates()



    except Exception as e:


        gui.log(
            "❌ ERROR: "
            +
            str(e)
        )



    finally:


        gui.refresh_button.config(
            state="normal"
        )


        gui.set_status(
            "🌱 Ready"
        )




gui = UpdateGUI(
    database,
    refresh,
    show_notes
)


gui.run()

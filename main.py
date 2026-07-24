import threading

from database import Database
from lutris import LutrisReader
from steam import SteamClient, normalize
from gui import UpdateGUI



database = Database()

lutris = LutrisReader()

steam = SteamClient()

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



                for update in updates:


                    inserted = database.save_update(
                        game_id,
                        update["title"],
                        update["description"],
                        update["date"],
                        update["link"]
                    )

                    if inserted:
                        gui.root.after(
                            0,
                            lambda name=name, title=update["title"]:
                                notify_new_update(name, title)
                        )

                        gui.root.after(0, gui.load_updates)


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
    refresh
)


gui.run()

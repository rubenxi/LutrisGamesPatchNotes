import threading
from datetime import datetime, timedelta

from database import Database
from lutris import LutrisReader
from steam import SteamClient, normalize, clean_bbcode, find_matching_news, extract_note_image_urls
from images import ensure_image_cached, ensure_note_image_cached
from gui import UpdateGUI


# How long to wait before retrying a Steam search for a game that
# came up with no match last time - avoids hammering Steam every
# single refresh for games that simply aren't on Steam.
RETRY_COOLDOWN_DAYS = 7


def should_retry_search(last_checked):

    if not last_checked:
        return True


    try:

        checked_at = datetime.fromisoformat(
            last_checked
        )

    except ValueError:

        return True


    return (
        datetime.now() - checked_at
        >=
        timedelta(days=RETRY_COOLDOWN_DAYS)
    )



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

    gui.news_check.config(
        state="disabled"
    )


    gui.log(
        "📰 Starting news check..."
        if gui.news_mode else
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



            if game["hidden"]:

                gui.log(
                    "  🙈 Hidden - skipping"
                )

                gui.set_progress(
                    index + 1,
                    total
                )

                continue



            # -------------------------
            # Steam search only if needed
            # -------------------------

            needs_search = not game["steam_appid"]


            if (
                needs_search
                and game["unavailable"]
                and not should_retry_search(game["last_checked"])
            ):

                needs_search = False

                gui.log(
                    "  ⏭ Skipping search "
                    "(no Steam match recently, will retry later)"
                )



            if needs_search:


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

                        result["url"],

                        result.get("rating_text"),

                        result.get("rating_percent")

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


                    database.set_checked(
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
            # SteamDB updates / Steam news
            # -------------------------

            if game["steam_appid"] and gui.news_mode:


                ensure_image_cached(
                    game["steam_appid"]
                )


                gui.log(
                    "  📰 Checking Steam news..."
                )


                # One request gets every news item's full text
                # directly, so unlike the updates flow there's no
                # separate lazy notes fetch needed here.

                news_items = steam.get_news_items(
                    game["steam_appid"]
                )


                for item in news_items:


                    notes = clean_bbcode(
                        item["contents"]
                    )


                    for image_url in extract_note_image_urls(notes):

                        ensure_note_image_cached(
                            image_url
                        )


                    result = database.save_news(
                        game_id,
                        item["title"],
                        notes,
                        item["date"],
                        item["link"]
                    )


                    if result["inserted"]:

                        identifier = (
                            name,
                            item["title"],
                            item["date"],
                        )

                        gui.root.after(
                            0,
                            lambda i=identifier, n=name, t=item["title"]:
                                (
                                    gui.new_updates.add(i),
                                    notify_new_update(n, t),
                                )
                        )


                database.set_checked(
                    game_id
                )


            elif game["steam_appid"]:


                ensure_image_cached(
                    game["steam_appid"]
                )


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


                    description = (update["description"] or "").strip()


                    if description.startswith("SteamDB Build"):

                        # No real patch-note content, just a build
                        # bump - skip it entirely rather than
                        # saving it.

                        continue


                    result = database.save_update(
                        game_id,
                        update["title"],
                        description,
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

                            notes = clean_bbcode(
                                match.get("contents", "")
                            )


                            for image_url in extract_note_image_urls(notes):

                                ensure_note_image_cached(
                                    image_url
                                )


                            database.save_notes(
                                result["id"],
                                notes
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

        gui.news_check.config(
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

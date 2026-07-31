"""
One-time maintenance script.

Notes are saved to the database already-cleaned, and the normal
refresh flow only fetches notes for updates that don't have any yet.
That means any row saved before a clean_bbcode fix keeps its old,
broken text forever unless it's redone from scratch.

This script re-fetches each game's official Steam news and re-runs
the current clean_bbcode on every stored update, overwriting the
notes column regardless of whether it already had something in it.

It also re-runs clean_update_title() on every stored update's title
AND description, stripping the "(Steam®)" / "(SteamDB Build 12345)"
suffixes from rows that were saved before that cleanup existed (the
description column is what the updates-tab Information column
actually displays). This one doesn't need a news match - it just
rewrites the columns in place.

Run it once after fixing clean_bbcode:

    python3 reclean_notes.py
"""

from database import Database
from steam import (
    SteamClient,
    clean_bbcode,
    clean_update_title,
    find_matching_news,
    extract_note_image_urls,
)
from images import ensure_note_image_cached


def main():

    database = Database()
    steam = SteamClient()

    games = database.get_all_games()

    total_updates = 0
    reclean = 0
    retitled = 0
    redescribed = 0
    no_match = 0
    skipped_games = 0

    for game in games:

        if not game["steam_appid"]:

            skipped_games += 1
            continue


        updates = database.get_updates(
            game["id"]
        )

        # Nothing to do for a game with no saved updates, or one
        # where the only row is the "Not found" placeholder.
        real_updates = [
            update
            for update in updates
            if update["title"] != "Not found"
        ]

        if not real_updates:
            continue


        print(
            f"🎮 {game['lutris_name']} "
            f"({len(real_updates)} update(s))"
        )

        news_items = steam.get_news_for_app(
            game["steam_appid"]
        )

        for update in real_updates:

            total_updates += 1

            cleaned_title = clean_update_title(
                update["title"]
            )

            if cleaned_title != update["title"]:

                database.save_title(
                    update["id"],
                    cleaned_title
                )

                retitled += 1

                print(
                    f"  ✂️ Retitled: {update['title']!r} -> {cleaned_title!r}"
                )


            cleaned_description = clean_update_title(
                update["description"]
            )

            if cleaned_description != update["description"]:

                database.save_description(
                    update["id"],
                    cleaned_description
                )

                redescribed += 1

                print(
                    f"  ✂️ Cleaned description: {update['description']!r} -> {cleaned_description!r}"
                )

            match = find_matching_news(
                update["update_date"],
                news_items
            )

            if not match:

                no_match += 1

                print(
                    f"  ⚠️ No official news match for: {update['title']}"
                )

                continue


            notes = clean_bbcode(
                match.get(
                    "contents",
                    ""
                )
            )

            for image_url in extract_note_image_urls(notes):

                ensure_note_image_cached(
                    image_url
                )

            database.save_notes(
                update["id"],
                notes
            )

            reclean += 1

            print(
                f"  🧹 Re-cleaned: {update['title']}"
            )


    print()
    print("─────────────────────────────")
    print(f"Games skipped (no Steam link): {skipped_games}")
    print(f"Updates checked: {total_updates}")
    print(f"Titles cleaned up: {retitled}")
    print(f"Descriptions cleaned up: {redescribed}")
    print(f"Notes re-cleaned: {reclean}")
    print(f"No news match found: {no_match}")

    database.close()


if __name__ == "__main__":
    main()

from pathlib import Path
import sqlite3
from datetime import datetime
import threading


BASE_DIR = Path(__file__).resolve().parent

DB_FILE = BASE_DIR / "updates.db"
SCHEMA_FILE = BASE_DIR / "schema.sql"



class Database:


    def __init__(self):

        self.lock = threading.Lock()


        self.connection = sqlite3.connect(
            DB_FILE,
            check_same_thread=False
        )


        self.connection.row_factory = sqlite3.Row


        self.initialize()



    def initialize(self):

        with self.lock:

            with open(
                SCHEMA_FILE,
                "r",
                encoding="utf-8"
            ) as file:

                schema = file.read()


            self.connection.executescript(
                schema
            )


            self.connection.commit()



    def close(self):

        with self.lock:

            self.connection.close()



    # ----------------------------
    # Games
    # ----------------------------


    def get_game(
            self,
            normalized_name
    ):

        with self.lock:

            cursor = self.connection.cursor()


            cursor.execute(
                """
                SELECT *
                FROM games
                WHERE normalized_name=?
                """,
                (
                    normalized_name,
                )
            )


            return cursor.fetchone()



    def add_or_update_game(
            self,
            lutris_name,
            normalized_name
    ):

        existing = self.get_game(
            normalized_name
        )


        if existing:

            return existing["id"]



        with self.lock:

            cursor = self.connection.cursor()


            cursor.execute(
                """
                INSERT INTO games
                (
                    lutris_name,
                    normalized_name
                )

                VALUES (?,?)
                """,
                (
                    lutris_name,
                    normalized_name
                )
            )


            self.connection.commit()


            return cursor.lastrowid



    def save_steam_data(
            self,
            game_id,
            appid,
            url
    ):

        with self.lock:

            self.connection.execute(
                """
                UPDATE games

                SET
                    steam_appid=?,
                    steam_url=?,
                    unavailable=0

                WHERE id=?
                """,
                (
                    appid,
                    url,
                    game_id
                )
            )


            self.connection.commit()



    def mark_unavailable(
            self,
            game_id
    ):

        with self.lock:

            self.connection.execute(
                """
                UPDATE games

                SET unavailable=1

                WHERE id=?
                """,
                (
                    game_id,
                )
            )


            self.connection.commit()



    def get_all_games(self):

        with self.lock:

            cursor = self.connection.cursor()


            cursor.execute(
                """
                SELECT *
                FROM games
                ORDER BY lutris_name
                """
            )


            return cursor.fetchall()



    def remove_missing_games(
            self,
            lutris_games
    ):

        normalized_games = set(
            lutris_games
        )


        removed = []


        with self.lock:

            cursor = self.connection.cursor()


            cursor.execute(
                """
                SELECT
                    id,
                    lutris_name,
                    normalized_name

                FROM games
                """
            )


            stored_games = cursor.fetchall()



            for game in stored_games:


                if game["normalized_name"] not in normalized_games:


                    cursor.execute(
                        """
                        DELETE FROM updates
                        WHERE game_id=?
                        """,
                        (
                            game["id"],
                        )
                    )


                    cursor.execute(
                        """
                        DELETE FROM games
                        WHERE id=?
                        """,
                        (
                            game["id"],
                        )
                    )


                    removed.append(
                        game["lutris_name"]
                    )



            self.connection.commit()



        return removed



    # ----------------------------
    # Updates
    # ----------------------------


    def save_not_found(
            self,
            game_id
    ):

        with self.lock:

            cursor = self.connection.cursor()


            cursor.execute(
                """
                SELECT id
                FROM updates

                WHERE game_id=?
                AND title='Not found'
                """,
                (
                    game_id,
                )
            )


            exists = cursor.fetchone()



            if exists:

                return



            cursor.execute(
                """
                INSERT INTO updates
                (
                    game_id,
                    title,
                    description,
                    update_date,
                    link
                )

                VALUES (?,?,?,?,?)
                """,
                (
                    game_id,
                    "Not found",
                    "Game not found on Steam",
                    "",
                    ""
                )
            )


            self.connection.commit()



    def save_update(
            self,
            game_id,
            title,
            description,
            date,
            link
    ):

        with self.lock:

            cursor = self.connection.cursor()

            cursor.execute(
                """
                INSERT OR IGNORE INTO updates
                (
                    game_id,
                    title,
                    description,
                    update_date,
                    link
                )
                VALUES (?,?,?,?,?)
                """,
                (
                    game_id,
                    title,
                    description,
                    date,
                    link
                )
            )

            inserted = cursor.rowcount > 0

            self.connection.commit()


            cursor.execute(
                """
                SELECT id, notes
                FROM updates
                WHERE game_id=? AND link=?
                """,
                (
                    game_id,
                    link
                )
            )

            row = cursor.fetchone()


            return {
                "id": row["id"] if row else None,
                "notes": row["notes"] if row else None,
                "inserted": inserted
            }



    def save_notes(
            self,
            update_id,
            notes
    ):

        with self.lock:

            self.connection.execute(
                """
                UPDATE updates

                SET notes=?

                WHERE id=?
                """,
                (
                    notes,
                    update_id
                )
            )


            self.connection.commit()



    def get_updates(
            self,
            game_id=None
    ):

        with self.lock:

            cursor = self.connection.cursor()



            if game_id:


                cursor.execute(
                    """
                    SELECT
                        games.lutris_name,
                        updates.*

                    FROM updates

                    JOIN games

                    ON games.id=updates.game_id

                    WHERE games.id=?

                    ORDER BY update_date DESC
                    """,
                    (
                        game_id,
                    )
                )


            else:


                cursor.execute(
                    """
                    SELECT
                        games.lutris_name,
                        updates.*

                    FROM updates

                    JOIN games

                    ON games.id=updates.game_id

                    ORDER BY update_date DESC
                    """
                )



            return cursor.fetchall()



    def set_checked(
            self,
            game_id
    ):

        with self.lock:

            self.connection.execute(
                """
                UPDATE games

                SET last_checked=?

                WHERE id=?
                """,
                (
                    datetime.now().isoformat(),
                    game_id
                )
            )


            self.connection.commit()

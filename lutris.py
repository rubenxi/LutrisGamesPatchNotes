from pathlib import Path
import sqlite3
import os


class LutrisReader:


    def __init__(self):

        self.db_path = self.find_lutris_database()



    def find_lutris_database(self):

        possible_paths = [

            Path.home() /
            ".var/app/net.lutris.Lutris/data/lutris/pga.db",

            Path.home() /
            ".local/share/lutris/pga.db"

        ]


        for path in possible_paths:

            if path.exists():
                return path


        return None



    def available(self):

        return self.db_path is not None



    def get_games(self):

        if not self.available():
            return []


        connection = sqlite3.connect(
            self.db_path
        )

        cursor = connection.cursor()


        cursor.execute(
            """
            SELECT name
            FROM games
            ORDER BY name
            """
        )


        games = [
            row[0]
            for row in cursor.fetchall()
        ]


        connection.close()


        return games

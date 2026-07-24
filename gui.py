import tkinter as tk
from tkinter import ttk
import subprocess
from datetime import datetime
from email.utils import parsedate_to_datetime


class UpdateGUI:


    def __init__(
            self,
            database,
            refresh_callback
    ):

        self.database = database
        self.refresh_callback = refresh_callback

        self.root = tk.Tk()

        self.root.title(
            "🎮 Lutris Steam Updates"
        )

        self.root.geometry(
            "1600x900"
        )

        self.root.configure(
            bg="#181825"
        )

        self.updates = []

        self.create_widgets()



    # ------------------------------------------------
    # Brave browser
    # ------------------------------------------------

    def open_in_brave(
            self,
            url
    ):

        if not url:
            return


        for browser in (
            "brave-browser",
            "brave"
        ):

            try:

                subprocess.Popen(
                    [
                        browser,
                        url
                    ],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )

                return

            except FileNotFoundError:
                continue



    # ------------------------------------------------
    # Interface
    # ------------------------------------------------

    def create_widgets(self):

        style = ttk.Style()

        style.theme_use(
            "clam"
        )


        style.configure(
            "Treeview",
            background="#202124",
            foreground="#eeeeee",
            fieldbackground="#202124",
            rowheight=65,
            font=(
                "Segoe UI",
                11
            )
        )


        style.configure(
            "Treeview.Heading",
            background="#4b0082",
            foreground="#ffffff",
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )


        style.map(
            "Treeview",
            background=[
                (
                    "selected",
                    "#4338ca"
                )
            ]
        )



        # -------------------------
        # Top bar
        # -------------------------

        top = tk.Frame(
            self.root,
            bg="#181825"
        )

        top.pack(
            fill="x",
            pady=10
        )


        self.refresh_button = ttk.Button(
            top,
            text="✨ Refresh Updates ✨",
            command=self.refresh_clicked
        )

        self.refresh_button.pack(
            side="left",
            padx=10
        )



        self.search = ttk.Entry(
            top,
            font=(
                "Segoe UI",
                12
            )
        )

        self.search.pack(
            side="left",
            fill="x",
            expand=True,
            padx=10
        )


        self.search.bind(
            "<KeyRelease>",
            lambda e:self.load_updates()
        )



        # -------------------------
        # Status
        # -------------------------

        self.status = tk.Label(
            self.root,
            text="🌱 Ready",
            bg="#181825",
            fg="#7dd3fc",
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )

        self.status.pack(
            anchor="w",
            padx=10
        )



        # -------------------------
        # Progress
        # -------------------------

        self.progress = ttk.Progressbar(
            self.root,
            mode="determinate"
        )

        self.progress.pack(
            fill="x",
            padx=10,
            pady=5
        )



        # -------------------------
        # Table
        # -------------------------

        frame = tk.Frame(
            self.root,
            bg="#181825"
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )


        columns = (
            "game",
            "date",
            "description"
        )


        self.tree = ttk.Treeview(
            frame,
            columns=columns,
            show="headings"
        )


        self.tree.heading(
            "game",
            text="🎮 Game Title"
        )


        self.tree.heading(
            "date",
            text="📅 Released"
        )

        self.tree.heading(
            "description",
            text="💡 Information"
        )



        self.tree.column(
            "game",
            width=350
        )

        self.tree.column(
            "date",
            width=220
        )

        self.tree.column(
            "description",
            width=1000
        )



        scrollbar = ttk.Scrollbar(
            frame,
            orient="vertical",
            command=self.tree.yview
        )


        self.tree.configure(
            yscrollcommand=scrollbar.set
        )


        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )

        scrollbar.pack(
            side="right",
            fill="y"
        )


        self.tree.tag_configure(
            "even",
            background="#202124"
        )


        self.tree.tag_configure(
            "odd",
            background="#292b36"
        )


        self.tree.bind(
            "<Double-1>",
            self.open_selected
        )



        # -------------------------
        # Console
        # -------------------------

        self.console = tk.Text(
            self.root,
            height=8,
            bg="#101018",
            fg="#a7f3d0",
            insertbackground="white",
            font=(
                "Cascadia Mono",
                10
            ),
            wrap="word"
        )


        self.console.pack(
            fill="x",
            padx=10,
            pady=10
        )


        self.console.insert(
            "end",
            "🌟 Lutris Steam Updates ready!\n"
            "💾 Database loaded\n"
            "🎮 Waiting for refresh...\n\n"
        )


        self.console.configure(
            state="disabled"
        )



    # ------------------------------------------------
    # Logging
    # ------------------------------------------------

    def log(
            self,
            text
    ):

        self.console.configure(
            state="normal"
        )

        self.console.insert(
            "end",
            f"[{datetime.now().strftime('%H:%M:%S')}] {text}\n"
        )

        self.console.see(
            "end"
        )

        self.console.configure(
            state="disabled"
        )

        self.root.update_idletasks()



    def set_status(
            self,
            text
    ):

        self.status.config(
            text=text
        )

        self.root.update_idletasks()



    def set_progress(
            self,
            value,
            maximum
    ):

        self.progress["maximum"] = maximum

        self.progress["value"] = value

        self.root.update_idletasks()


    # ------------------------------------------------
    # Refresh
    # ------------------------------------------------

    def refresh_clicked(self):

        # Save current updates before refresh
        old_updates = set()


        for update in self.database.get_updates():

            old_updates.add(
                (
                    update["lutris_name"],
                    update["title"],
                    update["update_date"]
                )
            )



        self.log(
            "🚀 Starting update check..."
        )


        self.refresh_callback()



        self.log(
            "🔎 Checking for new updates..."
        )


        new_updates = []



        for update in self.database.get_updates():

            identifier = (
                update["lutris_name"],
                update["title"],
                update["update_date"]
            )


            if identifier not in old_updates:

                new_updates.append(
                    update
                )



        if new_updates:


            self.log(
                f"🆕 {len(new_updates)} new update(s) found!"
            )


            for update in new_updates:

                self.log(
                    "-----------------------------"
                )

                self.log(
                    f"🎮 {update['lutris_name']}"
                )

                self.log(
                    f"📝 {update['title']}"
                )

                self.log(
                    f"📅 {update['update_date']}"
                )


        else:

            self.log(
                "ℹ️ No new updates found."
            )



        self.log(
            "🎉 Update check finished!"
        )


        self.load_updates()


    # ------------------------------------------------
    # Load updates
    # ------------------------------------------------


    def format_date(self, value):

        if not value:
            return ""

        try:
            date = parsedate_to_datetime(value)

            return date.strftime(
                "%d %b %Y  %H:%M"
            )

        except Exception:

            return value
        
    def load_updates(self):

        for row in self.tree.get_children():

            self.tree.delete(row)



        search = self.search.get().lower()


        self.updates = list(
            self.database.get_updates()
        )



        def sort_date(update):

            value = str(
                update["update_date"]
            ).strip()


            try:

                return parsedate_to_datetime(
                    value
                ).timestamp()

            except:

                return 0



        self.updates.sort(
            key=sort_date,
            reverse=True
        )



        count = 0


        for index, update in enumerate(self.updates):


            searchable = (
                str(update["lutris_name"])
                +
                str(update["title"])
                +
                str(update["description"])
            ).lower()


            if search not in searchable:
                continue



            tag = (
                "even"
                if count % 2 == 0
                else "odd"
            )

            description = update["description"].strip()

            if description and not description.startswith("SteamDB Build"):
                description = "✨ " + description
            self.tree.insert(
                "",
                "end",
                iid=str(index),
                tags=(tag,),
                values=(
                    update["lutris_name"],
                    self.format_date(update["update_date"]),
                    description
                )
            )


            count += 1



        self.status.config(
            text=f"🌱 {count} updates found"
        )



    # ------------------------------------------------
    # Open SteamDB
    # ------------------------------------------------

    def open_selected(
            self,
            event
    ):

        selected = self.tree.selection()

        if not selected:
            return


        update = self.updates[
            int(selected[0])
        ]


        self.open_in_brave(
            update["link"]
        )



    def run(self):

        self.load_updates()

        self.root.mainloop()

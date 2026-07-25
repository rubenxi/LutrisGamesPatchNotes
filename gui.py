import tkinter as tk
from tkinter import ttk
import subprocess
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from PIL import Image, ImageTk
from images import get_local_image_path, get_local_note_image_path


NOTE_IMAGE_LINE = re.compile(
    r"^\[\[STEAM_NOTE_IMAGE:(.+)\]\]$"
)


# ------------------------------------------------
# Theme
#
# tkinter/ttk has no real border-radius or alpha-transparency
# support, so "rounded" widgets below are hand-drawn on a Canvas,
# and "transparency" is faked with a cohesive family of blended
# dark tones instead of true see-through panels.
# ------------------------------------------------

BG = "#181825"
PANEL_BG = "#1c1e2b"          # slightly lighter than BG - "glass" panel look
PANEL_BG_ALT = "#20222f"

ACCENT = "#7dd3fc"             # cyan - status text / progress / headers
ACCENT_DIM = "#38bdf8"

BUTTON_BG = "#11121a"
BUTTON_BG_HOVER = "#1c1e2e"
BUTTON_BG_DISABLED = "#0d0e14"
BUTTON_OUTLINE = "#2dd4bf"

BORDER = "#2a2d3e"


def _rounded_rect_points(
        x1,
        y1,
        x2,
        y2,
        radius
):

    radius = min(
        radius,
        (x2 - x1) / 2,
        (y2 - y1) / 2
    )

    return [
        x1 + radius, y1,
        x2 - radius, y1,
        x2, y1,
        x2, y1 + radius,
        x2, y2 - radius,
        x2, y2,
        x2 - radius, y2,
        x1 + radius, y2,
        x1, y2,
        x1, y2 - radius,
        x1, y1 + radius,
        x1, y1,
    ]


def draw_rounded_rect(
        canvas,
        x1,
        y1,
        x2,
        y2,
        radius=14,
        **kwargs
):

    return canvas.create_polygon(
        _rounded_rect_points(
            x1,
            y1,
            x2,
            y2,
            radius
        ),
        smooth=True,
        **kwargs
    )


class RoundedButton(tk.Canvas):

    """
    A drop-in-ish replacement for a ttk.Button that actually has
    rounded corners, since ttk buttons can't. Supports the same
    .config(state="disabled"/"normal") calls the rest of the app
    already makes.
    """

    def __init__(
            self,
            parent,
            text,
            command,
            width=260,
            height=50,
            radius=18,
            bg_parent=BG,
            fill=BUTTON_BG,
            fill_hover=BUTTON_BG_HOVER,
            fill_disabled=BUTTON_BG_DISABLED,
            outline=BUTTON_OUTLINE,
            fg=ACCENT,
            fg_disabled="#4b5563",
            font=("Segoe UI", 12, "bold")
    ):

        super().__init__(
            parent,
            width=width,
            height=height,
            bg=bg_parent,
            highlightthickness=0,
            bd=0
        )

        self.command = command
        self.fill = fill
        self.fill_hover = fill_hover
        self.fill_disabled = fill_disabled
        self.outline = outline
        self.fg = fg
        self.fg_disabled = fg_disabled
        self.disabled = False

        self.rect = draw_rounded_rect(
            self,
            2,
            2,
            width - 2,
            height - 2,
            radius=radius,
            fill=fill,
            outline=outline,
            width=1.5
        )

        self.text_id = self.create_text(
            width / 2,
            height / 2,
            text=text,
            fill=fg,
            font=font
        )

        self.bind(
            "<Button-1>",
            self._on_click
        )

        self.bind(
            "<Enter>",
            self._on_enter
        )

        self.bind(
            "<Leave>",
            self._on_leave
        )

    def _on_click(self, event):

        if not self.disabled and self.command:
            self.command()

    def _on_enter(self, event):

        if not self.disabled:

            self.itemconfig(
                self.rect,
                fill=self.fill_hover
            )

    def _on_leave(self, event):

        if not self.disabled:

            self.itemconfig(
                self.rect,
                fill=self.fill
            )

    def config(self, **kwargs):

        state = kwargs.pop(
            "state",
            None
        )

        if state is not None:

            self.disabled = (state == "disabled")

            if self.disabled:

                self.itemconfig(
                    self.rect,
                    fill=self.fill_disabled,
                    outline=BORDER
                )

                self.itemconfig(
                    self.text_id,
                    fill=self.fg_disabled
                )

            else:

                self.itemconfig(
                    self.rect,
                    fill=self.fill,
                    outline=self.outline
                )

                self.itemconfig(
                    self.text_id,
                    fill=self.fg
                )

        if kwargs:

            super().config(
                **kwargs
            )

    configure = config


class RoundedEntryFrame(tk.Frame):

    """
    Wraps a plain, borderless tk.Entry with a hand-drawn rounded
    background so the search box reads as a modern rounded field
    instead of ttk's square-edged default.
    """

    def __init__(
            self,
            parent,
            bg_parent=BG,
            radius=14,
            height=38,
            **entry_kwargs
    ):

        super().__init__(
            parent,
            bg=bg_parent,
            highlightthickness=0,
            bd=0
        )

        self.canvas = tk.Canvas(
            self,
            height=height,
            bg=bg_parent,
            highlightthickness=0,
            bd=0
        )

        self.canvas.pack(
            fill="both",
            expand=True
        )

        self.entry = tk.Entry(
            self.canvas,
            bg=PANEL_BG_ALT,
            fg="#eeeeee",
            insertbackground=ACCENT,
            relief="flat",
            highlightthickness=0,
            bd=0,
            **entry_kwargs
        )

        self.canvas.bind(
            "<Configure>",
            self._redraw
        )

        self.radius = radius
        self.entry_window = None

    def _redraw(self, event):

        self.canvas.delete(
            "bg"
        )

        draw_rounded_rect(
            self.canvas,
            1,
            1,
            event.width - 1,
            event.height - 1,
            radius=self.radius,
            fill=PANEL_BG_ALT,
            outline=BORDER,
            width=1,
            tags="bg"
        )

        if self.entry_window is None:

            self.entry_window = self.canvas.create_window(
                14,
                event.height / 2,
                anchor="w",
                window=self.entry,
                width=event.width - 28
            )

        else:

            self.canvas.coords(
                self.entry_window,
                14,
                event.height / 2
            )

            self.canvas.itemconfig(
                self.entry_window,
                width=event.width - 28
            )

    def bind(self, sequence=None, func=None, add=None):

        # Route key bindings (e.g. <KeyRelease>) to the inner
        # entry, since that's where the user is actually typing.
        return self.entry.bind(
            sequence,
            func,
            add
        )

    def get(self):

        return self.entry.get()


class ContextMenu(tk.Toplevel):

    """
    A themed stand-in for tk.Menu. Native menus render with
    whatever the OS/window-manager theme is (usually a plain
    square Motif/GTK look), which clashes badly with the rest of
    this app's dark, rounded-corner styling. This draws a small
    borderless popup instead, with items that highlight on hover.
    """

    def __init__(
            self,
            root_window,
            items,
            radius=12
    ):

        super().__init__(
            root_window
        )

        self.root_window = root_window
        self._click_bind_id = None

        self.overrideredirect(
            True
        )

        self.attributes(
            "-topmost",
            True
        )


        # A 1px BORDER-colored Toplevel background peeking out
        # around a PANEL_BG_ALT inner frame fakes a hairline
        # border, since Toplevel itself can't have rounded
        # corners or a real outline.

        self.configure(
            bg=BORDER
        )

        inner = tk.Frame(
            self,
            bg=PANEL_BG_ALT
        )

        inner.pack(
            padx=1,
            pady=1
        )


        for entry in items:

            label, command = entry[0], entry[1]

            danger = entry[2] if len(entry) > 2 else False

            self._add_item(
                inner,
                label,
                command,
                danger
            )


        self.bind(
            "<Escape>",
            lambda event: self.close()
        )


    def _add_item(
            self,
            parent,
            label,
            command,
            danger
    ):

        row = tk.Label(
            parent,
            text=label,
            bg=PANEL_BG_ALT,
            fg="#f87171" if danger else "#eeeeee",
            font=(
                "Segoe UI",
                11
            ),
            anchor="w",
            padx=18,
            pady=10,
            cursor="hand2"
        )

        row.pack(
            fill="x"
        )

        row.bind(
            "<Enter>",
            lambda event, r=row: r.configure(bg=BUTTON_BG_HOVER)
        )

        row.bind(
            "<Leave>",
            lambda event, r=row: r.configure(bg=PANEL_BG_ALT)
        )

        row.bind(
            "<Button-1>",
            lambda event, cmd=command: self._select(cmd)
        )


    def _select(self, command):

        self.close()

        command()


    def show(self, x, y):

        self.update_idletasks()

        self.geometry(
            f"+{x}+{y}"
        )

        self.deiconify()

        self.lift()


        # Any click on the root window outside the menu itself
        # closes it - the menu's own rows stop this via the
        # "break" they return below, so only outside clicks reach
        # here.

        self._click_bind_id = self.root_window.bind(
            "<Button-1>",
            lambda event: self.close(),
            add="+"
        )

        self.bind(
            "<FocusOut>",
            lambda event: self.close()
        )

        self.focus_set()


    def close(self):

        if self._click_bind_id:

            try:

                self.root_window.unbind(
                    "<Button-1>",
                    self._click_bind_id
                )

            except tk.TclError:

                pass

            self._click_bind_id = None


        try:

            self.destroy()

        except tk.TclError:

            pass


class ConfirmDialog(tk.Toplevel):

    """
    A themed replacement for tkinter.messagebox.askyesno. The
    stock messagebox pops up as a plain OS dialog that clashes
    with the rest of the app, so this draws a small dark panel
    instead, using the same RoundedButton the rest of the UI
    already uses.
    """

    def __init__(
            self,
            root_window,
            title,
            message,
            confirm_label="Confirm",
            cancel_label="Cancel",
            danger=True
    ):

        super().__init__(
            root_window
        )

        self.root_window = root_window
        self.result = False

        self.overrideredirect(
            True
        )

        self.attributes(
            "-topmost",
            True
        )


        # Same hairline-border trick as ContextMenu: a
        # BORDER-colored Toplevel peeking out around a PANEL_BG
        # inner panel.

        self.configure(
            bg=BORDER
        )

        panel = tk.Frame(
            self,
            bg=PANEL_BG
        )

        panel.pack(
            padx=1,
            pady=1
        )

        content = tk.Frame(
            panel,
            bg=PANEL_BG
        )

        content.pack(
            padx=28,
            pady=24
        )


        tk.Label(
            content,
            text=title,
            bg=PANEL_BG,
            fg=ACCENT,
            font=(
                "Segoe UI",
                15,
                "bold"
            ),
            anchor="w",
            justify="left"
        ).pack(
            fill="x",
            pady=(0, 12)
        )

        tk.Label(
            content,
            text=message,
            bg=PANEL_BG,
            fg="#cbd5e1",
            font=(
                "Segoe UI",
                11
            ),
            anchor="w",
            justify="left",
            wraplength=360
        ).pack(
            fill="x",
            pady=(0, 24)
        )


        button_row = tk.Frame(
            content,
            bg=PANEL_BG
        )

        button_row.pack(
            fill="x"
        )

        confirm_color = "#f87171" if danger else BUTTON_OUTLINE


        cancel_button = RoundedButton(
            button_row,
            text=cancel_label,
            command=self._cancel,
            width=150,
            height=44,
            radius=14,
            bg_parent=PANEL_BG,
            fill=BUTTON_BG,
            fill_hover=BUTTON_BG_HOVER,
            outline=BORDER,
            fg="#cbd5e1",
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )

        cancel_button.pack(
            side="left"
        )

        confirm_button = RoundedButton(
            button_row,
            text=confirm_label,
            command=self._confirm,
            width=150,
            height=44,
            radius=14,
            bg_parent=PANEL_BG,
            fill=BUTTON_BG,
            fill_hover=BUTTON_BG_HOVER,
            outline=confirm_color,
            fg=confirm_color,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )

        confirm_button.pack(
            side="right"
        )


        self.bind(
            "<Escape>",
            lambda event: self._cancel()
        )


    def _confirm(self):

        self.result = True

        self._close()


    def _cancel(self):

        self.result = False

        self._close()


    def _close(self):

        try:

            self.grab_release()

        except tk.TclError:

            pass

        try:

            self.destroy()

        except tk.TclError:

            pass


    def show(self):

        self.update_idletasks()


        # Center over the main window rather than the cursor -
        # this is a deliberate "are you sure" prompt, not a
        # context menu, so it should draw the eye to the middle
        # of the app.

        root = self.root_window

        root.update_idletasks()

        width = self.winfo_reqwidth()
        height = self.winfo_reqheight()

        x = (
            root.winfo_rootx()
            +
            (root.winfo_width() - width) // 2
        )

        y = (
            root.winfo_rooty()
            +
            (root.winfo_height() - height) // 2
        )

        self.geometry(
            f"+{x}+{y}"
        )

        self.deiconify()

        self.lift()

        self.focus_force()

        self.grab_set()

        self.wait_window(
            self
        )


        return self.result


def ask_confirm(
        root_window,
        title,
        message,
        confirm_label="Confirm",
        cancel_label="Cancel",
        danger=True
):

    dialog = ConfirmDialog(
        root_window,
        title,
        message,
        confirm_label=confirm_label,
        cancel_label=cancel_label,
        danger=danger
    )

    return dialog.show()


class UpdateGUI:


    def __init__(
            self,
            database,
            refresh_callback,
            show_notes_callback=None
    ):

        self.database = database
        self.refresh_callback = refresh_callback
        self.show_notes_callback = show_notes_callback

        self.root = tk.Tk()

        self.root.title(
            "🎮 Lutris Steam Updates"
        )

        self.root.geometry(
            "1600x900"
        )

        self.root.configure(
            bg=BG
        )

        self.updates = []
        self.new_updates = set()
        self.photo_cache = {}
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
            background=PANEL_BG,
            foreground="#eeeeee",
            fieldbackground=PANEL_BG,
            rowheight=75,
            font=(
                "Segoe UI",
                15
            )
        )


        style.configure(
            "Treeview.Heading",
            background=ACCENT,
            foreground=PANEL_BG_ALT,
            relief="flat",
            borderwidth=0,
            font=(
                "Segoe UI",
                11,
                "bold"
            )
        )

        style.map(
            "Treeview.Heading",
            background=[
                (
                    "active",
                    ACCENT_DIM
                )
            ]
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
            bg=BG
        )

        top.pack(
            fill="x",
            pady=10
        )


        self.refresh_button = RoundedButton(
            top,
            text=" Refresh Updates ",
            command=self.refresh_clicked,
            bg_parent=BG
        )

        self.refresh_button.pack(
            side="left",
            padx=10
        )



        self.search = RoundedEntryFrame(
            top,
            bg_parent=BG,
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
            bg=BG,
            fg=ACCENT,
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

        style.configure(
            "Cyan.Horizontal.TProgressbar",
            troughcolor=PANEL_BG_ALT,   # Background of the bar
            background=ACCENT,          # Cyan fill, matches status/headers
            bordercolor=PANEL_BG_ALT,
            lightcolor=ACCENT,
            darkcolor=ACCENT
        )

        self.progress = ttk.Progressbar(
            self.root,
            mode="determinate",
            style="Cyan.Horizontal.TProgressbar"
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
            bg=BG
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=10,
            pady=10
        )


        tree_container = tk.Frame(
            frame,
            bg=BG
        )

        tree_container.pack(
            side="left",
            fill="both",
            expand=True
        )


        columns = (
            "game",
            "date",
            "description"
        )


        self.tree = ttk.Treeview(
            tree_container,
            columns=columns,
            show=(
                "tree",
                "headings"
            )
        )


        self.tree.heading(
            "#0",
            text="🖼️"
        )


        self.tree.column(
            "#0",
            width=190,
            minwidth=190,
            stretch=False,
            anchor="center"
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


        self.tree.pack(
            side="left",
            fill="both",
            expand=True
        )


        self.tree.tag_configure(
            "even",
            background=PANEL_BG
        )


        self.tree.tag_configure(
            "odd",
            background=PANEL_BG_ALT
        )

        self.tree.tag_configure(
            "new",
            background="#1f6f3d",   # green
            foreground="white"
        )
        self.tree.bind(
            "<Double-1>",
            self.open_selected
        )

        self.tree.bind(
            "<<TreeviewSelect>>",
            self.row_selected
        )

        self.tree.bind(
            "<Button-3>",
            self.show_tree_context_menu
        )



        # -------------------------
        # Details panel (hidden until a row is clicked)
        # -------------------------

        self.details_frame = tk.Frame(
            frame,
            bg=PANEL_BG,
            width=380
        )

        self.details_visible = False


        close_button = tk.Button(
            self.details_frame,
            text="❌",
            command=self.hide_details,
            bg=PANEL_BG,
            fg="#eeeeee",
            activebackground=PANEL_BG,
            activeforeground="#eeeeee",
            bd=0,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            font=(
                "Segoe UI",
                14,
                "bold"
            )
        )
            
        close_button.bind(
            "<Enter>",
            lambda e: close_button.config(
                bg="#2a2d3e"
            )
        )

        close_button.bind(
            "<Leave>",
            lambda e: close_button.config(
                bg=PANEL_BG
            )
        )

        close_button.pack(
            anchor="ne",
            padx=8,
            pady=8
        )


        self.details_image_label = tk.Label(
            self.details_frame,
            bg=PANEL_BG
        )

        self.details_image_label.pack(
            pady=(0, 15)
        )


        self.details_game_label = tk.Label(
            self.details_frame,
            text="",
            bg=PANEL_BG,
            fg="#7dd3fc",
            font=(
                "Segoe UI",
                19,
                "bold"
            ),
            wraplength=340,
            justify="center"
        )

        self.details_game_label.pack(
            padx=15,
            pady=(0, 5)
        )


        self.details_rating_label = tk.Label(
            self.details_frame,
            text="",
            bg=PANEL_BG,
            font=(
                "Segoe UI",
                13,
                "bold"
            ),
            wraplength=340,
            justify="center"
        )

        self.details_rating_label.pack(
            padx=15,
            pady=(0, 10)
        )


        self.details_title_label = tk.Label(
            self.details_frame,
            text="",
            bg=PANEL_BG,
            fg="#eeeeee",
            font=(
                "Segoe UI",
                14,
                "italic"
            ),
            wraplength=340,
            justify="center"
        )

        self.details_title_label.pack(
            padx=15,
            pady=(0, 15)
        )


        notes_frame = tk.Frame(
            self.details_frame,
            bg=PANEL_BG
        )

        notes_frame.pack(
            fill="both",
            expand=True,
            padx=15,
            pady=(0, 15)
        )


        self.details_notes_text = tk.Text(
            notes_frame,
            bg=BG,
            fg="#a7f3d0",
            insertbackground="white",
            wrap="word",
            bd=0,
            relief="flat",
            highlightthickness=0,
            borderwidth=0,
            padx=12,
            pady=10,
            spacing1=2,
            spacing2=4,
            spacing3=10,
            font=(
                "Segoe UI",
                12
            )
        )

        self.details_notes_text.pack(
            side="left",
            fill="both",
            expand=True
        )

        self.details_notes_text.configure(
            state="disabled"
        )


        # Ctrl + mouse wheel zooms the notes text in/out instead
        # of scrolling. <MouseWheel> covers Windows/Mac; Linux
        # (X11) sends wheel events as Button-4 (up) / Button-5
        # (down) instead, so both are bound.

        self.notes_font_family = "Segoe UI"
        self.notes_font_size = 12
        self.notes_font_min = 8
        self.notes_font_max = 28

        self.details_notes_text.bind(
            "<Control-MouseWheel>",
            self._on_notes_ctrl_wheel
        )

        self.details_notes_text.bind(
            "<Control-Button-4>",
            self._on_notes_ctrl_wheel_up
        )

        self.details_notes_text.bind(
            "<Control-Button-5>",
            self._on_notes_ctrl_wheel_down
        )



        # -------------------------
        # Console
        # -------------------------

        self.console = tk.Text(
            self.root,
            height=8,
            bg=PANEL_BG_ALT,
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

        self.new_updates.clear()

        self.log(
            "🚀 Starting update check..."
        )

        self.refresh_callback()


    # ------------------------------------------------
    # Load updates
    # ------------------------------------------------


    def get_photo(
            self,
            appid
    ):

        if not appid:
            return None


        if appid in self.photo_cache:
            return self.photo_cache[appid]


        path = get_local_image_path(
            appid
        )


        if not path:
            return None


        try:

            image = Image.open(
                path
            )

            image.thumbnail(
                (
                    160,
                    60
                )
            )

            photo = ImageTk.PhotoImage(
                image
            )


        except Exception:

            return None



        self.photo_cache[appid] = photo


        return photo



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



            identifier = (
                update["lutris_name"],
                update["title"],
                update["update_date"]
            )

            if identifier in self.new_updates:
                tags = ("new",)
            else:
                tags = (
                    "even",
                ) if count % 2 == 0 else (
                    "odd",
                )

            description = update["description"].strip()

            important = not description.startswith("SteamDB Build")

            if important:
                description = "🚀 " + description
                game_name = "🌟 " + update["lutris_name"] + " 🌟"
            else:
                game_name = update["lutris_name"]
            photo = self.get_photo(
                update["steam_appid"]
            )

            self.tree.insert(
                "",
                "end",
                iid=str(index),
                tags=tags,
                image=photo if photo else "",
                values=(
                    game_name,
                    self.format_date(update["update_date"]),
                    description
                )
            )


            count += 1



        self.status.config(
            text=f"🌱 {count} updates found"
        )



    # ------------------------------------------------
    # Right-click menu / hiding a game
    # ------------------------------------------------

    def show_tree_context_menu(
            self,
            event
    ):

        row_id = self.tree.identify_row(
            event.y
        )

        if not row_id:
            return


        # Right-clicking a row should also select it, so it's
        # obvious which game the menu is about to act on.

        self.tree.selection_set(
            row_id
        )


        update = self.updates[
            int(row_id)
        ]


        menu = ContextMenu(
            self.root,
            items=[
                (
                    f"🚫 Hide \"{update['lutris_name']}\"",
                    lambda: self.hide_game(update),
                    True
                )
            ]
        )

        menu.show(
            event.x_root,
            event.y_root
        )


    def hide_game(
            self,
            update
    ):

        game_name = update["lutris_name"]


        confirmed = ask_confirm(
            self.root,
            title="Hide game",
            message=(
                f"Hide \"{game_name}\"?\n\n"
                "This removes all its saved updates and stops "
                "checking it for new ones on future refreshes. "
                "This can't be undone from here."
            ),
            confirm_label="🚫 Hide",
            cancel_label="Cancel",
            danger=True
        )

        if not confirmed:
            return


        self.database.hide_game(
            update["game_id"]
        )


        # Drop any pending "new update" flags for this game too,
        # since its rows no longer exist.

        self.new_updates = {
            identifier
            for identifier in self.new_updates
            if identifier[0] != game_name
        }


        self.hide_details()

        self.load_updates()

        self.log(
            f"🚫 Hid \"{game_name}\" - it won't be checked again"
        )



    # ------------------------------------------------
    # Open SteamDB
    # ------------------------------------------------

    def row_selected(
            self,
            event
    ):

        selected = self.tree.selection()

        if not selected:
            return


        update = self.updates[
            int(selected[0])
        ]


        self.show_details(
            update
        )


        if self.show_notes_callback:

            self.show_notes_callback(
                update
            )



    # ------------------------------------------------
    # Notes text zoom (Ctrl + mouse wheel)
    # ------------------------------------------------

    def _set_notes_font_size(
            self,
            size
    ):

        size = max(
            self.notes_font_min,
            min(
                self.notes_font_max,
                size
            )
        )

        if size == self.notes_font_size:
            return


        self.notes_font_size = size

        self.details_notes_text.configure(
            font=(
                self.notes_font_family,
                self.notes_font_size
            )
        )


    def _on_notes_ctrl_wheel(
            self,
            event
    ):

        # Windows/Mac: event.delta is +/-120 per notch.

        if event.delta > 0:

            self._set_notes_font_size(
                self.notes_font_size + 1
            )

        else:

            self._set_notes_font_size(
                self.notes_font_size - 1
            )


        return "break"


    def _on_notes_ctrl_wheel_up(
            self,
            event
    ):

        # Linux (X11): scroll-up arrives as Button-4.

        self._set_notes_font_size(
            self.notes_font_size + 1
        )

        return "break"


    def _on_notes_ctrl_wheel_down(
            self,
            event
    ):

        # Linux (X11): scroll-down arrives as Button-5.

        self._set_notes_font_size(
            self.notes_font_size - 1
        )

        return "break"



    # ------------------------------------------------
    # Details panel
    # ------------------------------------------------

    def show_details(
            self,
            update
    ):

        self.details_game_label.config(
            text=update["lutris_name"]
        )


        rating_text = update["steam_rating_text"]
        rating_percent = update["steam_rating_percent"]


        if rating_text and rating_percent is not None:

            if rating_percent >= 70:
                rating_color = "#22c55e"
            elif rating_percent >= 40:
                rating_color = "#f59e0b"
            else:
                rating_color = "#ef4444"


            self.details_rating_label.config(
                text=f"👍 {rating_text} ({rating_percent}%)",
                fg=rating_color
            )

        else:

            self.details_rating_label.config(
                text="",
                fg=PANEL_BG
            )


        self.details_title_label.config(
            text=update["title"]
        )


        notes = (
            update["notes"]
            or
            update["description"]
            or
            "No notes available."
        )

        self.details_notes_text.configure(
            state="normal"
        )

        self.details_notes_text.delete(
            "1.0",
            "end"
        )


        # Keep references alive so PhotoImage objects don't get
        # garbage-collected the moment this function returns.
        self.details_note_images = []


        for line in notes.splitlines():

            match = NOTE_IMAGE_LINE.match(
                line.strip()
            )


            if match:

                image_url = match.group(1)

                image_path = get_local_note_image_path(
                    image_url
                )


                if image_path:

                    try:

                        note_image = Image.open(
                            image_path
                        )

                        note_image.thumbnail(
                            (
                                340,
                                220
                            )
                        )

                        note_photo = ImageTk.PhotoImage(
                            note_image
                        )

                        self.details_note_images.append(
                            note_photo
                        )

                        self.details_notes_text.image_create(
                            "end",
                            image=note_photo
                        )

                        self.details_notes_text.insert(
                            "end",
                            "\n"
                        )

                    except Exception:

                        pass


                # Not cached locally yet (e.g. notes saved before
                # this feature, or not refreshed since) - just
                # skip the line rather than showing raw markup.

                continue


            self.details_notes_text.insert(
                "end",
                line + "\n"
            )


        self.details_notes_text.configure(
            state="disabled"
        )


        appid = update["steam_appid"]

        path = get_local_image_path(
            appid
        ) if appid else None


        if path:

            try:

                image = Image.open(
                    path
                )

                image.thumbnail(
                    (
                        340,
                        160
                    )
                )

                self.details_photo = ImageTk.PhotoImage(
                    image
                )

                self.details_image_label.config(
                    image=self.details_photo
                )

            except Exception:

                self.details_image_label.config(
                    image=""
                )

        else:

            self.details_image_label.config(
                image=""
            )


        if not self.details_visible:

            self.details_frame.pack(
                side="right",
                fill="y",
                padx=(10, 0)
            )

            self.details_frame.pack_propagate(
                False
            )

            self.details_visible = True



    def hide_details(self):

        self.details_frame.pack_forget()

        self.details_visible = False



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

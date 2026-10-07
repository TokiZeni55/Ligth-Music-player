import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
import ctypes
import json
import random
import os


# ============================================================
# SETTINGS
# ============================================================

APP_NAME = "LitePlayer"

DATA_DIR = Path.home() / ".liteplayer"
DATA_FILE = DATA_DIR / "data.json"

SUPPORTED = {".mp3", ".wav"}

DATA_DIR.mkdir(exist_ok=True)


# ============================================================
# WINDOWS MCI AUDIO ENGINE
# ============================================================

class AudioEngine:

    def __init__(self):
        self.alias = "LitePlayerAudio"
        self.current_file = None
        self.is_open = False

        self.mci = ctypes.windll.winmm.mciSendStringW

    def command(self, command):
        buffer = ctypes.create_unicode_buffer(256)

        result = self.mci(
            command,
            buffer,
            256,
            0
        )

        return result, buffer.value

    def close(self):
        if self.is_open:
            self.command(f"close {self.alias}")

        self.is_open = False
        self.current_file = None

    def open(self, filepath):

        self.close()

        filepath = str(Path(filepath).resolve())
        filepath = filepath.replace('"', '""')

        result, _ = self.command(
            f'open "{filepath}" type mpegvideo alias {self.alias}'
        )

        if result != 0:
            result, _ = self.command(
                f'open "{filepath}" alias {self.alias}'
            )

        if result != 0:
            return False

        self.command(
            f"set {self.alias} time format milliseconds"
        )

        self.is_open = True
        self.current_file = filepath

        return True

    def play(self):
        if self.is_open:
            self.command(f"play {self.alias}")

    def pause(self):
        if self.is_open:
            self.command(f"pause {self.alias}")

    def resume(self):
        if self.is_open:
            self.command(f"resume {self.alias}")

    def stop(self):
        if self.is_open:
            self.command(f"stop {self.alias}")

    def position(self):

        if not self.is_open:
            return 0

        result, value = self.command(
            f"status {self.alias} position"
        )

        try:
            return int(value)
        except:
            return 0

    def length(self):

        if not self.is_open:
            return 0

        result, value = self.command(
            f"status {self.alias} length"
        )

        try:
            return int(value)
        except:
            return 0

    def mode(self):

        if not self.is_open:
            return "stopped"

        result, value = self.command(
            f"status {self.alias} mode"
        )

        return value.lower()

    def volume(self, value):

        if not self.is_open:
            return

        value = max(
            0.0,
            min(
                1.0,
                float(value)
            )
        )

        mci_volume = int(value * 1000)

        self.command(
            f"setaudio {self.alias} volume to {mci_volume}"
        )


# ============================================================
# MAIN APP
# ============================================================

class LitePlayer(ctk.CTk):

    def __init__(self):

        super().__init__()

        self.title("LitePlayer")
        self.geometry("1100x700")
        self.minsize(900, 600)

        self.audio = AudioEngine()

        # ----------------------------
        # Library / Playlists
        # ----------------------------

        self.library = []

        self.playlists = {
            "Favorites": []
        }

        # ----------------------------
        # Playback
        # ----------------------------

        self.current_index = -1
        self.current_file = None

        self.play_queue = []

        self.current_playlist = None

        self.paused = False
        self.shuffle = False
        self.repeat = False

        self.volume_level = 0.8

        self.theme = "dark"

        # ----------------------------
        # Dragging
        # ----------------------------

        self.drag_playlist = None
        self.drag_song = None
        self.drag_handle = None

        # ----------------------------
        # Load saved data
        # ----------------------------

        self.load_data()

        self.setup_theme()
        self.build_ui()

        self.protocol(
            "WM_DELETE_WINDOW",
            self.on_close
        )

        self.after(
            500,
            self.update_player
        )

    # ========================================================
    # THEMES
    # ========================================================

    THEMES = {

        "dark": {
            "bg": "#121212",
            "sidebar": "#181818",
            "panel": "#1E1E1E",
            "hover": "#292929",
            "text": "#FFFFFF",
            "subtext": "#A7A7A7",
            "accent": "#1DB954",
        },

        "light": {
            "bg": "#F5F5F5",
            "sidebar": "#EAEAEA",
            "panel": "#FFFFFF",
            "hover": "#DDDDDD",
            "text": "#111111",
            "subtext": "#555555",
            "accent": "#16A34A",
        },

        "neon": {
            "bg": "#080812",
            "sidebar": "#0D0D1A",
            "panel": "#111122",
            "hover": "#202044",
            "text": "#FFFFFF",
            "subtext": "#9D9DB8",
            "accent": "#00E5FF",
        },

        "thunder": {
            "bg": "#080D18",
            "sidebar": "#0D1422",
            "panel": "#121C2E",
            "hover": "#1D2B42",
            "text": "#FFFFFF",
            "subtext": "#9AA8BD",
            "accent": "#FFD21F",
        }
    }

    def setup_theme(self):

        t = self.THEMES[self.theme]

        ctk.set_appearance_mode(
            "Dark" if self.theme != "light" else "Light"
        )

        ctk.set_default_color_theme("green")

        self.configure(
            fg_color=t["bg"]
        )

    def colors(self):
        return self.THEMES[self.theme]

    # ========================================================
    # DATA
    # ========================================================

    def load_data(self):

        if not DATA_FILE.exists():
            return

        try:

            with open(
                DATA_FILE,
                "r",
                encoding="utf-8"
            ) as f:

                data = json.load(f)

            self.library = data.get(
                "library",
                []
            )

            self.playlists = data.get(
                "playlists",
                {"Favorites": []}
            )

            if "Favorites" not in self.playlists:
                self.playlists["Favorites"] = []

            self.theme = data.get(
                "theme",
                "dark"
            )

            self.volume_level = data.get(
                "volume",
                0.8
            )

            if self.theme not in self.THEMES:
                self.theme = "dark"

        except Exception:

            self.library = []

            self.playlists = {
                "Favorites": []
            }

            self.theme = "dark"
            self.volume_level = 0.8

    def save_data(self):

        data = {
            "library": self.library,
            "playlists": self.playlists,
            "theme": self.theme,
            "volume": self.volume_level
        }

        try:

            with open(
                DATA_FILE,
                "w",
                encoding="utf-8"
            ) as f:

                json.dump(
                    data,
                    f,
                    indent=2
                )

        except Exception:
            pass

    # ========================================================
    # UI
    # ========================================================

    def build_ui(self):

        t = self.colors()

        # ====================================================
        # SIDEBAR
        # ====================================================

        self.sidebar = ctk.CTkFrame(
            self,
            width=210,
            corner_radius=0,
            fg_color=t["sidebar"]
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)


        # ----------------------------------------------------
        # LIBRARY
        # ----------------------------------------------------

        self.library_button = ctk.CTkButton(
            self.sidebar,
            text="🎵  Library",
            anchor="w",
            height=42,
            fg_color="transparent",
            hover_color=t["hover"],
            text_color=t["text"],
            command=self.show_library
        )

        self.library_button.pack(
            fill="x",
            padx=12,
            pady=5
        )

        # ----------------------------------------------------
        # PLAYLISTS
        # ----------------------------------------------------

        self.playlist_button = ctk.CTkButton(
            self.sidebar,
            text="📋  Playlists",
            anchor="w",
            height=42,
            fg_color="transparent",
            hover_color=t["hover"],
            text_color=t["text"],
            command=self.show_playlists
        )

        self.playlist_button.pack(
            fill="x",
            padx=12,
            pady=5
        )

        # ----------------------------------------------------
        # NEW PLAYLIST
        # ----------------------------------------------------

        self.new_playlist_button = ctk.CTkButton(
            self.sidebar,
            text="＋  New Playlist",
            anchor="w",
            height=38,
            fg_color="transparent",
            hover_color=t["hover"],
            text_color=t["text"],
            command=self.create_playlist
        )

        self.new_playlist_button.pack(
            fill="x",
            padx=18,
            pady=(0, 5)
        )

        # ----------------------------------------------------
        # THEME
        # ----------------------------------------------------

        theme_label = ctk.CTkLabel(
            self.sidebar,
            text="THEME",
            text_color=t["subtext"],
            anchor="w"
        )

        theme_label.pack(
            fill="x",
            padx=20,
            pady=(35, 5)
        )

        self.theme_menu = ctk.CTkOptionMenu(
            self.sidebar,
            values=[
                "Dark",
                "Light",
                "Neon",
                "Thunder"
            ],
            command=self.change_theme
        )

        self.theme_menu.set(
            self.theme.title()
        )

        self.theme_menu.pack(
            padx=15,
            fill="x"
        )

        # ====================================================
        # MAIN
        # ====================================================

        self.main = ctk.CTkFrame(
            self,
            fg_color=t["bg"],
            corner_radius=0
        )

        self.main.pack(
            side="left",
            fill="both",
            expand=True
        )

        # ====================================================
        # TOP BAR
        # ====================================================

        self.topbar = ctk.CTkFrame(
            self.main,
            fg_color="transparent"
        )

        self.topbar.pack(
            fill="x",
            padx=25,
            pady=20
        )

        self.search = ctk.CTkEntry(
            self.topbar,
            placeholder_text="Search songs...",
            height=40
        )

        self.search.pack(
            side="left",
            fill="x",
            expand=True,
            padx=(0, 10)
        )

        self.search.bind(
            "<KeyRelease>",
            lambda e: self.refresh_library()
        )

        # ----------------------------------------------------
        # ADD FILES
        # ----------------------------------------------------

        self.add_button = ctk.CTkButton(
            self.topbar,
            text="+ Add Files",
            width=110,
            height=40,
            fg_color=t["accent"],
            command=self.add_files
        )

        self.add_button.pack(
            side="left",
            padx=5
        )

        # ----------------------------------------------------
        # FOLDER
        # ----------------------------------------------------

        self.folder_button = ctk.CTkButton(
            self.topbar,
            text="📁 Folder",
            width=100,
            height=40,
            fg_color=t["panel"],
            hover_color=t["hover"],
            command=self.add_folder
        )

        self.folder_button.pack(
            side="left"
        )

        # ====================================================
        # CONTENT
        # ====================================================

        self.content = ctk.CTkScrollableFrame(
            self.main,
            fg_color="transparent"
        )

        self.content.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=(0, 10)
        )

        # ====================================================
        # PLAYER BAR
        # ====================================================

        self.player_bar = ctk.CTkFrame(
            self.main,
            height=95,
            corner_radius=0,
            fg_color=t["panel"]
        )

        self.player_bar.pack(
            fill="x",
            side="bottom"
        )

        self.player_bar.grid_columnconfigure(
            0,
            weight=1
        )

        self.player_bar.grid_columnconfigure(
            1,
            weight=2
        )

        self.player_bar.grid_columnconfigure(
            2,
            weight=1
        )

        # ----------------------------------------------------
        # CURRENT SONG
        # ----------------------------------------------------

        self.now_playing = ctk.CTkLabel(
            self.player_bar,
            text="Nothing playing",
            anchor="w",
            text_color=t["text"],
            font=ctk.CTkFont(
                size=14,
                weight="bold"
            )
        )

        self.now_playing.grid(
            row=0,
            column=0,
            padx=20,
            pady=(15, 0),
            sticky="ew"
        )

        self.status_label = ctk.CTkLabel(
            self.player_bar,
            text="Ready",
            anchor="w",
            text_color=t["subtext"]
        )

        self.status_label.grid(
            row=1,
            column=0,
            padx=20,
            pady=(0, 15),
            sticky="ew"
        )

        # ----------------------------------------------------
        # CONTROLS
        # ----------------------------------------------------

        self.controls = ctk.CTkFrame(
            self.player_bar,
            fg_color="transparent"
        )

        self.controls.grid(
            row=0,
            column=1,
            rowspan=2,
            pady=10
        )

        self.shuffle_button = ctk.CTkButton(
            self.controls,
            text="🔀",
            width=35,
            fg_color="transparent",
            hover_color=t["hover"],
            command=self.toggle_shuffle
        )

        self.shuffle_button.pack(
            side="left",
            padx=3
        )

        ctk.CTkButton(
            self.controls,
            text="⏮",
            width=40,
            fg_color="transparent",
            hover_color=t["hover"],
            command=self.previous_song
        ).pack(
            side="left",
            padx=3
        )

        self.play_button = ctk.CTkButton(
            self.controls,
            text="▶",
            width=45,
            height=40,
            fg_color=t["accent"],
            command=self.toggle_play
        )

        self.play_button.pack(
            side="left",
            padx=5
        )

        ctk.CTkButton(
            self.controls,
            text="⏭",
            width=40,
            fg_color="transparent",
            hover_color=t["hover"],
            command=self.next_song
        ).pack(
            side="left",
            padx=3
        )

        self.repeat_button = ctk.CTkButton(
            self.controls,
            text="🔁",
            width=35,
            fg_color="transparent",
            hover_color=t["hover"],
            command=self.toggle_repeat
        )

        self.repeat_button.pack(
            side="left",
            padx=3
        )

        # ----------------------------------------------------
        # VOLUME
        # ----------------------------------------------------

        self.volume = ctk.CTkSlider(
            self.player_bar,
            from_=0,
            to=1,
            command=self.change_volume
        )

        self.volume.grid(
            row=0,
            column=2,
            padx=25,
            pady=(15, 0),
            sticky="ew"
        )

        self.volume.set(
            max(
                0,
                min(
                    1,
                    float(self.volume_level)
                )
            )
        )

        ctk.CTkLabel(
            self.player_bar,
            text="Volume",
            text_color=t["subtext"]
        ).grid(
            row=1,
            column=2,
            padx=25,
            pady=(0, 15),
            sticky="e"
        )

        self.refresh_library()

    # ========================================================
    # LIBRARY
    # ========================================================

    def refresh_library(self):

        for widget in self.content.winfo_children():
            widget.destroy()

        query = self.search.get().lower().strip()

        songs = []

        for path in self.library:

            if not os.path.exists(path):
                continue

            name = Path(path).stem

            if query and query not in name.lower():
                continue

            songs.append(path)

        t = self.colors()

        if not songs:

            label = ctk.CTkLabel(
                self.content,
                text="Your library is empty\n\nClick '+ Add Files' or '📁 Folder'",
                text_color=t["subtext"],
                font=ctk.CTkFont(
                    size=17
                )
            )

            label.pack(
                pady=100
            )

            return

        for index, path in enumerate(songs):

            self.create_song_row(
                path,
                index
            )

    def create_song_row(
        self,
        path,
        display_index
    ):

        t = self.colors()

        row = ctk.CTkFrame(
            self.content,
            fg_color=t["panel"],
            height=55
        )

        row.pack(
            fill="x",
            pady=3
        )

        row.grid_columnconfigure(
            0,
            weight=1
        )

        name = Path(path).stem

        label = ctk.CTkLabel(
            row,
            text=f"  {name}",
            anchor="w",
            text_color=t["text"],
            font=ctk.CTkFont(
                size=14
            )
        )

        label.grid(
            row=0,
            column=0,
            padx=10,
            sticky="ew"
        )

        # ----------------------------------------------------
        # PLAY
        # ----------------------------------------------------

        play = ctk.CTkButton(
            row,
            text="▶",
            width=45,
            fg_color="transparent",
            hover_color=t["hover"],
            command=lambda p=path: self.play_file(p)
        )

        play.grid(
            row=0,
            column=1,
            padx=3
        )

        # ----------------------------------------------------
        # FAVORITE
        # ----------------------------------------------------

        is_favorite = (
            path in self.playlists.get(
                "Favorites",
                []
            )
        )

        fav = ctk.CTkButton(
            row,
            text="★" if is_favorite else "☆",
            width=40,
            fg_color="transparent",
            hover_color=t["hover"],
            text_color=(
                "#FFD21F"
                if is_favorite
                else t["text"]
            ),
            command=lambda p=path:
                self.add_favorite(p)
        )

        fav.grid(
            row=0,
            column=2,
            padx=3
        )

        # ----------------------------------------------------
        # ADD TO PLAYLIST
        # ----------------------------------------------------

        playlist = ctk.CTkButton(
            row,
            text="＋",
            width=40,
            fg_color="transparent",
            hover_color=t["hover"],
            command=lambda p=path:
                self.add_to_playlist(p)
        )

        playlist.grid(
            row=0,
            column=3,
            padx=5
        )

    # ========================================================
    # ADD FILES
    # ========================================================

    def add_files(self):

        files = filedialog.askopenfilenames(
            title="Add Music",
            filetypes=[
                (
                    "Audio files",
                    "*.mp3 *.wav"
                ),
                (
                    "MP3",
                    "*.mp3"
                ),
                (
                    "WAV",
                    "*.wav"
                )
            ]
        )

        added = 0

        for file in files:

            file = str(
                Path(file).resolve()
            )

            if file not in self.library:

                self.library.append(file)

                added += 1

        if added:

            self.save_data()
            self.refresh_library()

    def add_folder(self):

        folder = filedialog.askdirectory(
            title="Select Music Folder"
        )

        if not folder:
            return

        added = 0

        for root, dirs, files in os.walk(folder):

            for filename in files:

                extension = Path(
                    filename
                ).suffix.lower()

                if extension not in SUPPORTED:
                    continue

                path = str(
                    Path(root) / filename
                )

                path = str(
                    Path(path).resolve()
                )

                if path not in self.library:

                    self.library.append(path)

                    added += 1

        if added:

            self.save_data()
            self.refresh_library()

    # ========================================================
    # PLAYBACK
    # ========================================================

    def play_file(
        self,
        path,
        queue=None,
        queue_index=None
    ):

        if not os.path.exists(path):

            messagebox.showerror(
                "File not found",
                path
            )

            return

        if not self.audio.open(path):

            messagebox.showerror(
                "Playback error",
                "Windows could not open this audio file."
            )

            return

        if queue is not None:

            self.play_queue = list(queue)

            if queue_index is not None:
                self.current_index = queue_index

            elif path in self.play_queue:
                self.current_index = self.play_queue.index(path)

            else:
                self.current_index = 0

        else:

            if (
                self.current_playlist
                and self.current_playlist in self.playlists
            ):

                self.play_queue = list(
                    self.playlists[self.current_playlist]
                )

            else:

                self.play_queue = list(
                    self.library
                )

            if path in self.play_queue:
                self.current_index = self.play_queue.index(path)

            else:
                self.current_index = -1

        self.audio.volume(
            self.volume_level
        )

        self.audio.play()

        self.current_file = path

        self.paused = False

        self.now_playing.configure(
            text=Path(path).stem
        )

        self.play_button.configure(
            text="⏸"
        )

        self.status_label.configure(
            text="Playing"
        )

    def play_playlist_song(
        self,
        playlist,
        path
    ):

        if playlist not in self.playlists:
            return

        songs = self.playlists[playlist]

        if path not in songs:
            return

        index = songs.index(path)

        self.current_playlist = playlist

        self.play_file(
            path,
            queue=songs,
            queue_index=index
        )

    def toggle_play(self):

        if not self.current_file:

            if self.play_queue:

                self.play_file(
                    self.play_queue[0]
                )

            elif self.library:

                self.current_playlist = None

                self.play_file(
                    self.library[0],
                    queue=self.library,
                    queue_index=0
                )

            return

        if self.paused:

            self.audio.resume()

            self.paused = False

            self.play_button.configure(
                text="⏸"
            )

            self.status_label.configure(
                text="Playing"
            )

        else:

            self.audio.pause()

            self.paused = True

            self.play_button.configure(
                text="▶"
            )

            self.status_label.configure(
                text="Paused"
            )

    def next_song(self):

        if not self.play_queue:

            if self.library:
                self.play_queue = list(self.library)
            else:
                return

        if self.shuffle:

            if len(self.play_queue) == 1:

                index = 0

            else:

                choices = list(
                    range(len(self.play_queue))
                )

                if self.current_index in choices:
                    choices.remove(
                        self.current_index
                    )

                index = random.choice(
                    choices
                )

        else:

            index = self.current_index + 1

            if index >= len(self.play_queue):

                if self.repeat:

                    index = 0

                else:

                    self.audio.stop()

                    self.play_button.configure(
                        text="▶"
                    )

                    self.status_label.configure(
                        text="Finished"
                    )

                    return

        path = self.play_queue[index]

        if not os.path.exists(path):

            self.play_queue.pop(index)

            if self.play_queue:
                self.next_song()

            return

        self.play_file(
            path,
            queue=self.play_queue,
            queue_index=index
        )

    def previous_song(self):

        if not self.play_queue:
            return

        index = self.current_index - 1

        if index < 0:
            index = len(self.play_queue) - 1

        path = self.play_queue[index]

        self.play_file(
            path,
            queue=self.play_queue,
            queue_index=index
        )

    # ========================================================
    # CONTROLS
    # ========================================================

    def toggle_shuffle(self):

        self.shuffle = not self.shuffle

        t = self.colors()

        self.shuffle_button.configure(
            text_color=(
                t["accent"]
                if self.shuffle
                else t["text"]
            )
        )

    def toggle_repeat(self):

        self.repeat = not self.repeat

        t = self.colors()

        self.repeat_button.configure(
            text_color=(
                t["accent"]
                if self.repeat
                else t["text"]
            )
        )

    def change_volume(self, value):

        try:
            value = float(value)

        except:
            value = 0.8

        value = max(
            0,
            min(
                1,
                value
            )
        )

        self.volume_level = value

        self.audio.volume(
            value
        )

        self.save_data()

    # ========================================================
    # FAVORITES
    # ========================================================

    def add_favorite(self, path):

        if "Favorites" not in self.playlists:
            self.playlists["Favorites"] = []

        if path in self.playlists["Favorites"]:

            self.playlists["Favorites"].remove(
                path
            )

            favorite_state = False

        else:

            self.playlists["Favorites"].append(
                path
            )

            favorite_state = True

        self.save_data()

        # Immediately update the library so
        # the star changes without restarting.

        self.refresh_library()

        self.status_label.configure(
            text=(
                "Added to Favorites"
                if favorite_state
                else "Removed from Favorites"
            )
        )

    # ========================================================
    # CREATE PLAYLIST
    # ========================================================

    def create_playlist(self):

        dialog = ctk.CTkInputDialog(
            text="Enter playlist name:",
            title="New Playlist"
        )

        name = dialog.get_input()

        if not name:
            return

        name = name.strip()

        if not name:
            return

        if name in self.playlists:

            messagebox.showwarning(
                "Playlist already exists",
                f"A playlist named '{name}' already exists."
            )

            return

        self.playlists[name] = []

        self.save_data()

        self.current_playlist = name

        self.show_playlists()

    # ========================================================
    # DELETE PLAYLIST
    # ========================================================

    def delete_playlist(self, playlist):

        if playlist == "Favorites":

            messagebox.showinfo(
                "Cannot delete Favorites",
                "The Favorites playlist cannot be deleted."
            )

            return

        confirm = messagebox.askyesno(
            "Delete Playlist",
            f"Delete playlist '{playlist}'?"
        )

        if not confirm:
            return

        if playlist in self.playlists:

            del self.playlists[playlist]

        if self.current_playlist == playlist:

            self.current_playlist = None
            self.play_queue = []

        self.save_data()

        self.show_playlists()

    # ========================================================
    # ADD SONG TO PLAYLIST
    # ========================================================

    def add_to_playlist(self, path):

        playlists = list(
            self.playlists.keys()
        )

        dialog = ctk.CTkToplevel(self)

        dialog.title("Add to Playlist")
        dialog.geometry("380x430")
        dialog.resizable(False, False)

        t = self.colors()

        dialog.configure(
            fg_color=t["bg"]
        )

        ctk.CTkLabel(
            dialog,
            text="Add to Playlist",
            font=ctk.CTkFont(
                size=20,
                weight="bold"
            ),
            text_color=t["text"]
        ).pack(
            pady=(20, 8)
        )

        ctk.CTkLabel(
            dialog,
            text=Path(path).stem,
            text_color=t["subtext"],
            wraplength=320
        ).pack(
            pady=(0, 15)
        )

        playlist_frame = ctk.CTkScrollableFrame(
            dialog,
            fg_color="transparent"
        )

        playlist_frame.pack(
            fill="both",
            expand=True,
            padx=15
        )

        for playlist in playlists:

            already = (
                path in self.playlists[playlist]
            )

            button = ctk.CTkButton(
                playlist_frame,
                text=(
                    f"✓  {playlist}"
                    if already
                    else f"📋  {playlist}"
                ),
                anchor="w",
                height=40,
                fg_color=(
                    t["hover"]
                    if already
                    else t["panel"]
                ),
                hover_color=t["hover"],
                text_color=t["text"],
                command=lambda p=playlist:
                    self.put_song_in_playlist(
                        path,
                        p,
                        dialog
                    )
            )

            button.pack(
                fill="x",
                pady=3
            )

        ctk.CTkButton(
            dialog,
            text="＋ Create New Playlist",
            height=40,
            fg_color=t["accent"],
            command=lambda:
                self.create_playlist_from_song_dialog(
                    path,
                    dialog
                )
        ).pack(
            fill="x",
            padx=25,
            pady=15
        )

    def put_song_in_playlist(
        self,
        path,
        playlist,
        dialog
    ):

        if playlist not in self.playlists:
            return

        if path not in self.playlists[playlist]:

            self.playlists[playlist].append(
                path
            )

            self.save_data()

            dialog.destroy()

            self.status_label.configure(
                text=f"Added to {playlist}"
            )

        else:

            messagebox.showinfo(
                "Already added",
                f"This song is already in '{playlist}'."
            )

    def create_playlist_from_song_dialog(
        self,
        path,
        dialog
    ):

        dialog.destroy()

        new_dialog = ctk.CTkInputDialog(
            text="Enter playlist name:",
            title="New Playlist"
        )

        name = new_dialog.get_input()

        if not name:
            return

        name = name.strip()

        if not name:
            return

        if name in self.playlists:

            messagebox.showwarning(
                "Playlist already exists",
                f"A playlist named '{name}' already exists."
            )

            return

        self.playlists[name] = [
            path
        ]

        self.save_data()

        self.current_playlist = name

        self.show_playlists()

    # ========================================================
    # PLAYLIST VIEW
    # ========================================================

    def show_playlists(self):

        for widget in self.content.winfo_children():
            widget.destroy()

        t = self.colors()

        title_frame = ctk.CTkFrame(
            self.content,
            fg_color="transparent"
        )

        title_frame.pack(
            fill="x",
            padx=10,
            pady=15
        )

        ctk.CTkLabel(
            title_frame,
            text="Playlists",
            font=ctk.CTkFont(
                size=24,
                weight="bold"
            ),
            text_color=t["text"]
        ).pack(
            side="left"
        )

        ctk.CTkButton(
            title_frame,
            text="＋ New Playlist",
            width=130,
            fg_color=t["accent"],
            command=self.create_playlist
        ).pack(
            side="right"
        )

        for playlist, songs in self.playlists.items():

            self.create_playlist_section(
                playlist,
                songs
            )

    def create_playlist_section(
        self,
        playlist,
        songs
    ):

        t = self.colors()

        frame = ctk.CTkFrame(
            self.content,
            fg_color=t["panel"]
        )

        frame.pack(
            fill="x",
            pady=7
        )

        header = ctk.CTkFrame(
            frame,
            fg_color="transparent"
        )

        header.pack(
            fill="x",
            padx=10,
            pady=8
        )

        ctk.CTkLabel(
            header,
            text=f"📋 {playlist}",
            font=ctk.CTkFont(
                size=17,
                weight="bold"
            ),
            text_color=t["text"]
        ).pack(
            side="left"
        )

        ctk.CTkLabel(
            header,
            text=f"{len(songs)} songs",
            text_color=t["subtext"]
        ).pack(
            side="left",
            padx=10
        )

        if songs:

            ctk.CTkButton(
                header,
                text="▶ Play",
                width=75,
                height=30,
                fg_color=t["accent"],
                command=lambda p=playlist:
                    self.play_playlist(p)
            ).pack(
                side="right",
                padx=4
            )

        if playlist != "Favorites":

            ctk.CTkButton(
                header,
                text="🗑",
                width=35,
                height=30,
                fg_color="transparent",
                hover_color=t["hover"],
                text_color=t["text"],
                command=lambda p=playlist:
                    self.delete_playlist(p)
            ).pack(
                side="right"
            )

        if songs:

            ctk.CTkLabel(
                frame,
                text="☰ Drag songs to change their order",
                text_color=t["subtext"],
                font=ctk.CTkFont(
                    size=11
                )
            ).pack(
                anchor="w",
                padx=18,
                pady=(0, 5)
            )

        for index, song in enumerate(songs):

            self.create_playlist_song_row(
                frame,
                playlist,
                song,
                index
            )

        if not songs:

            ctk.CTkLabel(
                frame,
                text="No songs yet\nUse ＋ beside a song to add one",
                text_color=t["subtext"]
            ).pack(
                pady=(5, 15)
            )

    def create_playlist_song_row(
        self,
        parent,
        playlist,
        song,
        index
    ):

        t = self.colors()

        row = ctk.CTkFrame(
            parent,
            fg_color=t["bg"],
            height=48
        )

        row.pack(
            fill="x",
            padx=10,
            pady=2
        )

        row.grid_columnconfigure(
            1,
            weight=1
        )

        # ----------------------------------------------------
        # DRAG HANDLE
        # ----------------------------------------------------

        handle = ctk.CTkLabel(
            row,
            text="☰",
            width=35,
            text_color=t["subtext"],
            cursor="hand2"
        )

        handle.grid(
            row=0,
            column=0,
            padx=(5, 0)
        )

        handle.bind(
            "<Button-1>",
            lambda event,
            p=playlist,
            s=song:
                self.start_playlist_drag(
                    event,
                    p,
                    s
                )
        )

        handle.bind(
            "<B1-Motion>",
            lambda event:
                self.move_playlist_drag(event)
        )

        handle.bind(
            "<ButtonRelease-1>",
            lambda event:
                self.finish_playlist_drag(event)
        )

        # ----------------------------------------------------
        # SONG NAME
        # ----------------------------------------------------

        if os.path.exists(song):

            song_name = Path(song).stem

        else:

            song_name = (
                Path(song).stem
                + " [missing]"
            )

        label = ctk.CTkLabel(
            row,
            text=song_name,
            anchor="w",
            text_color=t["text"]
        )

        label.grid(
            row=0,
            column=1,
            sticky="ew",
            padx=5
        )

        # ----------------------------------------------------
        # PLAY
        # ----------------------------------------------------

        ctk.CTkButton(
            row,
            text="▶",
            width=38,
            fg_color="transparent",
            hover_color=t["hover"],
            command=lambda p=playlist, s=song:
                self.play_playlist_song(
                    p,
                    s
                )
        ).grid(
            row=0,
            column=2,
            padx=2
        )

        # ----------------------------------------------------
        # REMOVE
        # ----------------------------------------------------

        ctk.CTkButton(
            row,
            text="✕",
            width=38,
            fg_color="transparent",
            hover_color=t["hover"],
            command=lambda p=playlist, s=song:
                self.remove_from_playlist(
                    p,
                    s
                )
        ).grid(
            row=0,
            column=3,
            padx=4
        )

    # ========================================================
    # PLAY PLAYLIST
    # ========================================================

    def play_playlist(self, playlist):

        if playlist not in self.playlists:
            return

        songs = [
            song
            for song in self.playlists[playlist]
            if os.path.exists(song)
        ]

        if not songs:

            messagebox.showinfo(
                "Empty Playlist",
                "This playlist has no playable songs."
            )

            return

        self.current_playlist = playlist

        self.play_queue = list(
            self.playlists[playlist]
        )

        first_index = -1

        for i, song in enumerate(
            self.play_queue
        ):

            if os.path.exists(song):

                first_index = i
                break

        if first_index == -1:
            return

        self.play_file(
            self.play_queue[first_index],
            queue=self.play_queue,
            queue_index=first_index
        )

    # ========================================================
    # REMOVE SONG FROM PLAYLIST
    # ========================================================

    def remove_from_playlist(
        self,
        playlist,
        song
    ):

        if playlist not in self.playlists:
            return

        if song not in self.playlists[playlist]:
            return

        self.playlists[playlist].remove(
            song
        )

        if self.current_playlist == playlist:

            self.play_queue = list(
                self.playlists[playlist]
            )

            if self.current_file == song:

                self.audio.stop()

                self.current_file = None
                self.current_index = -1

                self.play_button.configure(
                    text="▶"
                )

                self.now_playing.configure(
                    text="Nothing playing"
                )

        self.save_data()

        self.show_playlists()

    # ========================================================
    # DRAG AND DROP PLAYLIST ORDER
    # ========================================================

    def start_playlist_drag(
        self,
        event,
        playlist,
        song
    ):

        self.drag_playlist = playlist
        self.drag_song = song

        self.drag_handle = event.widget

        try:
            self.drag_handle.configure(
                text="⬍"
            )
        except:
            pass

    def move_playlist_drag(self, event):

        if not self.drag_playlist:
            return

        try:

            x = event.x_root
            y = event.y_root

            target_widget = self.winfo_containing(
                x,
                y
            )

            if target_widget is None:
                return

            target_row = target_widget

            while (
                target_row is not None
                and not isinstance(
                    target_row,
                    ctk.CTkFrame
                )
            ):

                target_row = target_row.master

            if target_row is None:
                return

        except:
            return

    def finish_playlist_drag(self, event):

        if not self.drag_playlist:
            return

        playlist = self.drag_playlist
        song = self.drag_song

        self.drag_playlist = None
        self.drag_song = None

        if self.drag_handle:

            try:
                self.drag_handle.configure(
                    text="☰"
                )
            except:
                pass

        self.drag_handle = None

        if playlist not in self.playlists:
            return

        songs = self.playlists[playlist]

        if song not in songs:
            return

        mouse_y = event.y_root

        target_index = None

        playlist_frame = self.find_playlist_frame(
            playlist
        )

        if playlist_frame is None:
            return

        rows = []

        for child in playlist_frame.winfo_children():

            if not isinstance(
                child,
                ctk.CTkFrame
            ):
                continue

            has_handle = False

            for sub in child.winfo_children():

                if isinstance(
                    sub,
                    ctk.CTkLabel
                ):

                    try:

                        if sub.cget("text") in (
                            "☰",
                            "⬍"
                        ):

                            has_handle = True
                            break

                    except:
                        pass

            if has_handle:
                rows.append(child)

        if not rows:
            return

        best_distance = None
        best_index = None

        for i, row in enumerate(rows):

            top = row.winfo_rooty()
            bottom = top + row.winfo_height()

            center = (
                top + bottom
            ) / 2

            distance = abs(
                mouse_y - center
            )

            if (
                best_distance is None
                or distance < best_distance
            ):

                best_distance = distance
                best_index = i

        if best_index is None:
            return

        old_index = songs.index(song)

        if old_index == best_index:
            return

        songs.pop(old_index)

        songs.insert(
            best_index,
            song
        )

        self.playlists[playlist] = songs

        if self.current_playlist == playlist:

            current_song = self.current_file

            self.play_queue = list(
                songs
            )

            if current_song in self.play_queue:

                self.current_index = (
                    self.play_queue.index(
                        current_song
                    )
                )

        self.save_data()

        self.show_playlists()

    def find_playlist_frame(self, playlist):

        for widget in self.content.winfo_children():

            if not isinstance(
                widget,
                ctk.CTkFrame
            ):
                continue

            for child in widget.winfo_children():

                if not isinstance(
                    child,
                    ctk.CTkFrame
                ):
                    continue

                for sub in child.winfo_children():

                    if isinstance(
                        sub,
                        ctk.CTkLabel
                    ):

                        try:

                            text = sub.cget(
                                "text"
                            )

                            if text == f"📋 {playlist}":
                                return widget

                        except:
                            pass

        return None

    # ========================================================
    # LIBRARY
    # ========================================================

    def show_library(self):

        self.current_playlist = None

        self.search.delete(
            0,
            "end"
        )

        self.refresh_library()

    # ========================================================
    # THEMES
    # ========================================================

    def change_theme(self, value):

        mapping = {
            "Dark": "dark",
            "Light": "light",
            "Neon": "neon",
            "Thunder": "thunder"
        }

        self.theme = mapping.get(
            value,
            "dark"
        )

        self.save_data()

        for widget in self.winfo_children():
            widget.destroy()

        self.setup_theme()
        self.build_ui()

    # ========================================================
    # PLAYER UPDATE
    # ========================================================

    def update_player(self):

        if (
            self.current_file
            and self.audio.is_open
        ):

            position = self.audio.position()
            length = self.audio.length()

            if length > 0:

                current = self.format_time(
                    position
                )

                total = self.format_time(
                    length
                )

                self.status_label.configure(
                    text=f"{current} / {total}"
                )

            mode = self.audio.mode()

            if (
                mode == "stopped"
                and not self.paused
            ):

                if self.repeat:

                    self.play_file(
                        self.current_file,
                        queue=self.play_queue,
                        queue_index=self.current_index
                    )

                else:

                    self.next_song()

        self.after(
            500,
            self.update_player
        )

    @staticmethod
    def format_time(milliseconds):

        seconds = max(
            0,
            int(milliseconds / 1000)
        )

        minutes = seconds // 60

        seconds %= 60

        return f"{minutes}:{seconds:02d}"

    # ========================================================
    # CLOSE
    # ========================================================

    def on_close(self):

        self.save_data()

        self.audio.close()

        self.destroy()


# ============================================================
# START
# ============================================================

if __name__ == "__main__":

    app = LitePlayer()

    app.mainloop()
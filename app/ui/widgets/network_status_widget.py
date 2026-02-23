from __future__ import annotations

import datetime
import os
import pathlib
import tkinter as tk

from PIL import Image, ImageTk


class NetworkStatusWidget:
    """Global network indicator widget, independent from screen implementations."""

    def __init__(self, main_app, root, icon_size):
        self.main_app = main_app
        self.root = root
        project_root = pathlib.Path(__file__).resolve().parents[3]
        image_path = os.fspath(project_root / "images" / "buttons" / "no-wifi-white.png")
        banner_icon_size = (14, 14)
        image = Image.open(image_path).convert("RGBA").resize(banner_icon_size, Image.LANCZOS)
        alpha = image.split()[-1]
        black_icon = Image.new("RGBA", image.size, (0, 0, 0, 255))
        black_icon.putalpha(alpha)
        self.icon = ImageTk.PhotoImage(black_icon)

        self.banner_bg = "#f4c542"
        self.row_height = 35
        self.row_gap = 0
        screen_width = int(getattr(self.main_app.settings, "screen_width", 720) or 720)
        self.row_width = max(200, min(screen_width - 200, 300))
        self.issue_first_seen: dict[str, str] = {}
        self.issue_rows: dict[str, tk.Frame] = {}
        self.visible = False

    def set_disconnected_connections(self, disconnected: list[str]) -> None:
        if not disconnected:
            self.hide()
            return
        self.show(disconnected)

    def show(self, disconnected: list[str]) -> None:
        # Keep per-connection first-seen timestamps stable until recovered.
        now_text = datetime.datetime.now().strftime("%d-%m %H:%M")
        active = []
        for connection in disconnected:
            connection_key = str(connection).strip()
            if not connection_key:
                continue
            active.append(connection_key)
            if connection_key not in self.issue_first_seen:
                self.issue_first_seen[connection_key] = now_text

        # Remove recovered connections.
        recovered = [key for key in self.issue_rows.keys() if key not in active]
        for key in recovered:
            row = self.issue_rows.pop(key, None)
            if row is not None:
                row.destroy()
            self.issue_first_seen.pop(key, None)

        for index, connection in enumerate(active):
            row = self.issue_rows.get(connection)
            if row is None:
                row = self._create_issue_row(connection)
                self.issue_rows[connection] = row
            row.place(
                relx=0.5,
                y=index * (self.row_height + self.row_gap),
                anchor="n",
                width=self.row_width,
                height=self.row_height,
            )
            row.lift()

        self.visible = True

    def hide(self) -> None:
        if not self.visible:
            return
        for row in self.issue_rows.values():
            row.place_forget()
            row.destroy()
        self.issue_rows.clear()
        self.issue_first_seen.clear()
        self.visible = False

    def _create_issue_row(self, connection: str) -> tk.Frame:
        lost_at_text = self.issue_first_seen.get(connection, datetime.datetime.now().strftime("%d-%m %H:%M"))
        row = tk.Frame(self.root, bg=self.banner_bg, highlightthickness=0)
        content = tk.Frame(row, bg=self.banner_bg)
        content.pack(fill=tk.BOTH, expand=True, padx=14, pady=0)

        icon_label = tk.Label(content, image=self.icon, bg=self.banner_bg)
        icon_label.image = self.icon
        icon_label.pack(side=tk.LEFT, padx=(0, 6), pady=2)

        text_label = tk.Label(
            content,
            text=self.main_app.t(
                "network_banner.connection_lost_single",
                default="{connection} offline since {timestamp}",
                connection=connection,
                timestamp=lost_at_text,
            ),
            bg=self.banner_bg,
            fg="black",
            font=("Helvetica", 13, "bold"),
            anchor="center",
            justify=tk.CENTER,
        )
        text_label.pack(side=tk.LEFT, fill=tk.X, expand=True, pady=2)
        return row

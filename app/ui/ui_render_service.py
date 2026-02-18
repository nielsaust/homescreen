from __future__ import annotations

import math
import os
import pathlib
import logging

import tkinter as tk
from PIL import Image, ImageTk
from app.observability.domain_logger import log_event

logger = logging.getLogger(__name__)


class UiRenderService:
    """Owns shared Tk render helpers and lightweight UI tracing."""

    def __init__(self, main_app):
        self.main_app = main_app
        self.action_labels = []
        self.current_overlay_label = None
        self.current_overlay_label_timeout = None
        self._buttons_image_dir = pathlib.Path(__file__).resolve().parents[2] / "images" / "buttons"
        self._label_timeouts: dict[tk.Label, int] = {}

    def force_screen_update(self):
        if self.main_app.settings.force_update:
            log_event(logger, logging.DEBUG, "ui", "render.force_update")
            self.main_app.root.update()
            self.main_app.root.update_idletasks()
        else:
            log_event(logger, logging.DEBUG, "ui", "render.force_update_skipped", reason="disabled_in_settings")

    def trace_ui(self, event_name, **fields):
        if not getattr(self.main_app, "ui_trace_logging", False):
            return
        if hasattr(self.main_app, "trace_ui_event"):
            self.main_app.trace_ui_event(event_name, **fields)

    def trace_widget_state(self, event_name, widget):
        if not getattr(self.main_app, "ui_trace_logging", False):
            return
        if widget is None:
            self.trace_ui(event_name, widget="none")
            return
        try:
            self.trace_ui(
                event_name,
                widget_class=widget.winfo_class(),
                manager=widget.winfo_manager(),
                mapped=bool(widget.winfo_ismapped()),
                width=int(widget.winfo_width()),
                height=int(widget.winfo_height()),
                rootx=int(widget.winfo_rootx()),
                rooty=int(widget.winfo_rooty()),
            )
        except Exception as exc:
            self.trace_ui(event_name, widget_error=str(exc))

    def schedule_trace_widget_state(self, event_name, widget):
        if not getattr(self.main_app, "ui_trace_logging", False):
            return
        delay_ms = max(1, int(getattr(self.main_app, "ui_trace_followup_ms", 80)))
        self.main_app.root.after(delay_ms, lambda: self.trace_widget_state(event_name, widget))

    def _cancel_label_timeout(self, label: tk.Label) -> None:
        timeout_id = self._label_timeouts.pop(label, None)
        if timeout_id is not None:
            try:
                self.main_app.root.after_cancel(timeout_id)
            except Exception:
                pass

    def _schedule_label_timeout(self, label: tk.Label, timeout_ms: int) -> None:
        self._cancel_label_timeout(label)
        if timeout_ms <= 0:
            return

        def remove():
            self._cancel_label_timeout(label)
            if label in self.action_labels:
                self.action_labels.remove(label)
            try:
                label.destroy()
            except Exception:
                pass

        self._label_timeouts[label] = self.main_app.root.after(timeout_ms, remove)

    def hold_action_label(self, label: tk.Label | None) -> None:
        if label is None:
            return
        self._cancel_label_timeout(label)

    def release_action_label(self, label: tk.Label | None, timeout_ms: int | None = None) -> None:
        if label is None:
            return
        timeout = self.main_app.settings.show_feedback_label_timeout if timeout_ms is None else max(0, int(timeout_ms))
        self._schedule_label_timeout(label, timeout)

    def place_action_label(
        self,
        text=None,
        anchor="center",
        image=None,
        bg="black",
        fg="white",
        bordercolor="black",
        timeout_ms: int | None = None,
    ):
        if self.main_app.settings.show_feedback_label_timeout == 0:
            log_event(logger, logging.INFO, "ui", "feedback_label.skipped", reason="disabled_in_settings")
            return None

        label_options = {
            "fg": fg,
            "bg": bg,
            "padx": self.main_app.settings.feedback_label_padx,
            "pady": self.main_app.settings.feedback_label_pady,
            "wraplength": self.main_app.settings.feedback_label_width - 10,
            "highlightbackground": bordercolor,
            "highlightthickness": self.main_app.settings.feedback_label_border,
        }

        if text is not None:
            label_options["text"] = text
            label_options["compound"] = "top"
            label_options["font"] = "Helvetica 20"

        label = tk.Label(self.main_app.root, **label_options)
        self.current_overlay_label = label

        if image is not None:
            image_path = os.fspath(self._buttons_image_dir / image)
            loaded_image = Image.open(image_path)
            loaded_image = loaded_image.resize(self.main_app.settings.feedback_icon_size)
            label_image = ImageTk.PhotoImage(loaded_image)
            label.image = label_image
            label.configure(
                image=label_image,
                width=self.main_app.settings.feedback_label_width,
                height=self.main_app.settings.feedback_label_height,
            )

        label_x = math.floor(
            (self.main_app.settings.screen_width - self.main_app.settings.feedback_label_width) / 2
        ) - self.main_app.settings.feedback_label_border
        label_y = math.floor(
            (self.main_app.settings.screen_height - self.main_app.settings.feedback_label_height) / 2
        ) - self.main_app.settings.feedback_label_border

        if anchor != "center":
            label.place(
                x=self.main_app.root.winfo_width() - label.winfo_reqwidth(),
                y=self.main_app.root.winfo_height() - label.winfo_reqheight(),
            )
        else:
            label.place(x=label_x, y=label_y)

        self.action_labels.append(label)
        timeout = self.main_app.settings.show_feedback_label_timeout if timeout_ms is None else max(0, int(timeout_ms))
        self._schedule_label_timeout(label, timeout)
        return label

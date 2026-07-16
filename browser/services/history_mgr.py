import os
import json
from collections import defaultdict
from datetime import datetime, timezone, date
from PySide6.QtCore import QUrl
from services.constants import HISTORY_PATH
from interface.widgets.better_webengine import BetterWebEngine

class HistoryManager:
    def __init__(self, controller):
        self.controller = controller
        self.browser: BetterWebEngine = None
        self.history: list[dict] = []

        self._load_history()
        self.controller.currentBrowserChanged.connect(self._set_browser)

    def _set_browser(self, browser):
        if self.browser:
            self.browser.urlChanged.disconnect(self._update_history)
        
        self.browser = browser
        self.browser.urlChanged.connect(self._update_history)
    
    def _load_history(self):
        if os.path.exists(HISTORY_PATH):
            try:
                with open(HISTORY_PATH, "r") as f:
                    history: list[dict] = json.load(f)

                if isinstance(history, list):
                    for entry in history:
                        url = entry.get("url", None)
                        visited_at = entry.get("visited_at", None)

                        if url is not None and visited_at is not None:
                            self.history.append({
                                "url": url,
                                "title": entry.get("title", ""),
                                "visited_at": datetime.fromisoformat(visited_at),
                            })

            except Exception as e:
                print(f"Failed to read history: {e}")
    
    def _persist(self):
        history_with_iso = self._get_history_with_iso_dates()

        with open(HISTORY_PATH, "w") as f:
            json.dump(history_with_iso, f, indent=4)

    def _get_history_with_iso_dates(self) -> list[dict]:
        alt_history: list[dict] = []

        for entry in self.history:
            url = entry.get("url", None)
            visited_at = entry.get("visited_at", None)

            if url is not None and visited_at is not None:
                alt_history.append({
                    "url": url,
                    "title": entry.get("title", ""),
                    "visited_at": visited_at.isoformat(),
                })
        
        return alt_history
    
    def _update_history(self, url: QUrl):
        if self.browser:
            now = datetime.now(timezone.utc)
            title = self.browser.title() if self.browser.title() else ""

            self.history.append({
                "url": url.toString(),
                "title": title,
                "visited_at": now,
            })

            self._persist()
    
    def get_history(self) -> list[dict]:
        return self.history
    
    def get_history_grouped_by_date(self) -> dict[date, list[dict]]:
        grouped = defaultdict(list)

        for entry in self.history:
            visited_at = entry.get("visited_at")
            if isinstance(visited_at, datetime):
                grouped[visited_at.date()].append(entry)
            else:
                grouped[date.today()].append(entry)

        return dict(sorted(grouped.items(), reverse=True))
    
    def delete_entry(self, url, visited_at):
        self.history = [
            e for e in self.history
            if not (e.get("url") == url and e.get("visited_at") == visited_at)
        ]
        self._persist()
    
    def clear_history(self):
        self.history.clear()
        self._persist()
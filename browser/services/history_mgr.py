import os
import json
from collections import defaultdict
from datetime import datetime, timezone, date
from PySide6.QtCore import QUrl
from services.constants import HISTORY_PATH
from interface.widgets.better_webengine import BetterWebEngine
from dataclasses import dataclass, field, asdict

@dataclass
class HistoryEntryData:
    url: str
    visited_at: datetime = field(default_factory=lambda: datetime.min(timezone.utc))
    title: str = ""


class HistoryManager:
    def __init__(self, controller):
        self.controller = controller
        self.browser: BetterWebEngine = None
        self.history: list[HistoryEntryData] = []

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
                    raw: list[dict] = json.load(f)

                if isinstance(raw, list):
                    for entry in raw:
                        visited_at = entry.get("visited_at")
                        if visited_at is not None:
                            self.history.append(HistoryEntryData(
                                url=entry.get("url", ""),
                                title=entry.get("title", ""),
                                visited_at=datetime.fromisoformat(visited_at),
                            ))

            except Exception as e:
                print(f"Failed to read history: {e}")
    
    def persist(self):
        with open(HISTORY_PATH, "w") as f:
            json.dump([asdict(e) | {"visited_at": e.visited_at.isoformat()} for e in self.history], f, indent=4)
    
    def _update_history(self, url: QUrl):
        if self.browser:
            self.history.append(HistoryEntryData(
                url=url.toString(),
                title=self.browser.title() if self.browser.title() else "",
                visited_at=datetime.now(timezone.utc),
            ))
    
    def get_history(self) -> list[HistoryEntryData]:
        return self.history
    
    def get_history_grouped_by_date(self) -> dict[date, list[HistoryEntryData]]:
        grouped = defaultdict(list)

        for entry in self.history:
            grouped[entry.visited_at.date()].append(entry)

        return dict(sorted(grouped.items(), reverse=True))
    
    def delete_entry(self, entry: HistoryEntryData):
        self.history = [e for e in self.history if e is not entry]
        self._persist()
    
    def clear_history(self):
        self.history.clear()
        self._persist()
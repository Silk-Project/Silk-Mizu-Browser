from dataclasses import dataclass, field
from services.constants import EXTENSIONS_PATH
import os
import json
import importlib.util

@dataclass
class ExtensionMetadata:
    app_id: str
    name: str
    author: str
    description: str
    version: str
    script_path: str = None
    icon_path: str = ""

    # Installables
    dependencies: list[str] = field(default_factory=list)
    download_path: str = None
    index_source: str = None

class ExtensionManager():
    def __init__(self):
        self.installed_extensions_data = []

    def update_extension_list(self):
        self.installed_extensions_data = []

        with os.scandir(EXTENSIONS_PATH) as d:
            for el in d:
                extension_index_path = os.path.join(EXTENSIONS_PATH, el.name, "index.json")

                if el.is_dir() and os.path.exists(extension_index_path):

                    with open(extension_index_path, "r") as f:
                        extension_index = json.load(f)
                    
                    current_ext = ExtensionMetadata(**extension_index)
                    self.installed_extensions_data.append(current_ext)
    
    def get_installed(self):
        return self.installed_extensions_data

def check_dependencies(deps_list):
        missing = []
        for dep in deps_list:
            if importlib.util.find_spec(dep) is None:
                missing.append(dep)
        return missing

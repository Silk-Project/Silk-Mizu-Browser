# 🌊 Silk Mizu Browser
[![Lint](https://github.com/Silk-Project/Silk-Mizu-Browser/actions/workflows/main.yml/badge.svg)](https://github.com/Silk-Project/Silk-Mizu-Browser/actions/workflows/main.yml)
![Static Badge](https://img.shields.io/badge/License-MIT-blue)
![Commit Activity](https://img.shields.io/github/commit-activity/m/Silk-Project/Silk-Mizu-Browser)
![GitHub Issues](https://img.shields.io/github/issues-raw/Silk-Project/Silk-Mizu-Browser)
![Static Badge](https://img.shields.io/badge/Python-3.14-e9f23d?logo=python&logoColor=white)
![Static Badge](https://img.shields.io/badge/PySide-6.11-41cd52?logo=Qt&labelColor=black)
<br>
Simple and lightweight PySide6 browser for Linux, Windows and Mac computers. Made possible through the QWebEngineView Widget for rendering webpages. Mizu (水) translates to "water" in japanese, which makes sense because you are "surfing" the web.

![Browser Preview](/assets/preview.png)
![Extensions Preview](/assets/preview_extensions.png)

## ⭐️ Features
- Simple but modern UI elements using the Awesome 6 icons and PyQt Dark theme
- Full navigation bar UI editor
- Default search engine selection (Google, DuckDuckGo, Brave...)
- Custom start page selection
- Basic browser navigation features
- Accessability features (zooming, font size)
- Bookmark management
- Silk-Start support
- Easy to use tab system
- AI webpage summarization (optional, local and completely private)
- Download manager
- Custom browser extension manager / engine

## ⚙️ Requirements
- `pyside6` (pip)
- `qtawesome` (pip)
- `pyqtdarktheme` (pip)
- `darkdetect` (pip)
- `ollama` (pip and system wide)
- `requests` (pip)

## ⬇️ Getting the program
A normal git clone will result into missing submodules. Instead use this command:
```
git clone --recursive https://github.com/Silk-Project/Silk-Mizu-Browser.git
```
...or initialize the submodules after you have already cloned the repository:
```
git submodule update --init --recursive
```


## 🚀 Running the program
To use this program, simply execute the main.py file directly via python3.
```
python3 browser/main.py
```
## 💻 To-do
- [x] ~~Improve website tab system and tab bar positioning at the top~~ (Unchanged because of performance reasons)
- [x] ~~"Explain selected text with AI"~~
- [x] ~~Rearrangeable browser interface~~
  - [x] ~~Multiple bar customisation~~
  - [x] ~~Individual styling of navigation elements (color, icon, size, shape, text)~~
  - [ ] Theme import and export (WIP)
  - [ ] Combine general theme settings and the Navigation UI Editor into one universal Theme Editor (WIP)
- [ ] Reader view
- [x] ~~Better overview of current downloads so it can't infinitely stack up in the download menu~~
- [x] ~~Multi-language support~~
- [x] ~~Custom extension store (for the browser itself)~~
  - [x] ~~Widgets (e. g. Notes and additional widgets from the store)~~
    - [ ] Let widgets connect to a Browser Window API
- [x] URL autocompletion
- [x] Tab manager
- [x] Floating Adress Bar
- [x] Website

## 👥 Contributing
Feel free to open issues and create pull requests.

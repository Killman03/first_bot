@echo off
cd /d "%~dp0"
title Zoom Clipboard Watcher
py zoom_clipboard_opener.py
if errorlevel 1 pause

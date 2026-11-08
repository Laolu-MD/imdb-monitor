@echo off
cd /d "%~dp0"
py movie_helper.py
if errorlevel 1 pause

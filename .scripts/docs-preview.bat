@echo off
cd /d "%~dp0.."
uv run .scripts/build_docs.py preview
pause

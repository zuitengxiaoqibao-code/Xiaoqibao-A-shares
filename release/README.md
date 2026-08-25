# Portable executable

This directory contains the latest Windows portable build committed with the
source snapshot. Run `XiaoQiBao-Portable/xiaoqibao.exe` on Windows 10/11.

The build includes the PyInstaller runtime (`_internal`) and bundled web
assets (`web`). Runtime data directories are intentionally omitted from Git:

- `config`
- `data`
- `news`
- `cache`
- `logs`
- `models`
- `exports`
- `backups`

The application creates those directories beside the executable on first
launch. Use the in-app data maintenance tools to acquire local market data.
No API keys, tokens, user configuration, databases, caches, news archives, or
logs are included in this artifact.

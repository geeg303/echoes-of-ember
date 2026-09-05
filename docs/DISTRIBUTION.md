# Distribution

Echoes of Ember `0.1.0-alpha` is an internal/pre-alpha **World 1 Vertical Slice**, not version 1.0 or the completed four-world game.

The release pipeline produces separate player and developer one-directory ZIPs named with version, actual host platform, architecture, and flavor. Player builds expose the normal title/campaign/settings/achievement experience and reject `--debug`, `--editor`, and `--level`. Developer builds support those modes for internal testing and authoring without duplicating source.

Read-only `assets/` and `data/` travel inside the application. Saves, settings, and achievements stay in the existing OS-specific per-user data directory and remain compatible with campaign schema 3, settings schema 2, and achievement schema 1. Deleting an extracted game folder does not delete user data.

Only Linux x86_64 artifacts were built automatically in Phase 26. Windows and macOS builds must be produced and tested natively. No GitHub Release, tag, signing, notarization, installer, updater, or store integration is created automatically. Physical-controller feel, audio balance, fullscreen quality, antivirus behavior, and a separate clean machine remain human-review items.

# Browser Manager

Spin up multiple isolated browser instances from one terminal. Each instance gets its own fresh profile — no shared cookies, no saved passwords leaking between windows, no leftover state from previous runs.

Built for Windows, Linux, macOS. Works with Chrome, Firefox, Edge.

## What It Does

You pick a browser, tell it how many instances you want, it opens them. Each one runs in a completely separate profile directory. When you're done, type `q` or hit Ctrl+C. It tears everything down cleanly.

Edge instances start fully fresh. No auto-importing your existing bookmarks or Microsoft account data. No "Welcome to Edge" setup wizard. Just a clean browser window.

## Why

I needed to log into the same site with multiple accounts at the same time. Normally you'd open incognito windows for that, but incognito has limits — you can only run one incognito session per browser, it doesn't save anything between runs, extensions are disabled by default, some sites detect it.

This tool gives you something better. Each instance is a full standalone browser with its own cookies, storage, login state. You can log into Gmail with 5 different accounts across 5 separate Chrome windows, all running side by side. No incognito needed. No "already signed in" conflicts. Each window has no idea the others exist.

Works great for managing multiple social media accounts, testing different user roles on the same app, running bots that each need their own session, or any situation where you need several independent logins open at once without them stepping on each other.

```

You still need Chrome, Firefox, or Edge installed on the machine. The binary bundles Python, Selenium, the driver manager — everything except the actual browser.

## Run From Source

If you prefer running the Python script directly:

```
pip install selenium colorama
cd browser
python browser.py
```

The script auto-installs `webdriver-manager` on first run if it's missing. That package downloads the correct driver binary for your browser version. You don't need to manually grab chromedriver or geckodriver.

It prints a banner showing your platform, then asks two questions:

```
Browser (chrome/edge/firefox): chrome
Number of instances: 3
```

Three Chrome windows open, each with their own profile. Close them by typing `q` or pressing Ctrl+C.

## Build Your Own Binary

Run the build script on whatever platform you're targeting. PyInstaller can only build for the OS it's running on.

```
pip install pyinstaller selenium colorama webdriver-manager
python build.py
```

This produces a single-file executable in the `dist/` folder:

| OS | Output file | Typical size |
|----|-------------|--------------|
| Windows | `dist/browser-manager.exe` | ~30 MB |
| Linux | `dist/browser-manager` | ~27 MB |
| macOS | `dist/browser-manager-macos` | ~30 MB |

The build script installs missing dependencies automatically, runs PyInstaller, cleans up temp files when done.

## Platform Notes

**Windows**
- Looks for Chrome in Program Files, Edge in its default location, Firefox in Mozilla's folder
- Profiles go to `%USERPROFILE%\selenium_profiles`
- Signal handling uses `SIGBREAK` since Windows handles Ctrl+C differently

**Linux**
- Searches PATH for `google-chrome`, `chromium-browser`, `microsoft-edge`, `firefox`
- Adds `--no-sandbox` since many Linux setups (containers, WSL) need it
- Adds `--disable-dev-shm-usage` to avoid shared memory issues in constrained environments
- Profiles go to `~/selenium_profiles`

**macOS**
- Checks `/Applications` for browser .app bundles
- Profiles go to `~/selenium_profiles`

## How Profiles Work

Every time you launch, the script creates a fresh directory per instance:

```
~/selenium_profiles/
  chrome_instance_1/
  chrome_instance_2/
  edge_instance_1/
```

Old profiles from previous runs get deleted on startup. When you close the script, it removes the profile directories too. Nothing sticks around.

For Edge specifically, the script forces `--profile-directory=Default` inside the custom user data dir. This stops Edge from pulling in your real profile. It also disables auto-import, sidebar popups, the sync prompt. Each Edge instance behaves like a first-time install.

## Stealth Mode

Chrome instances (Edge too, since it's Chromium-based) get a few anti-detection tweaks:

- `navigator.webdriver` returns `undefined` instead of `true`
- The "Chrome is being controlled by automated test software" banner is suppressed
- Automation flags are stripped from the browser switches

This isn't bulletproof anti-detection. It's enough that basic checks won't flag the session as automated.

## Driver Management

The script tries to launch with whatever driver is already on your system. If that fails, it falls back to `webdriver-manager` which downloads the matching driver automatically.

So if you already have `chromedriver` in your PATH, it uses that. If you don't, it grabs it. Either way you don't need to think about it.

## File Structure

```
browser/
  browser.py      - main script (run with Python)
  build.py        - builds standalone binary for your OS
  dist/
    browser-manager       - Linux binary
    browser-manager.exe   - Windows binary (build on Windows)
    browser-manager-macos - macOS binary (build on macOS)
```

## Quick Reference

| Action | How |
|--------|-----|
| Open 2 Chrome windows | Run the binary, type `chrome`, `2` |
| Open 5 Edge windows | Run the binary, type `edge`, `5` |
| Close everything | Type `q` or press Ctrl+C |
| Build binary for your OS | `python build.py` |
| Change profile location | Edit `get_profile_base_dir()` in browser.py |

## Author

**krainium** — [github.com/krainium](https://github.com/krainium)

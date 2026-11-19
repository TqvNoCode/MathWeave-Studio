# Arch Linux Installation Guide — MathWeave Studio

This guide covers the installation and setup of **MathWeave Studio** on **Arch Linux**.

---

## Table of Contents

- [Prerequisites](#prerequisites)
- [1. Installation via AUR / yay (Pending Publication)](#1-installation-via-aur--yay-pending-publication)
- [2. Installation from Source (Verified Working Path)](#2-installation-from-source-verified-working-path)
  - [Step 1: Install System Prerequisites](#step-1-install-system-prerequisites)
  - [Step 2: Clone the Repository](#step-2-clone-the-repository)
  - [Step 3: Synchronize Python Dependencies](#step-3-synchronize-python-dependencies)
  - [Step 4: Launch the Application](#step-4-launch-the-application)
  - [Step 5: Verify the Test Suite](#step-5-verify-the-test-suite)
  - [Troubleshooting](#troubleshooting)
- [3. Uninstallation](#3-uninstallation)
  - [AUR Uninstallation](#aur-uninstallation)
  - [Source / Git Uninstallation](#source--git-uninstallation)

---

## Prerequisites

MathWeave Studio requires:
- **Operating System:** Arch Linux (x86_64).
- **Python:** Version `>= 3.14` (as defined in `pyproject.toml` and `.python-version`).
- **Package Manager:** [`uv`](https://docs.astral.sh/uv/) (recommended for fast, reproducible dependency resolution) or standard `python-virtualenv`.
- **Web Browser:** Any modern browser (Firefox, Chromium, Brave) to render the NiceGUI interface and KaTeX/MathML formulas.

---

## 1. Installation via AUR / yay (Pending Publication)

> [!NOTE]
> MathWeave Studio is currently in active MVP development. An official Arch User Repository (AUR) package has not yet been published.
>
> Once the AUR package is published, users of AUR helpers such as `yay` will be able to install and update the package directly.

```bash
# --- AUR INSTALLATION PLACEHOLDER ---
# Once published to AUR, install with:
# yay -S <mathweave-studio-package-name>
```

If you do not have `yay` installed, follow the official instructions:
[How to install yay](https://github.com/jguer/yay#installation)

Until the AUR package is released, use the verified source installation below.

---

## 2. Installation from Source (Verified Working Path)

Running from source via `uv` is the officially verified method on Arch Linux.

### Step 1: Install System Prerequisites

Install Git and `uv` using `pacman`:

```bash
sudo pacman -S --needed git uv
```

*(If you prefer standard Python virtual environments instead of `uv`, install `python` and `python-pip` instead).*

### Step 2: Clone the Repository

Clone the project repository:

```bash
# Via HTTPS
git clone https://github.com/TqvNoCode/MathWeave-Studio.git
cd MathWeave-Studio

# Or via SSH (if authorized with an SSH key)
git clone git@github.com:TqvNoCode/MathWeave-Studio.git
cd MathWeave-Studio
```

*(Note: If the repository is currently private during development, ensure your GitHub account has authorized repository access).*

### Step 3: Synchronize Python Dependencies

Use `uv` to automatically create an isolated `.venv` and synchronize all exact locked dependencies from `uv.lock`:

```bash
uv sync
```

Alternatively, with standard Python:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
```

### Step 4: Launch the Application

- **Native Desktop Mode (Default):**
  ```bash
  uv run run.py
  ```
  Opens MathWeave Studio directly in a native desktop window via Qt6/PyQt6 and pywebview on X11 or Wayland (including KDE Plasma).

- **Browser Mode:**
  ```bash
  uv run run.py --browser
  ```
  Launches the UI directly in your default web browser at **[http://localhost:8080](http://localhost:8080)**.

To stop the application cleanly, press **`Ctrl + C`** in your terminal or close the native window. The shutdown handler immediately releases the port and cleanly terminates worker processes.

### Step 5: Verify the Test Suite

To verify that all mathematical solvers, architectural boundaries, and pedagogical derivation rules are working correctly in your environment, run the test suite:

```bash
uv run pytest
```

Expected result: **243 passed** in under 25 seconds.

### Troubleshooting

- **Port 8080 in use:** If port 8080 is already occupied by another service, MathWeave Studio automatically binds to an available ephemeral port. Check the terminal output for the active URL (e.g., `http://127.0.0.1:42189`).
- **Qt Platform / WebEngine system dependencies:** MathWeave Studio uses pywebview with the Qt backend. On Arch Linux, ensure system Qt dependencies are installed:
  ```bash
  sudo pacman -S --needed qt6-webengine qt6-webchannel
  ```
- **Headless environments without display:** If running on a server or container without X11/Wayland (`DISPLAY` or `WAYLAND_DISPLAY`), launch with `--browser`.

---

## 3. Uninstallation

### AUR Uninstallation

```bash
# --- AUR UNINSTALLATION PLACEHOLDER ---
# Once published, remove with:
# yay -R <mathweave-studio-package-name>
```

### Source / Git Uninstallation

MathWeave Studio is fully self-contained. It does not store hidden database files, background daemons, or configuration caches outside the project workspace.

1. **Stop the application:** Ensure any running instance has been stopped with `Ctrl + C`.
2. **Back up personal data:** If you created custom test scripts or notes inside the folder, back them up first.
3. **Remove the project directory:**
   ```bash
   rm -rf /path/to/MathWeave-Studio
   ```
4. **Remove user desktop launcher (if installed):** If you copied `mathweave-studio.desktop` into your user applications folder:
   ```bash
   rm -f ~/.local/share/applications/mathweave-studio.desktop
   update-desktop-database ~/.local/share/applications/ 2>/dev/null || true
   ```

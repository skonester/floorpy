![Floorpy Logo](floorpy.png)

## Overview
Floorpy is a Windows batch build script that packages the Floorp browser into a portable Self-Extracting Executable (SFX).

## Features
* **Latest Floorp Download:** Can download the current Windows x64 Floorp release from the official Floorp GitHub releases and refresh the local `floorp/` folder automatically.
* **Automated Debloating:** Strips unnecessary updaters and non-essential directories to reduce the footprint while maintaining critical media pipeline stability.
* **High-Ratio Compression:** Utilizes LZMA2 (7-Zip) maximum compression to drastically shrink the core binaries.
* **Portable SFX Generation:** Packages the compressed archive into a standalone `floorpy.exe` that executes the browser seamlessly.
* **Resource Injection:** Automatically applies custom icons and manifest configurations to the final executable using Resource Hacker.

## Primary Use Cases

* **WinPE (Windows Preinstallation Environment) Integration:** WinPE lacks a native web browser. `floorpy.exe` serves as a critical drop-in diagnostic tool. Because it is a portable SFX, it can be executed entirely within the WinPE RAM disk, allowing technicians to download drivers, read documentation, or access web-based IT consoles on bare-metal systems.
* **Portable IT Toolkits:** Ideal for inclusion on diagnostic USB flash drives. It provides a secure, fully functional web environment for troubleshooting host machines without relying on the host's potentially compromised or outdated local browsers.
* **Non-Administrative Execution:** Because the SFX extracts and runs within the user's local directory structure rather than executing a system-level installation, it can often be utilized in restricted environments where standard software installations are blocked by Group Policy.
* **Sterile Browsing Sessions:** By configuring the `TempProfile` prior to packing, the resulting executable launches a pre-configured, pristine browsing environment every time, making it ideal for clean-room testing or secure remote access.


## Prerequisites
The build script can either use an existing `floorp/` folder or download the latest Floorp release for you. These files must be present next to `Build.bat`:

* `7za64.exe` - 7-Zip standalone command-line executable.
* `7zS264.sfx` - 7-Zip Self-Extracting module.
* `ResourceHacker.exe` - Command-line resource compiler.
* `icon.ico` - Custom icon for the final executable.
* `Manifest.txt` - Configuration manifest for the final executable.
* `run.bat` - The internal execution script that is packaged and triggered when the SFX is launched.

Optional:

* `floorp/` - Existing Floorp browser files. If absent or stale, use the update option in `Build.bat`.
* `TempProfile/` - A root-level profile template. If present, it is copied into `floorp/TempProfile` during debloat.

## Usage
1. Run the primary batch script.
2. Select the desired operation from the interactive command menu:
   * **`1`**: Download the latest Windows x64 Floorp release into `floorp/`.
   * **`2`**: Debloat the `floorp/` directory.
   * **`3`**: Pack `floorp/` and `run.bat` into `floorp.7z`.
   * **`4`**: Generate the SFX executable (`floorpy.exe`).
   * **`5`**: Inject the custom icon and manifest.
   * **`F`**: Build from the current local `floorp/` folder.
   * **`U`**: Download the latest Floorp release, then build.

## Offline Builds
Internet access is not required if `floorp/` already contains the browser files. Choose **`F`** in `Build.bat` to debloat and package the existing local `floorp/` folder without downloading anything.

Use **`1`** or **`U`** only when you want the script to refresh `floorp/` from the latest online Floorp release.

## Technical Notes & Limitations
* **Engine Architecture:** The core `omni.ja` archive is intentionally bypassed during the debloat phase. Altering this file with standard 7-Zip compression corrupts the structural offsets required by the Gecko engine, resulting in fatal XPCOM initialization errors. Do not attempt to debloat `omni.ja` manually.
* **Generated Files:** `floorp.7z`, `floorpy.exe`, `.build/`, and `floorp.previous/` are build outputs and are ignored by Git.
* **Version Control:** If pushing `floorp/` itself to a repository, Git Large File Storage (LFS) should be used for large internal binaries such as `*.dll` and `*.ja`.

![Floorpy Logo](floorpy.png)

## Overview
Floorpy is an automated Windows batch script designed for the Firefox Floorp browser and compile it into a highly compressed 91MB, portable Self-Extracting Executable (SFX). 

## Features
* **Automated Debloating:** Strips unnecessary telemetry, updaters, and non-essential directories to reduce the footprint while maintaining critical media pipeline stability (Widevine DRM and Direct3D functionality are strictly preserved).
* **High-Ratio Compression:** Utilizes LZMA2 (7-Zip) maximum compression to drastically shrink the core binaries.
* **Portable SFX Generation:** Packages the compressed archive into a standalone `floorpy.exe` that executes the browser seamlessly.
* **Resource Injection:** Automatically applies custom icons and manifest configurations to the final executable using Resource Hacker.

## Primary Use Cases

* **WinPE (Windows Preinstallation Environment) Integration:** WinPE lacks a native web browser. `floorpy.exe` serves as a critical drop-in diagnostic tool. Because it is a portable SFX, it can be executed entirely within the WinPE RAM disk, allowing technicians to download drivers, read documentation, or access web-based IT consoles on bare-metal systems.
* **Portable IT Toolkits:** Ideal for inclusion on diagnostic USB flash drives. It provides a secure, fully functional web environment for troubleshooting host machines without relying on the host's potentially compromised or outdated local browsers.
* **Non-Administrative Execution:** Because the SFX extracts and runs within the user's local directory structure rather than executing a system-level installation, it can often be utilized in restricted environments where standard software installations are blocked by Group Policy.
* **Sterile Browsing Sessions:** By configuring the `TempProfile` prior to packing, the resulting executable launches a pre-configured, pristine browsing environment every time, making it ideal for clean-room testing or secure remote access.


## Prerequisites
To ensure structural integrity during the build process, the following files and directories must be present in the exact same root folder as the primary batch script:

* `floorp/` - The source directory containing the raw Floorp browser files.
* `7za64.exe` - 7-Zip standalone command-line executable.
* `7zS264.sfx` - 7-Zip Self-Extracting module.
* `ResourceHacker.exe` - Command-line resource compiler.
* `icon.ico` - Custom icon for the final executable.
* `Manifest.txt` - Configuration manifest for the final executable.
* `run.bat` - The internal execution script that is packaged and triggered when the SFX is launched.

## Usage
1. Run the primary batch script.
2. Select the desired operation from the interactive command menu:
   * **`1`**: Debloat the `floorp` directory.
   * **`2`**: Pack the directory into a `.7z` archive.
   * **`3`**: Generate the SFX executable (`floorpy.exe`).
   * **`4`**: Inject the custom icon and manifest.
   * **`F`**: Execute all steps (1-4) automatically in sequence.

## Technical Notes & Limitations
* **Engine Architecture:** The core `omni.ja` archive is intentionally bypassed during the debloat phase. Altering this file with standard 7-Zip compression corrupts the structural offsets required by the Gecko engine, resulting in fatal XPCOM initialization errors. Do not attempt to debloat `omni.ja` manually.
* **Version Control:** If pushing this project to a repository, Git Large File Storage (LFS) must be initialized to track the massive internal binaries (e.g., `*.dll`, `*.ja`) to bypass standard 100MB file size limitations.
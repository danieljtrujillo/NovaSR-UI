"""
install_context_menu.py  –  Add/remove "Upscale with NovaSR" to the Windows
right-click context menu for audio files.

Run as Administrator:
    python install_context_menu.py --install
    python install_context_menu.py --uninstall
"""

import argparse
import os
import sys

# Check if running on Windows
if os.name != 'nt':
    print("ERROR: This script only works on Windows.")
    print("Context menu integration is a Windows-only feature.")
    sys.exit(1)

import winreg

# Audio extensions to register
EXTENSIONS = [".wav", ".mp3", ".flac", ".ogg", ".opus", ".m4a", ".aac", ".wma"]
MENU_LABEL = "Upscale with NovaSR"
REG_KEY_NAME = "NovaSR_Upscale"


def _get_command():
    """Build the shell command that Windows will run when the menu item is clicked."""
    python = sys.executable
    gui_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "novasr_gui.py")
    # %1 is replaced by Windows with the selected file path
    return f'"{python}" "{gui_script}" "%1"'


def install():
    command = _get_command()
    count = 0
    for ext in EXTENSIONS:
        try:
            # Ensure the extension key exists under HKCU\Software\Classes
            ext_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"Software\Classes\{ext}")
            winreg.CloseKey(ext_key)

            # Create shell > NovaSR_Upscale > command
            key_path = rf"Software\Classes\{ext}\shell\{REG_KEY_NAME}"
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path)
            winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_LABEL)
            winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,168")
            winreg.CloseKey(key)

            cmd_key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, rf"{key_path}\command")
            winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, command)
            winreg.CloseKey(cmd_key)
            count += 1
        except Exception as exc:
            print(f"  ⚠  Failed for {ext}: {exc}")

    print(f"✓ Registered '{MENU_LABEL}' for {count}/{len(EXTENSIONS)} extensions.")
    print("  Right-click any audio file to see the new option.")


def uninstall():
    count = 0
    for ext in EXTENSIONS:
        try:
            key_path = rf"Software\Classes\{ext}\shell\{REG_KEY_NAME}"
            # Delete command subkey first, then the parent
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, rf"{key_path}\command")
            except FileNotFoundError:
                pass
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            count += 1
        except FileNotFoundError:
            pass
        except Exception as exc:
            print(f"  ⚠  Failed for {ext}: {exc}")

    print(f"✓ Removed '{MENU_LABEL}' for {count} extensions.")


def main():
    parser = argparse.ArgumentParser(description="NovaSR context-menu installer")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--install", action="store_true", help="Add right-click menu entry")
    group.add_argument("--uninstall", action="store_true", help="Remove right-click menu entry")
    args = parser.parse_args()

    if args.install:
        install()
    else:
        uninstall()


if __name__ == "__main__":
    main()

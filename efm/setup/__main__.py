#!/usr/bin/env python3
"""Interactive CLI for DRM configuration and key extraction."""

import argparse
import os
import platform
import subprocess
import sys
from pathlib import Path

from rich.console import Console
from rich.prompt import IntPrompt, Prompt
from rich.table import Table

# Platform-specific imports for keyboard handling
if platform.system() == "Windows":
    import msvcrt
else:
    import tty
    import termios

from efm.config import Config

console = Console()


# Local functions for each menu item
def get_adobe_key():
    """Extract Adobe Digital Editions keys."""
    console.print("[bold]Extracting Adobe Digital Editions Keys[/bold]")
    console.print("-" * 40)
    console.print()
    
    output_dir = Prompt.ask("Output directory", default=".")
    
    console.print(f"\n[yellow]Searching for Adobe Digital Editions installation...[/yellow]")
    console.print("Looking in default locations:")
    
    if platform.system() == "Windows":
        console.print("  • C:\\Program Files (x86)\\Adobe\\Adobe Digital Editions")
        console.print("  • Registry: HKEY_CURRENT_USER\\Software\\Adobe\\Adept")
    else:  # macOS
        console.print("  • ~/Library/Application Support/Adobe/Digital Editions")
        console.print("  • /Applications/Adobe Digital Editions.app")
    
    console.print(f"\n[yellow]Extracting keys to: {output_dir}[/yellow]")
    
    # Run the actual extraction
    success = run_dedrm_script("adobekey", "cli_main", [output_dir])
    
    if success:
        console.print("\n[green]✓ Keys extracted successfully![/green]")
        console.print(f"Check {output_dir} for .der key files")
    
    return success


def test_epub_drm():
    """Test EPUB DRM type."""
    console.print("[bold]Testing EPUB DRM Type[/bold]")
    console.print("-" * 40)
    console.print()
    
    epub_path = Prompt.ask("EPUB file path")
    
    console.print(f"\n[yellow]Analyzing: {epub_path}[/yellow]")
    console.print("Checking for DRM signatures...")
    
    # Run the test
    success = run_dedrm_script("epubtest", "main", [epub_path])
    
    return success


def decrypt_adobe_epub():
    """Decrypt Adobe EPUB."""
    console.print("[bold]Decrypting Adobe EPUB[/bold]")
    console.print("-" * 40)
    console.print()
    
    key_file = Prompt.ask("Key file path")
    input_epub = Prompt.ask("Input EPUB file")
    output_epub = Prompt.ask("Output EPUB file")
    
    console.print(f"\n[yellow]Processing Adobe DRM removal...[/yellow]")
    console.print(f"Key file: {key_file}")
    console.print(f"Input: {input_epub}")
    console.print(f"Output: {output_epub}")
    
    # Run decryption
    success = run_dedrm_script("ineptepub", "cli_main", [key_file, input_epub, output_epub])
    
    if success:
        console.print("\n[green]✓ EPUB decrypted successfully![/green]")
    
    return success


def decrypt_adobe_pdf():
    """Decrypt Adobe PDF."""
    console.print("[bold]Decrypting Adobe PDF[/bold]")
    console.print("-" * 40)
    console.print()
    
    key_file = Prompt.ask("Key file path")
    input_pdf = Prompt.ask("Input PDF file")
    output_pdf = Prompt.ask("Output PDF file")
    
    console.print(f"\n[yellow]Processing Adobe DRM removal...[/yellow]")
    console.print(f"Key file: {key_file}")
    console.print(f"Input: {input_pdf}")
    console.print(f"Output: {output_pdf}")
    
    # Run decryption
    success = run_dedrm_script("ineptpdf", "cli_main", [key_file, input_pdf, output_pdf])
    
    if success:
        console.print("\n[green]✓ PDF decrypted successfully![/green]")
    
    return success


def get_kindle_keys():
    """Extract Kindle for PC/Mac keys."""
    console.print("[bold]Extracting Kindle Desktop Keys[/bold]")
    console.print("-" * 40)
    console.print()
    
    console.print("[yellow]Searching for Kindle installation...[/yellow]")
    
    if platform.system() == "Windows":
        console.print("Looking in:")
        console.print("  • C:\\Users\\[username]\\AppData\\Local\\Amazon\\Kindle")
        console.print("  • Registry keys for Kindle")
    else:  # macOS
        console.print("Looking in:")
        console.print("  • ~/Library/Application Support/Kindle")
        console.print("  • ~/Library/Containers/com.amazon.Kindle")
    
    console.print("\n[yellow]Extracting keys...[/yellow]")
    
    # Run extraction
    success = run_dedrm_script("kindlekey", "cli_main", [])
    
    if success:
        console.print("\n[green]✓ Kindle keys extracted successfully![/green]")
    
    return success


def get_android_kindle_keys():
    """Extract Kindle for Android keys."""
    console.print("[bold]Extracting Kindle Android Keys[/bold]")
    console.print("-" * 40)
    console.print()
    
    output_dir = Prompt.ask("Output directory", default=".")
    
    console.print("\n[yellow]Instructions:[/yellow]")
    console.print("1. Enable USB debugging on your Android device")
    console.print("2. Connect device via USB")
    console.print("3. Run 'adb backup com.amazon.kindle' to create backup")
    console.print("4. This tool will extract keys from the backup")
    
    console.print(f"\n[yellow]Extracting keys to: {output_dir}[/yellow]")
    
    # Run extraction
    success = run_dedrm_script("androidkindlekey", "cli_main", [output_dir])
    
    if success:
        console.print("\n[green]✓ Android keys extracted successfully![/green]")
    
    return success


def generate_kindle_pid():
    """Generate Kindle PID."""
    console.print("[bold]Generating Kindle PID[/bold]")
    console.print("-" * 40)
    console.print()
    
    serial = Prompt.ask("Kindle serial number")
    
    console.print(f"\n[yellow]Generating PID from serial: {serial}[/yellow]")
    
    # Run generation
    success = run_dedrm_script("kindlepid", "cli_main", [serial])
    
    return success


def remove_mobi_drm():
    """Remove DRM from Mobi file."""
    console.print("[bold]Removing Mobi DRM[/bold]")
    console.print("-" * 40)
    console.print()
    
    input_mobi = Prompt.ask("Input Mobi file")
    output_mobi = Prompt.ask("Output Mobi file")
    pid_or_key = Prompt.ask("PID or key file")
    
    console.print(f"\n[yellow]Processing Mobi DRM removal...[/yellow]")
    console.print(f"Input: {input_mobi}")
    console.print(f"Output: {output_mobi}")
    console.print(f"PID/Key: {pid_or_key}")
    
    # Run removal
    success = run_dedrm_script("mobidedrm", "cli_main", [input_mobi, output_mobi, pid_or_key])
    
    if success:
        console.print("\n[green]✓ Mobi DRM removed successfully![/green]")
    
    return success


def remove_kindle_drm():
    """Remove DRM from Kindle file."""
    console.print("[bold]Removing Kindle DRM[/bold]")
    console.print("-" * 40)
    console.print()
    
    input_file = Prompt.ask("Input file")
    output_dir = Prompt.ask("Output directory", default=".")
    
    console.print(f"\n[yellow]Processing Kindle DRM removal...[/yellow]")
    console.print(f"Input: {input_file}")
    console.print(f"Output directory: {output_dir}")
    console.print("Supported formats: AZW, AZW3, AZW4, KFX, Mobi")
    
    # Run removal
    success = run_dedrm_script("k4mobidedrm", "cli_main", [input_file, output_dir])
    
    if success:
        console.print("\n[green]✓ Kindle DRM removed successfully![/green]")
    
    return success


def get_nook_keys():
    """Extract Nook Study keys."""
    console.print("[bold]Extracting Nook Study Keys[/bold]")
    console.print("-" * 40)
    console.print()
    
    console.print("[yellow]Searching for Nook Study installation...[/yellow]")
    console.print("Looking in:")
    console.print("  • C:\\Program Files (x86)\\Barnes & Noble\\NOOKstudy")
    console.print("  • Registry keys for Nook")
    
    console.print("\n[yellow]Extracting keys...[/yellow]")
    
    # Run extraction
    success = run_dedrm_script("ignoblekeyNookStudy", "cli_main", [])
    
    if success:
        console.print("\n[green]✓ Nook keys extracted successfully![/green]")
    
    return success


def generate_bn_hash():
    """Generate B&N passphrase hash."""
    console.print("[bold]Generating Barnes & Noble Passphrase Hash[/bold]")
    console.print("-" * 40)
    console.print()
    
    name = Prompt.ask("Name")
    cc_number = Prompt.ask("Credit card number (last 8 digits)")
    
    console.print(f"\n[yellow]Generating hash...[/yellow]")
    console.print(f"Name: {name}")
    console.print(f"CC suffix: {'*' * 4}{cc_number}")
    
    # Run generation
    success = run_dedrm_script("ignoblekeyGenPassHash", "cli_main", [name, cc_number])
    
    return success


# Menu structure using local functions
class MenuItem:
    def __init__(self, title, fn, platforms=None, description="", key=None):
        self.title = title
        self.fn = fn
        self.platforms = platforms or ["all"]
        self.description = description
        self.key = key  # Optional key for direct access


class MenuSection:
    def __init__(self, title, items):
        self.title = title
        self.items = items


def save_config():
    """Interactive config saving."""
    config = Config()
    
    console.print("\n[bold]Save Keys to Configuration[/bold]")
    console.print("-" * 30)
    
    # Check for existing keys
    key_types = [
        ("Adobe key file", "adobekey", "Path to Adobe key file (.der)"),
        ("Kindle key file", "kindlekey", "Path to Kindle key file"),
        ("Kindle database", "kindle_database", "Path to Kindle database"),
        ("Android backup", "android_backup", "Path to Android backup file"),
    ]
    
    updated = False
    for name, key, description in key_types:
        console.print(f"\n{description}")
        path = Prompt.ask(f"{name} path (leave empty to skip)", default="")
        
        if path:
            path_obj = Path(path).expanduser().resolve()
            if path_obj.exists():
                setattr(config, key, str(path_obj))
                updated = True
                console.print(f"[green]✓ {name} set to: {path_obj}[/green]")
            else:
                console.print(f"[red]✗ File not found: {path}[/red]")
    
    if updated:
        config.save()
        console.print("\n[green]Configuration saved successfully![/green]")
    else:
        console.print("\n[yellow]No changes made to configuration.[/yellow]")
    
    Prompt.ask("\nPress Enter to continue")


MENU_SECTIONS = [
    MenuSection("Adobe DRM Tools", [
        MenuItem(
            title="Extract Adobe Digital Editions keys",
            fn=get_adobe_key,
            platforms=["Windows", "Darwin"],
            description="Extract keys from Adobe Digital Editions installation",
            key="adobe-key"
        ),
        MenuItem(
            title="Test EPUB DRM type",
            fn=test_epub_drm,
            platforms=["all"],
            description="Check what type of DRM an EPUB file has",
            key="epub-test"
        ),
        MenuItem(
            title="Decrypt Adobe EPUB",
            fn=decrypt_adobe_epub,
            platforms=["all"],
            description="Remove Adobe DRM from EPUB file using key",
            key="epub-decrypt"
        ),
        MenuItem(
            title="Decrypt Adobe PDF",
            fn=decrypt_adobe_pdf,
            platforms=["all"],
            description="Remove Adobe DRM from PDF file using key",
            key="pdf-decrypt"
        ),
    ]),
    MenuSection("Kindle DRM Tools", [
        MenuItem(
            title="Extract Kindle for PC/Mac keys",
            fn=get_kindle_keys,
            platforms=["Windows", "Darwin"],
            description="Extract keys from Kindle desktop application",
            key="kindle-key"
        ),
        MenuItem(
            title="Extract Kindle for Android keys",
            fn=get_android_kindle_keys,
            platforms=["all"],
            description="Extract keys from Kindle Android backup",
            key="kindle-android"
        ),
        MenuItem(
            title="Generate Kindle PID",
            fn=generate_kindle_pid,
            platforms=["all"],
            description="Generate PID from Kindle device serial number",
            key="kindle-pid"
        ),
        MenuItem(
            title="Remove DRM from Mobi file",
            fn=remove_mobi_drm,
            platforms=["all"],
            description="Remove DRM from older Mobi format files",
            key="mobi-decrypt"
        ),
        MenuItem(
            title="Remove DRM from Kindle file",
            fn=remove_kindle_drm,
            platforms=["all"],
            description="Remove DRM from Kindle AZW/KFX files",
            key="kindle-decrypt"
        ),
    ]),
    MenuSection("Barnes & Noble DRM Tools", [
        MenuItem(
            title="Extract Nook Study keys",
            fn=get_nook_keys,
            platforms=["Windows"],
            description="Extract keys from Nook Study application",
            key="nook-key"
        ),
        MenuItem(
            title="Generate B&N passphrase hash",
            fn=generate_bn_hash,
            platforms=["all"],
            description="Generate Barnes & Noble passphrase hash",
            key="bn-hash"
        ),
    ]),
    MenuSection("Other Options", [
        MenuItem(
            title="Save extracted keys to config",
            fn=save_config,
            platforms=["all"],
            description="Update EFM config with extracted keys",
            key="save-config"
        ),
    ])
]


def create_menu_display(selected_index):
    """Create the menu display with highlighted selection."""
    lines = []
    lines.append("[bold cyan]EFM Setup - DRM Configuration Tool[/bold cyan]")
    lines.append("=" * 40)
    lines.append("")
    
    # Flatten all menu items to create a linear list
    all_items = []
    current_index = 0
    
    for section in MENU_SECTIONS:
        lines.append(f"[bold]{section.title}:[/bold]")
        
        for item in section.items:
            is_selected = current_index == selected_index
            prefix = "  → " if is_selected else "    "
            style = "[bold white on blue]" if is_selected else ""
            end_style = "[/bold white on blue]" if is_selected else ""
            lines.append(f"{style}{prefix}{item.title}{end_style}")
            all_items.append(item)
            current_index += 1
        
        lines.append("")
    
    # Exit option
    is_selected = current_index == selected_index
    prefix = "  → " if is_selected else "    "
    style = "[bold white on blue]" if is_selected else ""
    end_style = "[/bold white on blue]" if is_selected else ""
    lines.append(f"{style}{prefix}Exit{end_style}")
    all_items.append(None)  # None represents exit
    
    lines.append("")
    lines.append("[dim]Use ↑/↓ to navigate, Enter to select, q to quit[/dim]")
    
    return "\n".join(lines), all_items


def get_key():
    """Get a single keypress from the user."""
    if platform.system() == "Windows":
        key = msvcrt.getch()
        if key == b'\xe0':  # Special key (arrows)
            key = msvcrt.getch()
            if key == b'H':  # Up arrow
                return 'up'
            elif key == b'P':  # Down arrow
                return 'down'
        elif key == b'\r':  # Enter
            return 'enter'
        elif key == b'q':
            return 'q'
        return None
    else:
        # Unix/Linux/macOS
        if not os.isatty(sys.stdin.fileno()):
            raise RuntimeError("This program requires an interactive terminal")
            
        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(sys.stdin.fileno())
            key = sys.stdin.read(1)
            if key == '\x1b':  # ESC sequence
                key = sys.stdin.read(2)
                if key == '[A':  # Up arrow
                    return 'up'
                elif key == '[B':  # Down arrow
                    return 'down'
            elif key == '\r' or key == '\n':  # Enter
                return 'enter'
            elif key == 'q':
                return 'q'
            return None
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def interactive_menu():
    """Run interactive menu with arrow key navigation."""
    selected_index = 0
    
    # Calculate total number of items
    total_items = sum(len(section.items) for section in MENU_SECTIONS) + 1  # +1 for exit
    
    while True:
        console.clear()
        display, all_items = create_menu_display(selected_index)
        console.print(display)
        
        key = get_key()
        
        if key == 'up':
            selected_index = (selected_index - 1) % total_items
        elif key == 'down':
            selected_index = (selected_index + 1) % total_items
        elif key == 'enter':
            item = all_items[selected_index]
            return item  # Return the MenuItem or None for exit
        elif key == 'q':
            return None


def check_platform(required_platforms):
    """Check if current platform is supported."""
    if "all" in required_platforms:
        return True
    
    current = platform.system()
    return current in required_platforms


def run_dedrm_script(module, function, args):
    """Run a DeDRM script with the given arguments."""
    try:
        # Try to import and run directly first
        module_path = f"DeDRM_plugin.{module}"
        mod = __import__(module_path, fromlist=[function])
        func = getattr(mod, function)
        
        # Call with args
        sys.argv = [module] + args
        func()
        return True
        
    except Exception as e:
        console.print(f"[red]Error running script: {e}[/red]")
        
        # Fallback to subprocess
        try:
            cmd = ["python", "-m", f"DeDRM_plugin.{module}"] + args
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.stdout:
                console.print(result.stdout)
            if result.stderr:
                console.print(f"[yellow]{result.stderr}[/yellow]")
                
            return result.returncode == 0
            
        except Exception as e2:
            console.print(f"[red]Subprocess error: {e2}[/red]")
            return False


def handle_menu_item(item):
    """Handle menu selection."""
    if item is None:  # Exit was selected
        return
    
    # Check platform compatibility
    if not check_platform(item.platforms):
        console.print(f"[red]This tool is not available on {platform.system()}[/red]")
        console.print(f"Supported platforms: {', '.join(item.platforms)}")
        Prompt.ask("Press Enter to continue")
        return
    
    console.clear()
    console.print(f"[bold cyan]{item.title}[/bold cyan]")
    console.print("-" * len(item.title))
    console.print(f"\n{item.description}\n")
    
    # Run the function
    try:
        success = item.fn()
        if success is None:
            success = True  # Assume success if function doesn't return value
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Operation cancelled by user[/yellow]")
        success = False
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        success = False
    
    if not success:
        console.print("\n[red]✗ Operation failed or was cancelled[/red]")
    
    Prompt.ask("\nPress Enter to continue")


def create_parser():
    """Create argument parser."""
    parser = argparse.ArgumentParser(
        prog='efm-setup',
        description='Interactive DRM configuration tool for EFM'
    )
    
    parser.add_argument(
        '--version',
        action='version',
        version='%(prog)s 1.0.0'
    )
    
    return parser


def main():
    """Main entry point."""
    parser = create_parser()
    args = parser.parse_args()
    
    try:
        # Interactive menu loop
        while True:
            item = interactive_menu()
            
            if item is None:
                console.print("\n[cyan]Thanks for using EFM Setup![/cyan]")
                break
            
            handle_menu_item(item)
            
    except KeyboardInterrupt:
        console.print("\n\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"\n[red]Unexpected error: {e}[/red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
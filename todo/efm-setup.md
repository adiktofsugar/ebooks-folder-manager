# efm-setup CLI Implementation Plan

## Overview
This document outlines the plan for implementing `efm-setup`, an interactive CLI tool that provides easy access to DRM configuration and key extraction scripts.

## Background and Decision Process

### Initial Request
Add a new feature to the main efm CLI that handles config setup through an interactive CLI program.

### Alternatives Considered
1. **--config flag**: `efm --config` - Start interactive setup from main command
2. **Subcommand**: `efm config` - Similar to git's approach
3. **Init/setup command**: `efm init` or `efm setup` 
4. **Wizard flag**: `efm --wizard` or `efm --setup-wizard`
5. **Generate config**: `efm --generate-config` - Create template with comments
6. **Config subcommands**: `efm config init/set/get/validate`
7. **Separate command**: `efm-setup` - Standalone setup tool

### Final Decision
Create `efm-setup` as a separate command with advantages:
- Clear separation of concerns
- Simpler argument parsing
- Can be run independently
- Follows Unix philosophy (each tool does one thing well)
- Easy to document
- Pattern used by many tools (jupyter vs jupyter-notebook, pip vs pip-compile)

## Core Goals
1. Provide easy access to DRM-related scripts in DeDRM_plugin
2. Guide users through key extraction and configuration
3. Eliminate need to remember individual script names and arguments
4. Create user-friendly interface for complex DRM setup tasks

## Implementation Plan

### 1. Directory Structure
```
efm/
├── setup/
│   ├── __init__.py
│   └── __main__.py
```

### 2. Entry Point Configuration
Add to `pyproject.toml`:
```toml
[project.scripts]
efm-setup = "efm.setup.__main__:main"
```

### 3. Available DeDRM Scripts

#### Adobe DRM Tools
- **getadobekey** (`adobekey:cli_main`)
  - Extract Adobe Digital Editions keys
  - Platform: Windows/Wine/macOS only
  - Usage: `getadobekey [outputdir]`

- **epubtest** (`epubtest:main`)
  - Test EPUB DRM type
  - Usage: `epubtest <epub_file>`

- **epubdecrypt** (`ineptepub:cli_main`)
  - Decrypt Adobe DRM EPUB
  - Usage: `epubdecrypt <key> <infile> <outfile>`

- **ineptpdf** (`ineptpdf:cli_main`)
  - Decrypt Adobe DRM PDF
  - Similar usage to epubdecrypt

#### Kindle DRM Tools
- **kindlekey** (`kindlekey:cli_main`)
  - Extract Kindle for PC/Mac keys

- **androidkindlekey** (`androidkindlekey:cli_main`)
  - Extract Kindle for Android keys

- **kindlepid** (`kindlepid:cli_main`)
  - Generate Kindle PID from serial

- **mobidedrm** (`mobidedrm:cli_main`)
  - Remove DRM from Mobi files

- **k4mobidedrm** (`k4mobidedrm:cli_main`)
  - Remove DRM from Kindle files

#### Barnes & Noble DRM Tools
- **ignoblekeyNookStudy** (`ignoblekeyNookStudy:cli_main`)
  - Extract Nook Study keys

- **ignoblekeyGenPassHash** (`ignoblekeyGenPassHash:cli_main`)
  - Generate B&N passphrase hash

### 4. Menu Structure
```
EFM Setup - DRM Configuration Tool
==================================

Please select an option:

Adobe DRM Tools:
  1. Extract Adobe Digital Editions keys
  2. Test EPUB DRM type
  3. Decrypt Adobe EPUB
  4. Decrypt Adobe PDF

Kindle DRM Tools:
  5. Extract Kindle for PC/Mac keys
  6. Extract Kindle for Android keys
  7. Generate Kindle PID
  8. Remove DRM from Mobi file
  9. Remove DRM from Kindle file

Barnes & Noble DRM Tools:
  10. Extract Nook Study keys
  11. Generate B&N passphrase hash

Other Options:
  12. Save extracted keys to config
  13. Exit

Selection: 
```

### 5. Implementation Details

#### Main Menu Loop
```python
import sys
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, IntPrompt
from rich.table import Table
import subprocess

console = Console()

def main():
    while True:
        show_menu()
        choice = IntPrompt.ask("Selection", default=13)
        
        if choice == 13:
            break
            
        handle_choice(choice)
```

#### Script Execution
- Use `subprocess.run()` to execute DeDRM scripts
- Capture and display output
- Handle platform-specific requirements (e.g., Windows-only scripts)
- Prompt for required arguments
- Show usage instructions before execution

#### Key Management
- After successful key extraction, offer to save to config
- Support all config formats (TOML, YAML, JSON)
- Update existing config or create new one
- Store keys in appropriate config fields:
  - `adobe_key_files`
  - `kindle_database_files`
  - `kindle_android_files`
  - etc.

### 6. Error Handling
- Check platform compatibility for platform-specific scripts
- Validate file paths and arguments
- Provide clear error messages
- Offer troubleshooting suggestions

### 7. Future Enhancements
- Config validation and testing
- Batch operations
- Key backup/restore functionality
- Integration with main efm workflow
- Auto-detection of installed ebook readers

## Development Notes
- Use existing `rich` dependency for UI
- Leverage existing `Config` class from `efm.config`
- Ensure compatibility with existing efm workflow
- Add appropriate logging for debugging
- Consider adding --non-interactive flag for automation

## Testing Approach
1. Test menu navigation
2. Verify script execution with mock subprocess
3. Test config file creation/update
4. Platform compatibility testing
5. Error handling scenarios
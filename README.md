# STALKER 2 Mod Merging Script
#### (Original Credits to 63OR63)

## Description
```
A tool designed to help merge multiple STALKER 2 mods, resolving conflicts between pak files automatically where possible and providing tools for manual merging where needed.
```

## Key Features
```
• Automatic detection of mod conflicts
• Visual file tree display of all mod contents
• Automatic merging of non-conflicting files
• Guided manual merging process for conflicting files using WinMerge
• Automatic backup creation of original pak files (with *.pakbackup filename extension)
• Validation of merged pak files
• Detailed logging and error handling
```

## Requirements
```
• Python 3.x installed and added to system PATH
• WinMerge installed (https://winmerge.org/) (installed in users local appdata folder but can be installed anywhere)
• Repak CLI tool installed (GitHub: repak_cli-x86_64-pc-windows-msvc.msi)
```

## Installation
```
1. Download and extract the tool to a convenient location
2. Open "1_Mod_Merging_Helper_v0.2.py" in a text editor
3. Locate the following lines near the top:

    MODS = r"E:\s2hoc\Stalker2\Content\Paks\~mods"
    REPAK_PATH = r"C:\Program Files\repak_cli\repak.exe"  (sometimes also in the bin folder)

4. Change the MODS path to match your STALKER 2 mods folder location
```

## Usage
```
Method 1 - Using Batch File (Recommended)
    1. Simply drag and drop your .pak files onto "1bat.bat"
    2. The tool will automatically start processing the files

Method 2 - Using Python Script Directly
    1. Open command prompt in the tool's directory
    2. Run: python "1_Mod_Merging_Helper_v0.2.py" [pak files]
```

## How It Works
```
1. The tool analyzes all provided pak files for conflicts
2. Non-conflicting files are automatically merged
3. For conflicting files: must use winmerge to review each file (most reliable method by far)
    • Files are extracted to a temporary folder in the same spot your pak files are in
    • User opens WinMerge for manual conflict resolution
    • Follow the on-screen instructions to merge conflicts
4. Original conflicting pak files are renamed to .pakbackup after the merge process fully completes
5. A new merged pak file (ZZZZZZZ_Merged.pak) is created
```

## Important Notes
```
• Always backup your mods before merging
• The tool creates temporary directories during the merge process
• Original pak files are automatically backed up with .pakbackup extension
• Merged pak file is saved as "ZZZZZZZ_Merged.pak" in your mods folder
• A validation report is generated after merging
```

## Troubleshooting
```
• If WinMerge isn't found, verify its installation path
• Check the validation_report.txt for details about any merge issues
• If a merge fails, original .pakbackup files can be renamed back to .pak
• corrupt_paks.log will list any corrupted pak files encountered
```

## Known Limitations
```
• Requires manual intervention for resolving complex conflicts
• WinMerge must be installed for conflict resolution
```

## Support
```
For issues or questions, please post in the comments section. Include any relevant error messages and the contents of validation_report.txt if applicable.
```

## Why
```
I wanted a extended version of the original python script, and with more verification and validation of files.
```

## Credits
```
Original concept created by 63OR63
Heavily modified by nova

Endorse if you find this tool useful!
```

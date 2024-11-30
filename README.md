# STALKER 2 Python Mod Merging Script

## (Original Credits to 63OR63) 

## Description
A tool designed to help merge multiple STALKER 2 mods, resolving conflicts between pak files automatically where possible and providing tools for manual merging where needed.

--

## Key Features
1. Automatic display and detection of mod conflicts for each conflicting file (cfg file, etc)
2. Visual file tree display of all mod contents
3. Automatic merging of non-conflicting files
4. Guided manual merging process for conflicting files using WinMerge
5. Automatic backup creation of original pak files (with *.pakbackup filename extension)
6. Validation of merged pak files
7. Detailed logging and error handling


## Requirements
1. Python 3.11 or newer installed and added to system PATH
2. WinMerge installed (https://winmerge.org/) (installed in users local appdata folder but can be installed anywhere)
3. Repak CLI tool installed GitHub link: https://github.com/trumank/repak/releases/download/v0.2.2/repak_cli-x86_64-pc-windows-msvc.msi


# Usage

1. Simply drag and drop your .pak files onto "1 drag & drop pak files onto this bat file.bat"
2. The tool will automatically start processing the pak files

## Notes

1. Merged pak file is saved as "ZZZZZZZ_Merged.pak" in your mods folder
2. Original pak files are automatically backed up with .pakbackup extension
3. The tool creates temporary directories during the merge process
4. A validation report is generated after merging



# Winmerge Tips and Tricks for Merging Files
1. When you open the cfg files to compare, differences are automatically highlighted

2. Use Alt + Up/Down arrow keys on your keyboard to jump to each difference

3. For each difference:
    Alt + Left arrow key copies changes from left file to the right file
    and
    Alt + Right arrow key copies changes from right file to the left file

4. make sure you copy all changes you want saved to the same cfg file each time
5. Use Ctrl + D to focus only on differences when files are large

**Pro Tip:** If you're comparing large files, start with Ctrl + D to show only
differences, then use Alt + Up/Down to navigate through changes more
quickly.


# Installation / Configuration
*(needed only if mods folder not found in common default locations)*

1. Download and extract the tool to a convenient location
    
2. Open "1_Python_Merging_s2hoc.py" in a text editor
   Locate the following line near the top:
   ```
   CUSTOM_MODS_PATH = r"E:\s2hoc\Stalker2\Content\Paks\~mods"
   ```
   Change the MODS path to match your STALKER 2 mods folder location



## How It Works
1. The tool analyzes all provided pak files for conflicts
2. Non-conflicting files are automatically merged
3. For conflicting files: must use winmerge to review each file (most reliable method by far)
    • Files are extracted to a temporary folder in the same spot your pak files are in
    • User opens WinMerge for manual conflict resolution
    • Follow the on-screen instructions to merge conflicts
4. Original conflicting pak files are renamed to .pakbackup after the merge process fully completes
5. A new merged pak file (ZZZZZZZ_Merged.pak) is created


## Troubleshooting
1. If WinMerge isn't found, verify its installation path
2. Check the validation_report.txt for details about any merge issues
3. If a merge fails, original .pakbackup files can be renamed back to .pak
4. corrupt_paks.log will list any corrupted pak files encountered

## Known Limitations
1. Requires manual intervention for resolving complex conflicts
2. WinMerge must be installed for conflict resolution


## Support
For issues or questions, please post in the comments section. Include any relevant error messages and the contents of validation_report.txt if applicable.

## Why
I wanted a extended version of the original python script, and with more verification and validation of files.

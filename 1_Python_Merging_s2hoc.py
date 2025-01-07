import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import hashlib



# 
# Python Merge on nexusmods modifed by Takashi
# 
# credits to 63OR63 for original script
# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description



# Custom mods folder path - edit this if your Stalker 2 mods folder is in a different location
CUSTOM_MODS_PATH = r"E:\s2hoc\Stalker2\Content\Paks\~mods"



SCRIPT_VERSION = "2.4.2" 


# Add with other globals at top
VALIDATION_MESSAGES = []  # Buffer to store messages for report



def color_text(text, color):
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m",
    }
    return f"{colors[color]}{text}{colors['reset']}"




# These need to be defined BEFORE the PakCache class since it uses TEMP_UNPACK_DIR
TEMP_UNPACK_DIR = Path(__file__).parent / "temp_unpack"
TEMP_REPACK_DIR = Path(__file__).parent / "temp_repack"
TEMP_MERGE_DIR = Path(__file__).parent / "temp_merge"
TEMP_BACKUP_DIR = Path(__file__).parent / "temp_backup"
TEMP_HASH_DIR = Path(__file__).parent / "temp_hash"
TEMP_VALIDATION_DIR = Path(__file__).parent / "temp_validation"  # Add this line
VANILLA_DIR = Path(__file__).parent / "vanilla"


# Not used for now.
KDIFF3_PATH = r"C:\Program Files\KDiff3\kdiff3.exe"

# Add this with other configuration variables at top
VALIDATE_MERGED_PAK = True  # Set to False to disable merged pak validation
VALIDATION_DIR = Path(__file__).parent / "temp_validation"  # New temp directory for validation



######### Don't edit anything beneath this line! #########


def log_for_report(message, message_type="info"):
    """Version 1.0 - Logs message to both console and report buffer
    Args:
        message (str): Message to log
        message_type (str): "info", "error", "success", "warning"
    """
    # Print to console with color
    if message_type == "error":
        print(color_text(message, "red"))
    elif message_type == "success":
        print(color_text(message, "green"))
    elif message_type == "warning":
        print(color_text(message, "yellow"))
    else:
        print(color_text(message, "cyan"))
        
    # Store for report
    VALIDATION_MESSAGES.append((message_type, message))



def shorten_path(path, marker="~mods"):
    """Version 1.0 - Shortens path display by removing everything before marker"""
    try:
        path_str = str(path)
        marker_index = path_str.find(marker)
        if marker_index != -1:
            return path_str[marker_index:]
        return path_str
    except:
        return path_str


def find_repak_path():
    """Version 1.0 - Smart REPAK path detection"""
    possible_paths = [
        r"C:\Program Files\repak_cli\bin\repak.exe",
        r"C:\Program Files\repak_cli\repak.exe"
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    return None

def find_winmerge_path():
    """Version 1.0 - Smart WinMerge path detection"""
    possible_paths = [
        os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'WinMerge', 'WinMergeU.exe'),
        r"C:\Program Files\WinMerge\WinMergeU.exe"
    ]
    for path in possible_paths:
        if os.path.isfile(path):
            return path
    return None



def find_stalker2_mods_path():
    """Version 1.2 - Smart Stalker 2 mods directory detection
    - Added custom path priority
    - Improved validation and feedback
    - Enhanced path detection
    """
    # Configuration
    GAME_SUBPATH = r"steamapps\common\S.T.A.L.K.E.R. 2 Heart of Chornobyl\Stalker2\Content\Paks\~mods"
    STEAM_PATTERNS = ['steam', 'SteamLibrary']
    DRIVE_LETTERS = list(f"{d}:" for d in 'CDEFGHIJ')  # Extended drive letter support

    def validate_mods_directory(path):
        """Helper function to validate mods directory structure"""
        try:
            if not os.path.isdir(path):
                return False
            parent_paks = os.path.dirname(path)
            if not os.path.basename(path) == "~mods":
                return False
            if not os.path.basename(parent_paks) == "Paks":
                return False
            return True
        except Exception:
            return False

    # Build and check paths
    found_paths = []
    checked_paths = []

    # First check custom path from user setting
    if CUSTOM_MODS_PATH:
        custom_path = os.path.normpath(CUSTOM_MODS_PATH)
        checked_paths.append(custom_path)
        if os.path.exists(custom_path):
            if validate_mods_directory(custom_path):
                print(color_text(f"\nFound custom mods directory: {custom_path}", "green"))
                return custom_path
            else:
                print(color_text(f"Warning: Custom path exists but doesn't appear to be a valid mods directory: {custom_path}", "yellow"))
        else:
            print(color_text(f"Note: Custom mods path not found, checking standard locations: {custom_path}", "yellow"))

    # Check Steam paths
    for drive in DRIVE_LETTERS:
        for steam_dir in STEAM_PATTERNS:
            try:
                full_path = os.path.normpath(os.path.join(drive, steam_dir, GAME_SUBPATH))
                checked_paths.append(full_path)
                if os.path.exists(full_path) and validate_mods_directory(full_path):
                    found_paths.append(full_path)
            except Exception as e:
                print(color_text(f"Error checking path {full_path}: {str(e)}", "yellow"))
                continue

    # Handle results
    if not found_paths:
        print(color_text("\nError: Could not find Stalker 2 mods directory in any location:", "red"))
        print(color_text("\nChecked locations:", "yellow"))
        for path in checked_paths:
            print(color_text(f"- {path}", "yellow"))
        print(color_text("\nPlease ensure Stalker 2 is installed or set CUSTOM_MODS_PATH at the top of the script.", "red"))
        return None
    
    # If multiple valid installations found
    if len(found_paths) > 1:
        print(color_text("\nMultiple Stalker 2 installations found:", "yellow"))
        for i, path in enumerate(found_paths, 1):
            print(color_text(f"{i}. {path}", "cyan"))
        
        # User selection with retry logic
        max_attempts = 3
        for attempt in range(max_attempts):
            try:
                choice = input(color_text("\nPlease select which installation to use (enter number): ", "cyan"))
                index = int(choice) - 1
                if 0 <= index < len(found_paths):
                    selected_path = found_paths[index]
                    print(color_text(f"\nSelected mods directory: {selected_path}", "green"))
                    return selected_path
                print(color_text(f"Invalid selection. Please enter 1-{len(found_paths)}", "red"))
            except ValueError:
                print(color_text("Please enter a valid number.", "red"))
            if attempt == max_attempts - 1:
                print(color_text("\nToo many invalid attempts. Using first found path.", "yellow"))
                return found_paths[0]
    
    # Single path found
    selected_path = found_paths[0]
    print(color_text(f"\nFound mods directory: {selected_path}", "green"))
    return selected_path




REPAK_PATH = find_repak_path()
if not REPAK_PATH:
    print(color_text("Error: Could not find repak.exe in any of the expected locations:", "red"))
    print(color_text("- C:\\Program Files\\repak_cli\\bin\\repak.exe", "yellow"))
    print(color_text("- C:\\Program Files\\repak_cli\\repak.exe", "yellow"))
    print(color_text("\nPlease install repak or correct the path at the top of the script.", "red"))
    input(color_text("\nPress enter to close...", "cyan"))
    sys.exit(1)


WINMERGE_PATH = find_winmerge_path()
if not WINMERGE_PATH:
    print(color_text("Warning: Could not find WinMerge in any of the expected locations:", "yellow"))
    print(color_text("- %LOCALAPPDATA%\\Programs\\WinMerge\\WinMergeU.exe", "yellow"))
    print(color_text("- C:\\Program Files\\WinMerge\\WinMergeU.exe", "yellow"))
    print(color_text("\nWinMerge is required for this script to function properly.", "yellow"))



MODS = find_stalker2_mods_path()
if not MODS:
    input(color_text("\nPress enter to close...", "cyan"))
    sys.exit(1)







def create_unique_temp_dir(base_path, prefix):
    """Version 1.0 - Create unique temporary directory"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_dir = base_path / f"{prefix}_{timestamp}"
    
    # Try to create directory with retry logic
    max_attempts = 5
    for attempt in range(max_attempts):
        try:
            if not unique_dir.exists():
                unique_dir.mkdir(parents=True)
                return unique_dir
            # If directory exists, append attempt number
            unique_dir = base_path / f"{prefix}_{timestamp}_{attempt}"
        except Exception as e:
            if attempt == max_attempts - 1:
                raise Exception(f"Failed to create unique directory after {max_attempts} attempts: {e}")
            time.sleep(0.1)  # Small delay before retry
    
    return unique_dir



class PakCache:
    """Version 1.0 - Manages pak extraction and caching"""
    
    def __init__(self, max_cache_size=None):
        self.extracted_paks = {}
        self.file_hashes = {}
        self.extraction_root = TEMP_UNPACK_DIR
        self.max_cache_size = max_cache_size  # in bytes, None means unlimited


    def get_extracted_path(self, pak_path, file_entry=None):
        """Get path to extracted pak or specific file"""
        if pak_path not in self.extracted_paks:
            return None
        if file_entry:
            return self.extracted_paks[pak_path] / file_entry.replace('/', os.sep)
        return self.extracted_paks[pak_path]



    # Update extract_pak method in PakCache class:
    def extract_pak(self, pak_path):
        """Version 2.1 - Added unique directory handling"""
        if pak_path in self.extracted_paks:
            return self.extracted_paks[pak_path]

        mod_name = Path(pak_path).stem
        try:
            extract_dir = create_unique_temp_dir(self.extraction_root, mod_name)
            
            result = subprocess.run(
                [REPAK_PATH, "unpack", pak_path, "--output", str(extract_dir)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode == 0:
                self.extracted_paks[pak_path] = extract_dir
                return extract_dir
            else:
                print(color_text(f"Error extracting {pak_path}: {result.stderr}", "red"))
                # Cleanup failed extraction
                if extract_dir.exists():
                    shutil.rmtree(extract_dir, ignore_errors=True)
                return None
                
        except Exception as e:
            print(color_text(f"Exception extracting {pak_path}: {e}", "red"))
            return None


    def get_file_hash(self, pak_path, file_entry):
        """Version 2.2 - Improved resource management and error handling"""
        cache_key = (pak_path, file_entry)
        if cache_key in self.file_hashes:
            return self.file_hashes[cache_key]

        extracted_path = self.get_extracted_path(pak_path, file_entry)
        if not extracted_path or not extracted_path.exists():
            if not self.extract_pak(pak_path):
                return None
            extracted_path = self.get_extracted_path(pak_path, file_entry)

        file_size = None
        file_hash = None
        
        try:
            # Get file size first
            file_size = extracted_path.stat().st_size
            
            # Compute hash with proper resource management
            md5_hash = hashlib.md5()
            try:
                with open(extracted_path, "rb") as f:
                    while True:
                        chunk = f.read(65536)
                        if not chunk:
                            break
                        md5_hash.update(chunk)
                file_hash = md5_hash.hexdigest()
                
                # Only cache if both operations succeeded
                self.file_hashes[cache_key] = (file_size, file_hash)
                return (file_size, file_hash)
                
            except IOError as io_err:
                print(color_text(f"IO Error reading file {file_entry}: {io_err}", "red"))
                return None
                
        except Exception as e:
            print(color_text(f"Error computing hash for {file_entry}: {e}", "red"))
            return None











# Initialize global pak cache
pak_cache = PakCache()









def execute_repak_list(pak_file):
    """Version 2.0 - Cache aware repak list execution"""
    global pak_cache  # Add this line to make it explicit we're using global
    try:
        # Check if pak is already extracted in cache
        if pak_file in pak_cache.extracted_paks:
            # Get file listing from extracted directory
            extracted_dir = pak_cache.extracted_paks[pak_file]
            files = []
            for root, _, filenames in os.walk(extracted_dir):
                for filename in filenames:
                    rel_path = os.path.relpath(os.path.join(root, filename), extracted_dir)
                    files.append(rel_path.replace('\\', '/'))
            return files
            
        # If not in cache, use repak list command
        result = subprocess.run(
            [REPAK_PATH, "list", pak_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(color_text(f"Error processing {pak_file}: {error_msg}", "red"))
            return None
        return result.stdout.strip().splitlines()
    except Exception as e:
        print(color_text(f"Failed to run repak.exe on {pak_file}: {e}", "red"))
        return None









def get_file_size_from_pak(pak_file, file_entry):
    """Version 2.0 - Gets file size from extracted file instead of repak command"""
    try:
        # Get file from cache or extract it
        extracted_path = pak_cache.get_extracted_path(pak_file, file_entry)
        if not extracted_path or not extracted_path.exists():
            if not pak_cache.extract_pak(pak_file):
                return 'Unknown'
            extracted_path = pak_cache.get_extracted_path(pak_file, file_entry)
            
        if extracted_path and extracted_path.exists():
            return str(extracted_path.stat().st_size)
        return 'Unknown'
    except Exception as e:
        return 'Unknown'







def build_file_tree(pak_sources):
    """Version 2.5 - Enhanced error handling and progress tracking, removed size command dependency
    Builds file tree from PAK sources with comprehensive validation and source deduplication
    """
    file_tree = {}
    file_count = defaultdict(int)
    file_sources = defaultdict(list)
    file_hashes = defaultdict(dict)
    
    total_files = len(pak_sources)
    processed = 0
    errors = []
    skipped = []
    
    print(color_text(f"\nBuilding file tree from {total_files} entries...", "cyan"))
    
    try:
        update_interval = max(1, min(100, total_files // 20))
        last_percentage = -1
        
        for pak_file, entry in pak_sources:
            processed += 1
            current_percentage = (processed * 100) // total_files
            
            if current_percentage != last_percentage and processed % update_interval == 0:
                print(color_text(f"→ Progress: {current_percentage}% ({processed}/{total_files})", "cyan"))
                last_percentage = current_percentage
            
            try:
                if not entry or not isinstance(entry, str):
                    skipped.append((pak_file, entry, "Invalid entry format"))
                    continue
                
                parts = entry.split('/')
                if not parts:
                    skipped.append((pak_file, entry, "Empty path structure"))
                    continue
                
                if not all(is_valid_path_component(part) for part in parts):
                    skipped.append((pak_file, entry, "Invalid path component"))
                    continue
                
                current_level = file_tree
                for part in parts[:-1]:
                    current_level = current_level.setdefault(part, {})
                    if not isinstance(current_level, dict):
                        raise ValueError(f"Path conflict: {entry}")
                
                file_name = parts[-1]
                current_level[file_name] = None
                
                file_count[entry] += 1
                mod_name = Path(pak_file).stem
                
                # New deduplication check before adding source
                if not any(source[1] == pak_file for source in file_sources[entry]):
                    file_sources[entry].append([mod_name, pak_file])
                
                # Get file size and hash from extracted file
                try:
                    extracted_path = pak_cache.get_extracted_path(pak_file, entry)
                    if extracted_path and extracted_path.exists():
                        file_size = extracted_path.stat().st_size
                        md5_hash = hashlib.md5()
                        with open(extracted_path, "rb") as f:
                            for chunk in iter(lambda: f.read(65536), b''):
                                md5_hash.update(chunk)
                        file_hash = md5_hash.hexdigest()
                        file_hashes[entry][mod_name] = (file_size, file_hash)
                    else:
                        error_msg = f"Failed to get hash for {entry} in {mod_name}"
                        errors.append((pak_file, entry, error_msg))
                        file_hashes[entry][mod_name] = ('Error', 'Error')
                except Exception as e:
                    error_msg = f"Hash calculation error: {str(e)}"
                    errors.append((pak_file, entry, error_msg))
                    file_hashes[entry][mod_name] = ('Error', 'Error')
                
            except Exception as e:
                errors.append((pak_file, entry, str(e)))
                continue
        
        # Generate statistics
        total_unique_files = len(file_sources)
        files_with_conflicts = sum(1 for count in file_count.values() if count > 1)
        
        # Print summary
        log_for_report("\nFile Analysis Summary:", "info")
        log_for_report(f"✓ Total entries processed: {processed}", "success")
        log_for_report(f"✓ Unique files found: {total_unique_files}", "success")
        log_for_report(f"→ Files with conflicts: {files_with_conflicts}", "warning" if files_with_conflicts else "success")

        
        if errors:
            print(color_text(f"\nProcessing Errors ({len(errors)}):", "red"))
            print(color_text("First 5 errors:", "red"))
            for pak, entry, error in errors[:5]:
                print(color_text(f"❌ {shorten_path(pak)} - {entry}: {error}", "red"))
            if len(errors) > 5:
                print(color_text(f"...and {len(errors) - 5} more errors", "red"))
        
        if skipped:
            print(color_text(f"\nSkipped Entries ({len(skipped)}):", "yellow"))
            print(color_text("First 5 skipped:", "yellow"))
            for pak, entry, reason in skipped[:5]:
                print(color_text(f"⚠️ {shorten_path(pak)} - {entry}: {reason}", "yellow"))
            if len(skipped) > 5:
                print(color_text(f"...and {len(skipped) - 5} more skipped", "yellow"))
        
        if not file_tree:
            raise ValueError("No valid file structure could be built")
        
        return file_tree, file_count, file_sources, file_hashes
        
    except Exception as e:
        error_context = {
            "operation": "File Tree Building",
            "processed_files": f"{processed}/{total_files}",
            "error": str(e),
            "impact": "File tree construction failed",
            "solution": "Check PAK file integrity and entry formats"
        }
        log_error_context(error_context)
        raise RuntimeError(f"Failed to build file tree: {str(e)}")






# Helper function for build_file_tree
def is_valid_path_component(component):
    """Version 1.0 - Validates individual path components"""
    if not component or not isinstance(component, str):
        return False
    # Add more specific validation as needed
    # Example: Check for invalid characters, length limits, etc.
    invalid_chars = '<>:"|?*'
    return not any(char in component for char in invalid_chars)






def is_merged_pak(pak_path):
    """Version 1.0 - Checks if a PAK file is the merged PAK
    
    Args:
        pak_path (Path): Path to PAK file
    
    Returns:
        bool: True if this is the merged PAK, False otherwise
    """
    return pak_path.name.startswith("ZZZZZZZ_Merged")







def handle_existing_merged_pak(mods_path):
    """Version 2.0 - Enhanced merged PAK handling with user options"""
    merged_pak = "ZZZZZZZ_Merged.pak"
    merged_pak_path = Path(mods_path) / merged_pak
    
    try:
        if merged_pak_path.exists():
            print(color_text(f"\nFound existing merged PAK: {shorten_path(merged_pak_path)}", "cyan"))
            
            # Show options to user
            print(color_text("\nChoose how to handle the existing merged PAK:", "magenta"))
            print(color_text("1 - Include this merged PAK in new merge process", "white"))
            print(color_text("2 - Backup this merged PAK and skip it", "white"))
            print(color_text("3 - Cancel operation", "white"))
            
            while True:
                try:
                    choice = input(color_text("\nEnter your choice (1-3): ", "cyan")).strip()
                    if choice == "1":
                        print(color_text("\n→ Including existing merged PAK in merge process...", "cyan"))
                        return {"success": True, "action": "include", "pak_path": merged_pak_path}
                    elif choice == "2":
                        # Create backup with timestamp
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        backup_name = f"ZZZZZZZ_Merged_OLD_{timestamp}.pakbackup"
                        backup_path = merged_pak_path.parent / backup_name
                        
                        try:
                            # Verify source file is accessible
                            if not os.access(merged_pak_path, os.W_OK):
                                print(color_text("❌ Cannot access existing merged PAK file", "red"))
                                return {"success": False, "error": "Access denied"}
                            
                            # Perform the rename
                            merged_pak_path.rename(backup_path)
                            print(color_text(f"✓ Backed up existing merged PAK to: {backup_name}", "green"))
                            return {"success": True, "action": "backup"}
                            
                        except Exception as e:
                            print(color_text(f"❌ Failed to backup existing merged PAK: {str(e)}", "red"))
                            return {"success": False, "error": str(e)}
                    elif choice == "3":
                        print(color_text("\nOperation cancelled by user.", "yellow"))
                        return {"success": False, "action": "cancel"}
                    else:
                        print(color_text("Invalid choice. Please enter 1, 2, or 3.", "red"))
                except ValueError:
                    print(color_text("Invalid input. Please enter a number.", "red"))
        
        return {"success": True, "action": "none"}  # No existing merged PAK
        
    except Exception as e:
        print(color_text(f"❌ Error handling existing merged PAK: {str(e)}", "red"))
        return {"success": False, "error": str(e)}






def wait_for_user_merge(file_name, merge_folder):
    """Version 1.0 - Waits for the user to complete the merge and checks for the final merged file."""
    final_merged_file = merge_folder.parent / f"final_merged_{file_name}"
    while True:
        if final_merged_file.exists():
            return final_merged_file
        else:
            print(color_text(f"Waiting for 'final_merged_{file_name}' to appear in {merge_folder.parent}...", "cyan"))
            time.sleep(5)  # Check every 5 seconds



def display_file_tree(file_tree, prefix="", file_count=None, full_path=""):
    """Version 1.1 - Added input validation"""
    # Validate inputs
    if not isinstance(file_tree, dict):
        print(color_text("Error: file_tree must be a dictionary", "red"))
        return
        
    if not isinstance(prefix, str):
        prefix = ""
        print(color_text("Warning: prefix must be a string, using empty string", "yellow"))
        
    if file_count is not None and not isinstance(file_count, dict):
        print(color_text("Error: file_count must be a dictionary or None", "red"))
        return
        
    if not isinstance(full_path, str):
        full_path = ""
        print(color_text("Warning: full_path must be a string, using empty string", "yellow"))

    # Original display logic
    for key, value in sorted(file_tree.items()):
        current_path = f"{full_path}/{key}".strip("/")
        if isinstance(value, dict):
            print(color_text(f"{prefix}{key}/", "blue"))
            display_file_tree(value, prefix=prefix + "    ", 
                            file_count=file_count, full_path=current_path)
        else:
            count = file_count.get(current_path, 1) if file_count else 1
            marker = f"(*)[{count}]" if count > 1 else ""
            color = "yellow" if marker else "green"
            print(color_text(f"{prefix}{marker}{key}", color))






def process_pak_files(pak_files, pak_cache):
    """Version 2.8 - Enhanced error handling and feedback, removed size command dependency
    
    Args:
        pak_files (list): List of PAK file paths to process
        pak_cache (PakCache): Cache object for PAK operations
        
    Returns:
        list: List of tuples containing (pak_file, entry) pairs
    """
    pak_sources = []
    total_paks = len(pak_files)
    processed_paks = 0
    failed_paks = []
    skipped_entries = []

    if not isinstance(pak_cache, PakCache):
        raise ValueError("Invalid pak_cache object provided")

    print(color_text(f"\nAnalyzing {total_paks} PAK files...", "cyan"))

    for index, pak_file in enumerate(pak_files, 1):
        try:
            # Clear status line and show current progress
            print(color_text(f"\n[Processing PAK {index} of {total_paks}]", "white"))
            print(color_text(f"File: {shorten_path(pak_file)}", "white"))

            # Initial PAK validation
            print(color_text("→ Validating PAK structure...", "cyan"))
            is_valid, error_message = validate_pak_file(pak_file)
            
            if not is_valid:
                error_context = {
                    "operation": "PAK Validation",
                    "file": shorten_path(pak_file),
                    "error": error_message,
                    "impact": "PAK will be skipped",
                    "solution": "Check if PAK file is corrupted or incorrectly formatted"
                }
                log_error_context(error_context)
                failed_paks.append((pak_file, error_message))
                continue

            # Extract to cache with progress feedback
            print(color_text("→ Extracting PAK contents...", "cyan"))
            extract_path = pak_cache.extract_pak(pak_file)
            
            if not extract_path:
                error_context = {
                    "operation": "PAK Extraction",
                    "file": shorten_path(pak_file),
                    "error": "Failed to extract PAK contents",
                    "impact": "PAK will be skipped",
                    "solution": "Check disk space and permissions"
                }
                log_error_context(error_context)
                failed_paks.append((pak_file, "Extraction failed"))
                continue

            # Process file entries using standard list command
            print(color_text("→ Reading file entries...", "cyan"))
            result = subprocess.run(
                [REPAK_PATH, "list", pak_file],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            if result.returncode != 0:
                error_context = {
                    "operation": "File Entry Reading",
                    "file": shorten_path(pak_file),
                    "error": result.stderr.strip(),
                    "impact": "PAK will be skipped",
                    "solution": "Check if PAK format is supported"
                }
                log_error_context(error_context)
                failed_paks.append((pak_file, "Failed to read entries"))
                continue

            file_entries = result.stdout.strip().splitlines()

            # Process entries with validation
            valid_entries = 0
            for entry in file_entries:
                try:
                    if not entry.strip():
                        continue
                        
                    # Validate entry path
                    if not is_valid_file_entry(entry):
                        skipped_entries.append((pak_file, entry, "Invalid entry format"))
                        continue

                    pak_sources.append((pak_file, entry))
                    valid_entries += 1

                except Exception as e:
                    skipped_entries.append((pak_file, entry, str(e)))

            processed_paks += 1
            print(color_text(f"✓ Processed {valid_entries} valid entries", "green"))

        except Exception as e:
            error_context = {
                "operation": "PAK Processing",
                "file": shorten_path(pak_file),
                "error": str(e),
                "impact": "PAK will be skipped",
                "solution": "Check PAK file integrity"
            }
            log_error_context(error_context)
            failed_paks.append((pak_file, str(e)))


    # # Final summary
    # log_for_report("\nProcessing Summary:", "info")
    # log_for_report(f"✓ Successfully processed: {processed_paks} of {total_paks} PAKs", "success")

    # if failed_paks:
    #     log_for_report(f"\nFailed PAKs ({len(failed_paks)}):", "error")
    #     for pak, error in failed_paks:
    #         log_for_report(f"❌ {shorten_path(pak)}: {error}", "error")



    # New version
    log_for_report("\nProcessing Summary:", "info")
    log_for_report(f"✓ Successfully processed: {processed_paks} of {total_paks} PAKs", "success")

    if failed_paks:
        # Show failures prominently
        print("\nCRITICAL ERRORS FOUND:")
        print("="*50)
        print(f"Failed to process {len(failed_paks)} PAKs:")
        for pak, error in failed_paks:
            print(f"❌ {shorten_path(pak)}: {error}")
        print("="*50)
        
        # Single prompt to continue
        if not yes_or_no("\nContinue processing all files? (Additional errors will be shown in console and log file)"):
            raise RuntimeError("Processing halted due to PAK failures")

        # Still log failures for report
        log_for_report(f"\nFailed PAKs ({len(failed_paks)}):", "error")
        for pak, error in failed_paks:
            log_for_report(f"❌ {shorten_path(pak)}: {error}", "error")





    if skipped_entries:
        print(color_text(f"\nSkipped Entries ({len(skipped_entries)}):", "yellow"))
        print(color_text("First 5 skipped entries:", "yellow"))
        for pak, entry, reason in skipped_entries[:5]:
            print(color_text(f"⚠️ {shorten_path(pak)} - {entry}: {reason}", "yellow"))
        if len(skipped_entries) > 5:
            print(color_text(f"...and {len(skipped_entries) - 5} more", "yellow"))

    if not pak_sources:
        error_msg = "No valid files were processed from any PAK file"
        print(color_text(f"\n❌ {error_msg}", "red"))
        raise ValueError(error_msg)

    return pak_sources



# Helper functions needed for process_pak_files

def is_valid_file_entry(entry):
    """Version 1.0 - Validates file entry format"""
    if not isinstance(entry, str):
        return False
    if not entry.strip():
        return False
    # Add more specific validation as needed
    return True

def log_error_context(context):
    """Version 1.0 - Logs error context in a structured format"""
    print(color_text("\nError Details:", "red"))
    for key, value in context.items():
        print(color_text(f"→ {key.title()}: {value}", "yellow"))












def display_conflicts(conflicting_files, file_hashes):
    """Version 2.0 - Improved conflict display and organization"""
    total_conflicts = len(conflicting_files)
    print(color_text(f"\nConflicting Files Analysis:", "magenta"))
    print(color_text(f"Found {total_conflicts} conflicting files:", "magenta"))
    
    conflict_count = 0
    for file, sources in conflicting_files.items():
        conflict_count += 1
        hashes = file_hashes[file]
        
        # Get unique sizes and hashes for comparison
        unique_sizes = set(hash_data[0] for hash_data in hashes.values() if hash_data[0] != 'Error')
        unique_hashes = set(hash_data[1] for hash_data in hashes.values() if hash_data[1] != 'Error')
        
        print(color_text(f"\n[File {conflict_count} of {total_conflicts}] {file}", "yellow"))
        print(color_text(f"    Affected by {len(sources)} mods:", "red"))
        
        # Display each mod and its details
        for mod_name, pak_file in sources:
            size, hash_value = hashes.get(mod_name, ('Unknown', 'Unknown'))
            
            # Determine if this mod has different content but same size
            same_size_diff_hash = (
                len(unique_sizes) == 1 and 
                len(unique_hashes) > 1 and 
                hash_value != 'Error'
            )
            
            if same_size_diff_hash:
                print(color_text(f"    • {mod_name}.pak (Hash: {hash_value}) - Same size but different content", "white"))
            else:
                print(color_text(f"    • {mod_name}.pak (Size: {size} bytes, Hash: {hash_value})", "white"))







def unpack_sources(sources):
    """Version 1.0"""
    for source in sources:
        unpack_pak(source[1])
    time.sleep(1)




def unpack_pak(pak_file):
    """Version 2.0 - Uses PakCache for improved performance"""
    try:
        print(color_text(f"Unpacking {pak_file}...", "white"))
        
        if not os.path.isfile(pak_file):
            print(color_text(f"Error: The .pak file does not exist at {pak_file}", "red"))
            return False

        extracted_dir = pak_cache.extract_pak(pak_file)
        if extracted_dir and extracted_dir.exists():
            print(color_text(f"Successfully unpacked {pak_file} to {extracted_dir}", "green"))
            return extracted_dir
        else:
            print(color_text(f"Failed to locate unpacked folder for {pak_file}.", "red"))
            return False
    except Exception as e:
        print(color_text(f"Error unpacking {pak_file}: {e}", "red"))
        return False











def repack_pak():
    """Version 1.9 - Enhanced repack process with merged PAK handling"""
    merged_pak = "ZZZZZZZ_Merged.pak"
    merged_pak_path = Path(MODS) / merged_pak
    
    print(color_text(f"\nPreparing to repack merged files...", "cyan"))
    
    try:
        # First handle any existing merged PAK
        if not handle_existing_merged_pak(MODS):
            raise ValueError("Failed to handle existing merged PAK")
        
        # Pre-repack validation checks
        validation_results = perform_prerepack_checks(TEMP_REPACK_DIR, merged_pak_path)
        if not validation_results["success"]:
            raise ValueError(f"Pre-repack validation failed: {validation_results['error']}")
        
        # Print content statistics
        log_for_report("\nValidation Summary:", "info")
        log_for_report(f"✓ Available disk space: {validation_results['disk_space_gb']:.2f} GB", "success")
        log_for_report(f"✓ Files to pack: {validation_results['file_count']}", "success")
        log_for_report(f"✓ Total size: {validation_results['total_size_mb']:.2f} MB", "success")

        # Process files in repack directory
        print(color_text("\n→ Processing files for repack...", "cyan"))
        processed_files = process_repack_files(TEMP_REPACK_DIR)
        
        if not processed_files["success"]:
            raise ValueError(f"File processing failed: {processed_files['error']}")
            
        print(color_text(f"✓ Processed {processed_files['count']} files", "green"))
        
        # Create the final PAK
        print(color_text("\n→ Creating final PAK file...", "cyan"))
        command = [
            REPAK_PATH,
            "pack",
            "--version",
            "V11",
            str(TEMP_REPACK_DIR),
            str(merged_pak_path)
        ]
        
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = result.stderr.strip()
            error_context = {
                "operation": "PAK Creation",
                "command": " ".join(command),
                "error": error_msg,
                "impact": "Failed to create merged PAK",
                "solution": "Check repak tool and file permissions"
            }
            log_error_context(error_context)
            raise RuntimeError(f"Repak command failed: {error_msg}")
        
        # Verify the merged PAK was created
        if merged_pak_path.exists():
            size_mb = merged_pak_path.stat().st_size / (1024 * 1024)
            print(color_text(f"\n✓ Successfully created merged PAK: {shorten_path(merged_pak_path)}", "green"))
            print(color_text(f"✓ PAK size: {size_mb:.2f} MB", "green"))
            
            # Validate the merged PAK
            if VALIDATE_MERGED_PAK:
                print(color_text("\n→ Validating merged PAK...", "cyan"))
                is_valid, message = validate_merged_pak(merged_pak_path)
                
                if not is_valid:
                    print(color_text(f"\n❌ Validation Failed: {message}", "red"))
                    if not yes_or_no("Would you like to keep the merged pak anyway?"):
                        merged_pak_path.unlink()
                        raise ValueError(f"PAK validation failed: {message}")
                    print(color_text("→ Keeping merged PAK despite validation failure.", "yellow"))
                else:
                    print(color_text("\n✓ Merged PAK validation successful!", "green"))
                    
            # Verify permissions
            try:
                merged_pak_path.chmod(merged_pak_path.stat().st_mode | 0o666)  # Ensure file is readable
            except Exception as e:
                print(color_text(f"⚠️ Warning: Could not set permissions on merged PAK: {e}", "yellow"))
                
        else:
            raise FileNotFoundError("Failed to create merged PAK file")
            
    except Exception as e:
        error_context = {
            "operation": "PAK Repacking",
            "error": str(e),
            "impact": "Merged PAK creation failed",
            "solution": "Check error details and try again"
        }
        log_error_context(error_context)
        raise RuntimeError(f"Repack operation failed: {str(e)}")

    return True







def perform_prerepack_checks(repack_dir, output_path):
    """Version 1.0 - Validates environment before repacking"""
    try:
        results = {
            "success": False,
            "error": None,
            "disk_space_gb": 0,
            "file_count": 0,
            "total_size_mb": 0
        }
        
        # Check if repack directory exists and is not empty
        if not repack_dir.exists():
            results["error"] = "Repack directory does not exist"
            return results
            
        if is_folder_empty(repack_dir):
            results["error"] = "No files found to repack"
            return results
        
        # Calculate total size and count files
        total_size = 0
        file_count = 0
        for root, _, files in os.walk(repack_dir):
            for file in files:
                file_path = Path(root) / file
                total_size += file_path.stat().st_size
                file_count += 1
        
        # Check disk space (need at least double the size for safety)
        free_space = shutil.disk_usage(output_path.parent).free
        required_space = total_size * 2.5  # Safety margin
        
        if free_space < required_space:
            results["error"] = f"Insufficient disk space. Need {required_space/1024/1024/1024:.2f}GB, have {free_space/1024/1024/1024:.2f}GB"
            return results
        
        # Update results
        results["success"] = True
        results["disk_space_gb"] = free_space / (1024**3)
        results["file_count"] = file_count
        results["total_size_mb"] = total_size / (1024**2)
        
        return results
        
    except Exception as e:
        results["error"] = f"Pre-repack check failed: {str(e)}"
        return results

def process_repack_files(repack_dir):
    """Version 1.0 - Processes and validates files before repacking"""
    results = {
        "success": False,
        "error": None,
        "count": 0
    }
    
    try:
        processed = 0
        for root, _, files in os.walk(repack_dir):
            for file in files:
                file_path = Path(root) / file
                if file.startswith('final_merged_'):
                    new_name = file.replace('final_merged_', '', 1)
                    new_path = file_path.parent / new_name
                    file_path.rename(new_path)
                processed += 1
                
        results["success"] = True
        results["count"] = processed
        return results
        
    except Exception as e:
        results["error"] = f"File processing failed: {str(e)}"
        return results





def log_validation_status(step_name, passed, error=None):
    """Version 1.0 - Unified validation status logging"""
    if passed:
        print(color_text(f"✓ {step_name} passed", "green"))
    else:
        if error:
            print(color_text(f"❌ {step_name} failed: {error}", "red"))
        else:
            print(color_text(f"❌ {step_name} failed", "red"))
    return passed








def cleanup_temp_files():
    """Version 2.4.1 - Ensures complete cleanup of all cached data and temporary files
    
    """
    print(color_text("\nCleaning all temporary files and cache...", "white"))
    
    # Clear any existing cache references first
    try:
        global pak_cache
        if 'pak_cache' in globals() and pak_cache is not None:
            pak_cache.extracted_paks.clear()
            pak_cache.file_hashes.clear()
    except Exception as e:
        print(color_text(f"⚠️ Warning: Failed to clear cache references: {e}", "yellow"))
    
    # Define ALL possible cache directories
    cleanup_dirs = [
        (TEMP_UNPACK_DIR, "PAK extraction"),
        (TEMP_REPACK_DIR, "repacking workspace"),
        (TEMP_HASH_DIR, "hash calculations"),
        (TEMP_MERGE_DIR, "merge workspace"),
        (TEMP_VALIDATION_DIR, "validation files"),
        # Add any other temp directories that might exist
    ]
    
    print(color_text("→ Performing thorough cleanup of all cache directories...", "cyan"))
    
    for dir_path, dir_purpose in cleanup_dirs:
        if dir_path.exists():
            try:
                # Force removal of read-only attributes
                for root, dirs, files in os.walk(dir_path):
                    for item in dirs + files:
                        item_path = Path(root) / item
                        try:
                            # Force remove read-only attribute if it exists
                            if item_path.exists():
                                item_path.chmod(item_path.stat().st_mode | 0o666)
                        except Exception:
                            pass  # Continue even if permission change fails

                # Aggressively remove directory
                shutil.rmtree(dir_path, ignore_errors=True)
                print(color_text(f"✓ Cleaned {dir_purpose} directory: {shorten_path(dir_path)}", "green"))
                
            except Exception as e:
                print(color_text(f"❌ Error cleaning {dir_purpose} directory: {shorten_path(dir_path)}", "red"))
                print(color_text(f"   Error: {str(e)}", "yellow"))
                print(color_text("   WARNING: Manual cleanup may be required!", "red"))
                
            # Double-check directory is gone, recreate if needed
            try:
                if dir_path.exists():
                    print(color_text(f"⚠️ Forcing removal of {shorten_path(dir_path)}", "yellow"))
                    os.system(f'rd /s /q "{dir_path}"')  # Windows force remove
            except Exception:
                pass

            # Create fresh empty directory
            try:
                dir_path.mkdir(parents=True, exist_ok=True)
                print(color_text(f"✓ Created fresh {dir_purpose} directory", "green"))
            except Exception as e:
                print(color_text(f"❌ Failed to create fresh directory: {str(e)}", "red"))
                sys.exit(1)  # Exit if we can't create clean directories

    print(color_text("\n✓ Workspace cleaned and ready", "green"))






import atexit
atexit.register(cleanup_temp_files)

# Register cleanup handler for keyboard interrupts
import signal

def signal_handler(signum, frame):
    """Version 1.0 - Handles cleanup on keyboard interrupt"""
    print(color_text("\n\nInterrupt received, cleaning up...", "yellow"))
    cleanup_temp_files()
    sys.exit(1)

signal.signal(signal.SIGINT, signal_handler)







def validate_merged_pak(merged_pak_path):
    """Version 2.1 - Enhanced PAK validation with comprehensive checks"""
    if not VALIDATE_MERGED_PAK:
        return True, "Validation skipped per configuration"

    print(color_text("\nInitiating merged PAK validation...", "cyan"))
    validation_results = {
        "pak_exists": False,
        "size_check": False,
        "structure_check": False,
        "extraction_check": False,
        "content_check": False,
        "errors": []
    }
    
    try:
        # Step 1: Basic existence and size validation
        validation_results["pak_exists"] = basic_pak_validation(merged_pak_path, validation_results)
        if not validation_results["pak_exists"]:
            return False, "PAK file does not exist or is empty"
            
        # Step 2: Validate PAK structure
        print(color_text("→ Validating PAK structure...", "cyan"))
        validation_results["structure_check"] = validate_pak_structure(merged_pak_path, validation_results)
        if not validation_results["structure_check"]:
            return False, "PAK structure validation failed"
            
        # Step 3: Extraction test
        print(color_text("→ Testing PAK extraction...", "cyan"))
        validation_results["extraction_check"] = validate_pak_extraction(merged_pak_path, validation_results)
        if not validation_results["extraction_check"]:
            return False, "PAK extraction validation failed"
            
        # Step 4: Content validation
        print(color_text("→ Validating PAK contents...", "cyan"))
        validation_results["content_check"] = validate_pak_contents(merged_pak_path, validation_results)
        if not validation_results["content_check"]:
            return False, "PAK content validation failed"
        
        # Generate validation report with properly formatted data
        validation_report = []  # List for successful validations
        validation_errors = []  # List for any errors found
        
        # Add validation results to appropriate lists
        for check, result in validation_results.items():
            if check != "errors":
                if result:
                    validation_report.append(f"Passed: {check}")
                else:
                    validation_errors.append(f"Failed: {check}")
        
        # Add any collected errors
        validation_errors.extend(validation_results.get("errors", []))
        
        # Generate report
        generate_validation_report(validation_report, validation_errors)
        
        # Final validation status
        if validation_results["errors"]:
            error_summary = "\n".join(validation_results["errors"][:3])
            return False, f"Validation failed with errors:\n{error_summary}"
            
        return True, "All validation checks passed successfully"
        
    except Exception as e:
        error_msg = f"Validation failed with error: {str(e)}"
        print(color_text(f"\n❌ {error_msg}", "red"))
        return False, error_msg







# Helper functions for validate_merged_pak

def basic_pak_validation(pak_path, results):
    """Version 1.0 - Performs basic PAK file validation"""
    try:
        print(color_text("→ Checking PAK file basics...", "cyan"))
        
        if not pak_path.exists():
            results["errors"].append("PAK file does not exist")
            return False
            
        file_size = pak_path.stat().st_size
        if file_size == 0:
            results["errors"].append("PAK file is empty")
            return False
            
        min_size = 100  # Minimum reasonable size in bytes
        if file_size < min_size:
            results["errors"].append(f"PAK file suspiciously small: {file_size} bytes")
            return False
            
        print(color_text(f"✓ Basic validation passed - Size: {file_size/1024/1024:.2f} MB", "green"))
        results["size_check"] = True
        return True
        
    except Exception as e:
        results["errors"].append(f"Basic validation error: {str(e)}")
        return False

def validate_pak_structure(pak_path, results):
    """Version 1.0 - Validates PAK file structure"""
    try:
        # Use repak to list contents and verify structure
        command = [REPAK_PATH, "list", str(pak_path)]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            results["errors"].append(f"Structure validation failed: {result.stderr.strip()}")
            return False
            
        # Analyze file listing
        file_listing = result.stdout.strip().splitlines()
        if not file_listing:
            results["errors"].append("PAK contains no files")
            return False
            
        print(color_text(f"✓ Structure validation passed - Found {len(file_listing)} files", "green"))
        return True
        
    except Exception as e:
        results["errors"].append(f"Structure validation error: {str(e)}")
        return False

def validate_pak_extraction(pak_path, results):
    """Version 1.0 - Validates PAK extraction"""
    temp_extract_path = None
    try:
        # Create temporary extraction directory
        temp_extract_path = create_unique_temp_dir(TEMP_VALIDATION_DIR, "extraction_test")
        
        # Try to extract PAK
        command = [REPAK_PATH, "unpack", str(pak_path), "--output", str(temp_extract_path)]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            results["errors"].append(f"Extraction test failed: {result.stderr.strip()}")
            return False
            
        # Verify extraction results
        extracted_files = list(temp_extract_path.rglob('*'))
        if not any(f.is_file() for f in extracted_files):
            results["errors"].append("No files found after extraction")
            return False
            
        print(color_text("✓ Extraction validation passed", "green"))
        return True
        
    except Exception as e:
        results["errors"].append(f"Extraction validation error: {str(e)}")
        return False
    finally:
        # Cleanup
        if temp_extract_path and temp_extract_path.exists():
            shutil.rmtree(temp_extract_path, ignore_errors=True)








def validate_pak_contents(pak_path, results):
    """Version 2.1 - Enhanced basic error checking and logging"""
    try:
        print(color_text("\n→ Starting content validation...", "cyan"))
        
        # Basic existence check
        if not pak_path.exists():
            print(color_text(f"❌ PAK file not found at: {pak_path}", "red"))
            results["errors"].append("PAK file not found")
            return False
            
        # Get file listing with basic error handling
        print(color_text("→ Getting file listing...", "cyan"))
        command = [REPAK_PATH, "list", str(pak_path)]
        result = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            error_msg = f"Content listing failed: {result.stderr.strip()}"
            print(color_text(f"❌ {error_msg}", "red"))
            results["errors"].append(error_msg)
            return False
            
        # Basic content analysis
        file_listing = result.stdout.strip().splitlines()
        if not file_listing:
            print(color_text("❌ No files found in PAK", "red"))
            results["errors"].append("PAK contains no files")
            return False
            
        # Analyze content structure
        print(color_text("→ Analyzing content structure...", "cyan"))
        content_stats = analyze_pak_contents(file_listing)
        
        # Print detailed statistics
        log_for_report("\nContent Statistics - ", "info")
        log_for_report(f"→ Total files: {content_stats['total_files']}", "info")
        
        # todo fixme later bug with MB showing 0.0 MB specifically here only
        # log_for_report(f"→ Total size: {content_stats['total_size_mb']:.2f} MB", "info")

        if content_stats['empty_files'] > 0:
            print(color_text(f"⚠️ Found {content_stats['empty_files']} empty files", "yellow"))
            results["errors"].append(f"Found {content_stats['empty_files']} empty files")
            
        if content_stats['suspicious_files'] > 0:
            print(color_text(f"⚠️ Found {content_stats['suspicious_files']} suspicious files", "yellow"))
            
        if content_stats["has_errors"]:
            print(color_text("❌ Content validation failed - see above warnings", "red"))
            return False
            
        print(color_text("✓ Content validation passed", "green"))
        return True
        
    except Exception as e:
        error_msg = f"Content validation error: {str(e)}"
        print(color_text(f"❌ {error_msg}", "red"))
        results["errors"].append(error_msg)
        return False







def analyze_pak_contents(file_listing):
    """Version 2.4 - Basic content analysis with proper size reporting and logging
    Using existing PAK size and consistent log_for_report
    """
    stats = {
        "total_files": 0,
        "empty_files": 0,
        "suspicious_files": 0,
        "total_size": 0,
        "min_size": float('inf'),
        "max_size": 0,
        "has_errors": False
    }
    
    try:
        log_for_report("→ Analyzing PAK contents...", "info")
        
        for entry in file_listing:
            if not entry.strip():
                continue
                
            stats["total_files"] += 1
            
            # Basic path validation
            try:
                if '/' in entry:  # Has path separator
                    parts = entry.split('/')
                    if not all(part.strip() for part in parts):
                        log_for_report(f"⚠️ Invalid path structure: {entry}", "warning")
                        stats["has_errors"] = True
                        continue
                        
                if len(entry) > 260:  # Windows max path
                    log_for_report(f"⚠️ Path too long: {entry}", "warning")
                    stats["has_errors"] = True
                    
            except Exception as e:
                log_for_report(f"⚠️ Error processing entry {entry}: {str(e)}", "warning")
                stats["has_errors"] = True
                continue
        
        # If we have files, use the PAK file size for total size
        if stats["total_files"] > 0:
            try:
                # Get size from parent validation process
                pak_size = Path(pak_path).stat().st_size if 'pak_path' in globals() else 0
                stats["total_size"] = pak_size
                stats["total_size_mb"] = pak_size / (1024 * 1024)
            except Exception:
                # Fallback if size calculation fails
                stats["total_size_mb"] = 0
                log_for_report("⚠️ Warning: Could not determine PAK size", "warning")
                
        if stats["total_files"] > 0:
            stats["min_size"] = min(stats["min_size"], float('inf'))
            
        return stats
        
    except Exception as e:
        log_for_report(f"❌ Content analysis error: {e}", "error")
        stats["has_errors"] = True
        return stats









def generate_detailed_validation_report(validation_results, pak_path):
    """Version 2.0 - Generates detailed validation report with proper path handling"""
    report_path = Path(__file__).parent / "validation_report.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(f"PAK Validation Report - {timestamp}\n")
            f.write("="* 50 + "\n\n")
            
            # Basic Information
            f.write("PAK Information:\n")
            f.write(f"File: {str(pak_path)}\n")
            f.write(f"Size: {pak_path.stat().st_size / (1024*1024):.2f} MB\n\n")
            
            # Validation Results
            f.write("Validation Results:\n")
            f.write("-"* 20 + "\n")
            for check, result in validation_results.items():
                if check != "errors":
                    f.write(f"{check}: {'✓' if result else '❌'}\n")
            
            # Error List
            if validation_results.get("errors"):
                f.write("\nErrors Found:\n")
                f.write("-"* 20 + "\n")
                for i, error in enumerate(validation_results["errors"], 1):
                    f.write(f"{i}. {str(error)}\n")
            else:
                f.write("\nNo errors found during validation.\n")
                
        print(color_text(f"\nDetailed validation report saved to: {str(report_path)}", "cyan"))
        
    except Exception as e:
        print(color_text(f"Failed to save validation report: {str(e)}", "red"))








def compare_extracted_files(original_dir, validation_dir):
    """Version 1.0 - Compares original and validated files"""
    validation_report = []
    validation_errors = []

    def get_file_info(path):
        """Helper function to get file info"""
        size = path.stat().st_size
        md5_hash = hashlib.md5()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b""):
                md5_hash.update(chunk)
        return size, md5_hash.hexdigest()

    # Get all files from both directories
    original_files = {p.relative_to(original_dir): p for p in original_dir.rglob('*') if p.is_file()}
    validation_files = {p.relative_to(validation_dir): p for p in validation_dir.rglob('*') if p.is_file()}

    # Check for missing or extra files
    missing_files = set(original_files.keys()) - set(validation_files.keys())
    extra_files = set(validation_files.keys()) - set(original_files.keys())

    if missing_files:
        validation_errors.append(f"Missing files in merged pak: {', '.join(str(f) for f in missing_files)}")

    if extra_files:
        validation_errors.append(f"Extra files in merged pak: {', '.join(str(f) for f in extra_files)}")

    # Compare common files
    for rel_path in set(original_files.keys()) & set(validation_files.keys()):
        orig_file = original_files[rel_path]
        val_file = validation_files[rel_path]
        
        try:
            orig_size, orig_hash = get_file_info(orig_file)
            val_size, val_hash = get_file_info(val_file)

            if orig_size != val_size:
                validation_errors.append(f"Size mismatch for {rel_path}: Original={orig_size}, Merged={val_size}")
            elif orig_hash != val_hash:
                validation_errors.append(f"Content mismatch for {rel_path}")
            else:
                validation_report.append(f"Validated: {rel_path}")
        except Exception as e:
            validation_errors.append(f"Error comparing {rel_path}: {str(e)}")

    # Generate and save report
    generate_validation_report(validation_report, validation_errors)

    if validation_errors:
        return False, "Validation failed. See validation_report.txt for details."
    return True, "Validation successful"





def generate_validation_report(validation_report, validation_errors):
    """Version 2.1 - Uses global message buffer for comprehensive reporting"""
    report_path = Path(__file__).parent / "validation_report.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(report_path, "w", encoding='utf-8') as f:
            # Header
            f.write(f"Validation Report - {timestamp}\n")
            f.write("="* 50 + "\n\n")
            
            # Write buffered messages
            current_section = None
            for msg_type, message in VALIDATION_MESSAGES:
                # Start new section if message ends with "Summary:" or similar
                if message.strip().endswith(":"):
                    f.write(f"\n{message}\n")
                    current_section = message
                else:
                    f.write(f"{message}\n")
            
            # Include any additional validation errors not caught in buffer
            if validation_errors:
                f.write("\nADDITIONAL ERRORS:\n")
                f.write("-"* 20 + "\n")
                for error in validation_errors:
                    f.write(f"ERROR: {str(error)}\n")
                f.write("\n")
            
            # Final status
            if not validation_errors:
                f.write("\n✓ All validation checks completed successfully\n")
            else:
                f.write(f"\n❌ Validation completed with {len(validation_errors)} errors\n")

        # Clear the message buffer after writing report
        VALIDATION_MESSAGES.clear()
        
        print(color_text(f"Validation report saved to {shorten_path(report_path)}", "cyan"))
        
    except Exception as e:
        print(color_text(f"Failed to save validation report: {str(e)}", "red"))







def choose_step(steps, prompt="Choose the next step by number"):
    """Version 1.0"""
    print(color_text(f"\n{prompt}:", "magenta"))
    for i, step in enumerate(steps, start=1):
        print(color_text(f"{i} - {step}", "white"))

    while True:
        try:
            choice = int(input(color_text("Enter your choice: ", "cyan")))
            if 1 <= choice <= len(steps):
                return steps[choice-1]
            else:
                print(color_text(f"Invalid choice. Please enter a number between 1 and {len(steps)}.\n", "red"))
        except ValueError:
            print(color_text("Invalid input. Please enter a valid number.\n", "red"))

def choose_file_to_compare(conflicting_files, prompt="Choose a file to compare by number"):
    """Version 1.0"""
    print(color_text(f"\n{prompt}:", "magenta"))

    for i, (file, sources) in enumerate(conflicting_files.items(), start=1):
        print(color_text(f"{i} - {file}", "yellow"))
        print(color_text(f"    Affected by {len(sources)} mods:", "red"))
        for source in sources:
            print(color_text(f"    - {source[0]}.pak", "white"))

    while True:
        try:
            choice = int(input(color_text("Enter your choice: ", "cyan")))
            if 1 <= choice <= len(conflicting_files):
                selected_file = list(conflicting_files.keys())[choice-1]
                return {selected_file: conflicting_files[selected_file]}
            else:
                print(color_text(f"Invalid choice. Please enter a number between 1 and {len(conflicting_files)}.\n", "red"))
        except ValueError:
            print(color_text("Invalid input. Please enter a valid number.\n", "red"))

def choose_source_to_unpack(file, sources):
    """Version 1.0"""
    print(color_text(f"\nConflicting file: {file}", "magenta"))
    print(color_text("Available .pak source files affecting this file:", "magenta"))
    for i, source in enumerate(sources, start=1):
        print(color_text(f"{i} - {source[0]}.pak", "white"))

    while True:
        try:
            choice = int(input(color_text("Select a .pak file by number: ", "cyan")))
            if 1 <= choice <= len(sources):
                return sources[choice-1]
            else:
                print(color_text(f"Invalid choice. Please enter a number between 1 and {len(sources)}.\n", "red"))
        except ValueError:
            print(color_text("Invalid input. Please enter a valid number.\n", "red"))

def create_merged_folder_structure(file):
    """Version 1.0"""
    destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    print(color_text(f"Folder structure created for {file} in: {TEMP_REPACK_DIR}", "white"))
    return destination_path




def yes_or_no(prompt):
    """Version 1.1"""
    while True:
        choice = input(color_text(f"\n{prompt} (y/n): ", "cyan")).strip().lower()
        if choice in ['y', 'yes']:
            return True
        elif choice in ['n', 'no']:
            return False
        else:
            print(color_text("Invalid input. Please enter 'y' or 'n'.", "red"))




def log_corrupt_pak(pak_file, error_message):
    """Version 1.0 - Logs corrupt PAK files"""
    log_file = Path(__file__).parent / "corrupt_paks.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a", encoding='utf-8') as f:
            f.write(f"[{timestamp}] {pak_file}: {error_message}\n")
        print(color_text(f"Logged corrupt PAK: {pak_file}", "yellow"))
    except Exception as e:
        print(color_text(f"Failed to log corrupt PAK: {e}", "red"))





def validate_pak_file(pak_file):
    """Version 3.1 - Enhanced basic validation with clear logging
    
    Args:
        pak_file (str/Path): Path to PAK file to validate
    
    Returns:
        tuple: (is_valid, error_message)
    """
    validation_results = {
        "file_check": False,
        "header_check": False,
        "structure_check": False,
        "content_check": False,
        "errors": []
    }
    
    try:
        print(color_text("\nStarting PAK validation...", "cyan"))
        pak_path = Path(pak_file)
        
        # Step 1: Basic file validation
        print(color_text("→ Performing basic file validation...", "cyan"))
        basic_result = validate_pak_basics(pak_path, validation_results)
        if not basic_result["success"]:
            print(color_text(f"❌ Basic validation failed: {basic_result['error']}", "red"))
            return False, basic_result["error"]
        print(color_text("✓ Basic validation passed", "green"))
            
        # Step 2: Header validation
        print(color_text("→ Validating PAK header...", "cyan"))
        header_result = validate_pak_header(pak_path, validation_results)
        if not header_result["success"]:
            print(color_text(f"❌ Header validation failed: {header_result['error']}", "red"))
            return False, header_result["error"]
        print(color_text("✓ Header validation passed", "green"))
            
        # Step 3: Structure validation
        print(color_text("→ Validating PAK structure...", "cyan"))
        structure_result = validate_pak_structure_integrity(pak_path, validation_results)
        if not structure_result["success"]:
            print(color_text(f"❌ Structure validation failed: {structure_result['error']}", "red"))
            return False, structure_result["error"]
        print(color_text("✓ Structure validation passed", "green"))
            
        # Step 4: Content validation
        print(color_text("→ Validating PAK contents...", "cyan"))
        content_result = validate_pak_content_integrity(pak_path, validation_results)
        if not content_result["success"]:
            print(color_text(f"❌ Content validation failed: {content_result['error']}", "red"))
            return False, content_result["error"]
        print(color_text("✓ Content validation passed", "green"))
            
        # Log successful validation
        print(color_text("\n✓ All validation checks passed successfully", "green"))
        return True, "PAK file is valid"
        
    except Exception as e:
        error_msg = f"Validation failed with unexpected error: {str(e)}"
        print(color_text(f"\n❌ {error_msg}", "red"))
        validation_results["errors"].append(error_msg)
        return False, error_msg






# Helper functions for validate_pak_file






def analyze_extracted_content(extract_dir, file_listing):
    """Version 2.0 - Analyzes extracted PAK content with basic validation"""
    stats = {
        "total_files": 0,
        "empty_files": 0,
        "total_size": 0,
        "error": None
    }
    
    try:
        print(color_text("→ Analyzing extracted content...", "cyan"))
        extract_path = Path(extract_dir)
        
        if not extract_path.exists():
            stats["error"] = "Extraction directory not found"
            return stats
            
        processed_files = 0
        for file_entry in file_listing:
            file_entry = file_entry.strip()
            if not file_entry:
                continue
                
            file_path = extract_path / file_entry.replace('/', os.sep)
            if file_path.exists() and file_path.is_file():
                try:
                    size = file_path.stat().st_size
                    stats["total_files"] += 1
                    stats["total_size"] += size
                    
                    if size == 0:
                        stats["empty_files"] += 1
                        print(color_text(f"⚠️ Empty file found: {file_entry}", "yellow"))
                        
                    processed_files += 1
                    
                except Exception as e:
                    print(color_text(f"⚠️ Error processing {file_entry}: {str(e)}", "yellow"))
                    
            else:
                print(color_text(f"⚠️ File not found in extraction: {file_entry}", "yellow"))
                
        print(color_text(f"→ Processed {processed_files} files", "cyan"))
        return stats
        
    except Exception as e:
        stats["error"] = f"Content analysis failed: {str(e)}"
        return stats







def validate_pak_content_integrity_new(pak_path, results):
    """Version 1.0 - Validates PAK content integrity using extracted files"""
    result = {
        "success": False,
        "error": None
    }
    
    try:
        # Use standard repak list command
        content_result = subprocess.run(
            [REPAK_PATH, "list", str(pak_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if content_result.returncode != 0:
            result["error"] = f"Content validation failed: {content_result.stderr.strip()}"
            results["errors"].append(result["error"])
            return result
            
        # Extract and analyze files
        extract_dir = pak_cache.extract_pak(pak_path)
        if not extract_dir:
            result["error"] = "Failed to extract PAK for validation"
            results["errors"].append(result["error"])
            return result
            
        # Analyze extracted files
        file_listing = content_result.stdout.splitlines()
        content_stats = analyze_extracted_content(extract_dir, file_listing)
        
        if content_stats["error"]:
            result["error"] = content_stats["error"]
            results["errors"].append(result["error"])
            return result
            
        if content_stats["empty_files"] > 0:
            results["errors"].append(f"Warning: Found {content_stats['empty_files']} empty files")
            
        if content_stats["total_files"] == 0:
            result["error"] = "No valid files found in PAK"
            results["errors"].append(result["error"])
            return result
            
        results["content_check"] = True
        result["success"] = True
        return result
        
    except Exception as e:
        result["error"] = f"Content integrity check failed: {str(e)}"
        results["errors"].append(result["error"])
        return result




def validate_pak_basics(pak_path, results):
    """Version 2.0 - Enhanced basic PAK validation checks"""
    result = {
        "success": False,
        "error": None
    }
    
    try:
        # Check file existence
        if not pak_path.exists():
            result["error"] = f"PAK file not found: {pak_path}"
            return result
            
        # Check if it's actually a file
        if not pak_path.is_file():
            result["error"] = f"Path exists but is not a file: {pak_path}"
            return result
            
        # Check file size
        file_size = pak_path.stat().st_size
        if file_size == 0:
            result["error"] = "PAK file is empty"
            return result
            
        # Check minimum size (arbitrary minimum, adjust if needed)
        if file_size < 100:  # 100 bytes as minimum
            result["error"] = f"PAK file suspiciously small: {file_size} bytes"
            return result
            
        # Check file extension
        if pak_path.suffix.lower() != '.pak':
            result["error"] = "File does not have .pak extension"
            return result
            
        # Check file permissions
        if not os.access(pak_path, os.R_OK):
            result["error"] = "PAK file is not readable"
            return result
            
        # All basic checks passed
        results["file_check"] = True
        result["success"] = True
        return result
        
    except Exception as e:
        result["error"] = f"Basic validation error: {str(e)}"
        results["errors"].append(result["error"])
        return result





def validate_pak_header(pak_path, results):
    """Version 2.0 - Enhanced PAK header validation"""
    result = {
        "success": False,
        "error": None
    }
    
    try:
        # Try to read header bytes
        with open(pak_path, 'rb') as f:
            header_bytes = f.read(16)  # Read first 16 bytes
            
        if len(header_bytes) < 16:
            result["error"] = f"Invalid header size: got {len(header_bytes)} bytes, expected 16"
            return result
            
        # Use repak to verify version/format
        verify_result = subprocess.run(
            [REPAK_PATH, "info", str(pak_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if verify_result.returncode != 0:
            result["error"] = f"Invalid PAK format: {verify_result.stderr.strip()}"
            return result
            
        # Header validation passed
        results["header_check"] = True
        result["success"] = True
        return result
        
    except Exception as e:
        result["error"] = f"Header validation error: {str(e)}"
        results["errors"].append(result["error"])
        return result







def validate_pak_structure_integrity(pak_path, results):
    """Version 2.2 - Enhanced PAK structure validation with comprehensive logging
    Args:
        pak_path (Path): Path to PAK file
        results (dict): Results dictionary to update
        
    Returns:
        dict: Result status and details
    """
    result = {
        "success": False,
        "error": None,
        "file_count": 0
    }
    
    try:
        log_for_report("\n→ Checking PAK structure...", "info")
        
        # Get file listing with basic error handling
        structure_result = subprocess.run(
            [REPAK_PATH, "list", str(pak_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if structure_result.returncode != 0:
            result["error"] = f"Structure check failed: {structure_result.stderr.strip()}"
            log_for_report(f"❌ {result['error']}", "error")
            
            # Log detailed error context
            log_for_report("\nError Details:", "error")
            log_for_report("→ Operation: PAK Structure Validation", "warning")
            log_for_report(f"→ File: {shorten_path(pak_path)}", "warning")
            log_for_report(f"→ Error: {result['error']}", "warning")
            log_for_report("→ Impact: PAK will be skipped", "warning")
            return result
            
        # Analyze file listing
        file_listing = structure_result.stdout.strip().splitlines()
        
        if not file_listing:
            result["error"] = "PAK contains no files"
            log_for_report("❌ Empty PAK file", "error")
            log_for_report(f"❌ Structure validation failed: {result['error']}", "error")
            
            # Log empty PAK error details
            log_for_report("\nError Details:", "error")
            log_for_report("→ Operation: PAK Validation", "warning")
            log_for_report(f"→ File: {shorten_path(pak_path)}", "warning")
            log_for_report("→ Error: PAK contains no files", "warning")
            log_for_report("→ Impact: PAK will be skipped", "warning")
            return result
            
        # Basic structure validation
        invalid_entries = []
        valid_count = 0
        
        for entry in file_listing:
            if not entry.strip():
                continue
                
            # Basic path validation
            if not is_valid_pak_entry(entry):
                invalid_entries.append(entry)
                continue
                
            valid_count += 1
            
        # Update results and log findings
        result["file_count"] = valid_count
        log_for_report(f"→ Found {valid_count} valid files", "info")
        
        if invalid_entries:
            log_for_report(f"⚠️ Found {len(invalid_entries)} invalid entries", "warning")
            if len(invalid_entries) <= 3:  # Show first few invalid entries
                for entry in invalid_entries:
                    log_for_report(f"  → Invalid: {entry}", "warning")
            else:
                log_for_report(f"  → First 3 invalid entries:", "warning")
                for entry in invalid_entries[:3]:
                    log_for_report(f"  → Invalid: {entry}", "warning")
                log_for_report(f"  → And {len(invalid_entries) - 3} more...", "warning")
        
        if valid_count == 0:
            result["error"] = "No valid files found in PAK"
            log_for_report("❌ No valid files found", "error")
            
            # Log no valid files error details
            log_for_report("\nError Details:", "error")
            log_for_report("→ Operation: PAK Validation", "warning")
            log_for_report(f"→ File: {shorten_path(pak_path)}", "warning")
            log_for_report("→ Error: No valid files found", "warning")
            log_for_report("→ Impact: PAK will be skipped", "warning")
            return result
            
        # Structure validation passed
        results["structure_check"] = True
        result["success"] = True
        log_for_report("✓ Structure validation passed", "success")
        return result
        
    except Exception as e:
        result["error"] = f"Structure validation error: {str(e)}"
        log_for_report(f"❌ {result['error']}", "error")
        
        # Log exception error details
        log_for_report("\nError Details:", "error")
        log_for_report("→ Operation: PAK Structure Validation", "warning")
        log_for_report(f"→ File: {shorten_path(pak_path)}", "warning")
        log_for_report(f"→ Error: {str(e)}", "warning")
        log_for_report("→ Impact: PAK will be skipped", "warning")
        
        results["errors"].append(result["error"])
        return result









def validate_pak_content_integrity(pak_path, results):
    """Version 2.2 - Enhanced content validation with fixed size reporting and logging"""
    result = {
        "success": False,
        "error": None
    }
    
    try:
        log_for_report("\n→ Validating content integrity...", "info")
        
        # Try to get content listing
        content_result = subprocess.run(
            [REPAK_PATH, "list", str(pak_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if content_result.returncode != 0:
            result["error"] = f"Content listing failed: {content_result.stderr.strip()}"
            log_for_report(f"❌ {result['error']}", "error")
            return result
            
        # Extract PAK for validation
        log_for_report("→ Extracting PAK for validation...", "info")
        extract_dir = pak_cache.extract_pak(pak_path)
        if not extract_dir:
            result["error"] = "Failed to extract PAK for validation"
            log_for_report(f"❌ {result['error']}", "error")
            return result
            
        # Get PAK size for accurate reporting
        pak_size = pak_path.stat().st_size
        size_mb = pak_size / (1024 * 1024)
            
        # Analyze content listing
        file_listing = content_result.stdout.splitlines()
        content_stats = analyze_extracted_content(extract_dir, file_listing)
        
        if content_stats["error"]:
            result["error"] = content_stats["error"]
            log_for_report(f"❌ {result['error']}", "error")
            return result
            
        # Print content statistics using actual PAK size
        log_for_report("\nContent Statistics::", "info")
        log_for_report(f"→ Total files: {content_stats['total_files']}", "info")
        log_for_report(f"→ Total size: {size_mb:.2f} MB", "info")  # Use actual PAK size
        
        if content_stats["empty_files"] > 0:
            log_for_report(f"⚠️ Found {content_stats['empty_files']} empty files", "warning")
            
        if content_stats["total_files"] == 0:
            result["error"] = "No valid files found in extracted content"
            log_for_report(f"❌ {result['error']}", "error")
            return result
            
        # Content validation passed
        results["content_check"] = True
        result["success"] = True
        log_for_report("✓ Content validation passed", "success")
        return result
        
    except Exception as e:
        result["error"] = f"Content integrity error: {str(e)}"
        log_for_report(f"❌ {result['error']}", "error")
        results["errors"].append(result["error"])
        return result







def analyze_pak_content_listing(file_lines, extract_dir):
    """Version 2.0 - Analyzes PAK content listing using extracted files"""
    stats = {
        "total_files": 0,
        "empty_files": 0,
        "suspicious_sizes": 0,
        "total_size": 0,
        "min_size": float('inf'),
        "max_size": 0
    }
    
    try:
        for line in file_lines:
            if not line.strip():
                continue
                
            file_path = Path(extract_dir) / line.strip()
            if file_path.exists():
                size = file_path.stat().st_size
                stats["total_files"] += 1
                stats["total_size"] += size
                
                # Track size statistics
                stats["min_size"] = min(stats["min_size"], size)
                stats["max_size"] = max(stats["max_size"], size)
                
                # Check for anomalies
                if size == 0:
                    stats["empty_files"] += 1
                elif size < 100:  # Suspiciously small files
                    stats["suspicious_sizes"] += 1
                    
        if stats["total_files"] > 0:
            stats["min_size"] = min(stats["min_size"], float('inf'))
            
        return stats
        
    except Exception:
        return stats






def is_valid_pak_entry(entry):
    """Version 2.0 - Enhanced PAK entry validation"""
    if not entry or not isinstance(entry, str):
        return False
        
    try:
        # Check for basic path validity
        if not entry.strip():
            return False
            
        # Check for invalid characters
        invalid_chars = '<>:"|?*'
        if any(char in entry for char in invalid_chars):
            return False
            
        # Check path components
        parts = entry.split('/')
        if not all(part.strip() for part in parts):
            return False
            
        # Check for reasonable path length (Windows MAX_PATH = 260)
        if len(entry) > 260:
            return False
            
        # Check for valid file name
        filename = parts[-1] if parts else ""
        if not filename or filename.startswith('.'):
            return False
            
        return True
        
    except Exception:
        return False





def log_pak_validation(pak_path, results, success=True, error=None):
    """Version 1.0 - Logs PAK validation results"""
    log_file = Path(__file__).parent / "pak_validation.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(log_file, "a", encoding='utf-8') as f:
            f.write(f"\n{'='*50}\n")
            f.write(f"Validation Time: {timestamp}\n")
            f.write(f"PAK File: {pak_path}\n")
            f.write(f"Status: {'Success' if success else 'Failed'}\n")
            
            if error:
                f.write(f"Error: {error}\n")
                
            f.write("\nValidation Results:\n")
            for check, result in results.items():
                if check != "errors":
                    f.write(f"- {check}: {'✓' if result else '❌'}\n")
                    
            if results["errors"]:
                f.write("\nErrors Found:\n")
                for i, err in enumerate(results["errors"], 1):
                    f.write(f"{i}. {err}\n")
                    
            f.write(f"{'='*50}\n")
            
    except Exception as e:
        print(color_text(f"Failed to write validation log: {e}", "red"))

def get_pak_file_stats(pak_path):
    """Version 1.0 - Gets detailed PAK file statistics"""
    stats = {
        "size": 0,
        "last_modified": None,
        "is_readable": False,
        "is_writable": False,
        "error": None
    }
    
    try:
        if pak_path.exists():
            stats["size"] = pak_path.stat().st_size
            stats["last_modified"] = datetime.fromtimestamp(pak_path.stat().st_mtime)
            stats["is_readable"] = os.access(pak_path, os.R_OK)
            stats["is_writable"] = os.access(pak_path, os.W_OK)
    except Exception as e:
        stats["error"] = str(e)
        
    return stats









def rename_conflicting_paks(conflicting_files):
    """Version 1.5 - Improved backup naming with merged PAK protection"""
    print(color_text("\nBacking up original PAK files...", "cyan"))
    
    renamed_files = set()
    total_paks = 0
    renamed_count = 0
    skipped_count = 0
    error_count = 0
    
    # First count total unique PAKs to process
    for sources in conflicting_files.values():
        for _, pak_file in sources:
            pak_path = Path(pak_file)
            # Skip merged PAK from counting
            if pak_path.exists() and not is_merged_pak(pak_path) and pak_path not in renamed_files:
                total_paks += 1

    if total_paks == 0:
        print(color_text("→ No PAK files found to backup", "yellow"))
        return

    print(color_text(f"→ Found {total_paks} PAK files to backup", "cyan"))

    # Process the renames
    for sources in conflicting_files.values():
        for mod_name, pak_file in sources:
            pak_path = Path(pak_file)
            
            # Skip if already processed or if it's the merged PAK
            if pak_path in renamed_files or is_merged_pak(pak_path):
                continue

            try:
                if not pak_path.exists():
                    print(color_text(f"⚠️ PAK not found, skipping: {shorten_path(pak_path)}", "yellow"))
                    skipped_count += 1
                    continue
                    
                # Find available backup name with a safety limit
                backup_number = ""
                max_attempts = 100  # Prevent infinite loop
                attempt = 0
                
                while attempt < max_attempts:
                    backup_path = pak_path.with_suffix(f'.pakbackup{backup_number}')
                    if not backup_path.exists():
                        break
                    # Increment backup number
                    if backup_number == "":
                        backup_number = "2"
                    else:
                        backup_number = str(int(backup_number) + 1)
                    attempt += 1

                if attempt >= max_attempts:
                    error_msg = f"Failed to find available backup name after {max_attempts} attempts"
                    print(color_text(f"❌ {error_msg}", "red"))
                    error_count += 1
                    continue

                # Verify source file is still accessible
                if not os.access(pak_path, os.W_OK):
                    error_msg = "Source PAK file is not writable"
                    print(color_text(f"❌ {error_msg}", "red"))
                    error_count += 1
                    continue

                # Perform the rename with verification
                pak_path.rename(backup_path)
                
                # Verify the rename was successful
                if backup_path.exists() and not pak_path.exists():
                    renamed_count += 1
                    renamed_files.add(pak_path)
                    suffix = f" (backup #{backup_number})" if backup_number else ""
                    print(color_text(f"✓ Backed up: {shorten_path(pak_path)} → {shorten_path(backup_path)}{suffix}", "green"))
                else:
                    error_msg = "Rename operation failed verification"
                    print(color_text(f"❌ {error_msg}", "red"))
                    error_count += 1
                
            except PermissionError as pe:
                error_count += 1
                print(color_text(f"❌ Permission denied backing up {shorten_path(pak_path)}: {str(pe)}", "red"))
            except Exception as e:
                error_count += 1
                print(color_text(f"❌ Error backing up {shorten_path(pak_path)}: {str(e)}", "red"))

    # Print summary
    print(color_text("\nBackup Summary:", "magenta"))
    print(color_text(f"✓ Successfully backed up: {renamed_count} PAKs", "green"))
    if skipped_count > 0:
        print(color_text(f"⚠️ Skipped: {skipped_count} PAKs", "yellow"))
    if error_count > 0:
        print(color_text(f"❌ Errors encountered: {error_count} PAKs", "red"))
        
    # Warn if any backups were skipped
    if skipped_count + error_count > 0:
        print(color_text("\n⚠️ Warning: Some PAK files may still be accessible by the game!", "yellow"))







def is_folder_empty(folder_path):
    """Version 1.0"""
    for root, dirs, files in os.walk(folder_path):
        if files:
            return False
    return True

def display_compare_report(compared_files, compare_errors):
    """Version 1.0"""
    print(color_text("\nFinal Report:", "magenta"))
    if compared_files:
        print(color_text(f"\nCompared files:", "white"))
        print("\n".join(color_text(f"- {compared_file}", "yellow") for compared_file in compared_files))
    if compare_errors:
        print(color_text(f"\nErrors during comparison:", "red"))
        print("\n".join(color_text(f"- {error_file}", "red") for error_file in compare_errors))

def compare_prompts(conflicting_files, use_base, compare_app):
    """Version 1.0"""
    max_sources = 2 if use_base else 3
    print(color_text(f"\nNote: Files present in more than {max_sources} mods cannot be compared using {compare_app}.", "yellow"))

    eligible_files = {file: sources for file, sources in conflicting_files.items()
                      if len(sources) <= max_sources}

    if not eligible_files:
        print(color_text("\nNo files are eligible for comparison with the selected options.", "red"))
        return {}

    if len(eligible_files) == 1:
        print(color_text(f"\nOnly one file is eligible for comparison: {list(eligible_files.keys())[0]}", "yellow"))
        return eligible_files

    step = choose_step([
        "Select specific conflicting files to compare",
        "Compare all eligible conflicting files"
    ])

    if step == "Select specific conflicting files to compare":
        files_to_compare = choose_file_to_compare(eligible_files)
        return files_to_compare
    else:
        return eligible_files






def compare_files(conflicting_files):
    """Version 2.4 - Enhanced file comparison and merging with improved error handling, removed size command dependency
    
    Args:
        conflicting_files (dict): Dictionary of files with conflicts and their sources
    """
    total_conflicts = len(conflicting_files)
    processed_count = 0
    failed_merges = []
    successful_merges = []
    
    print(color_text(f"\nPreparing to merge {total_conflicts} conflicting files...", "cyan"))
    
    try:
        # Create and validate merge workspace
        merge_folder = prepare_merge_workspace(TEMP_MERGE_DIR)
        if not merge_folder:
            raise RuntimeError("Failed to prepare merge workspace")

        # Process each conflicting file
        for file, sources in conflicting_files.items():
            processed_count += 1
            print(color_text(f"\n[Processing {processed_count} of {total_conflicts}]", "magenta"))
            print(color_text(f"File: {file}", "white"))
            
            try:
                # Setup merge environment for this file
                merge_result = setup_file_merge(file, sources, merge_folder)
                if not merge_result["success"]:
                    raise ValueError(merge_result["error"])
                
                file_merge_path = merge_result["merge_path"]
                merged_file_name = f"final_merged_{Path(file).name}"
                merged_file_path = file_merge_path.parent / merged_file_name
                
                # Check if already merged
                if merged_file_path.exists():
                    print(color_text(f"✓ Final merged file already exists.", "green"))
                    if validate_merged_file(merged_file_path):
                        copy_to_repack(merged_file_path, file)
                        successful_merges.append(file)
                        continue
                    else:
                        print(color_text("⚠️ Existing merge file appears invalid. Remerging...", "yellow"))
                
                # Copy and validate source files
                files_copied = copy_source_files(sources, file, file_merge_path.parent)
                if not files_copied["success"]:
                    raise ValueError(f"Failed to copy source files: {files_copied['error']}")
                
                # Display merge instructions
                display_merge_instructions(file_merge_path.parent, merged_file_name)
                
                # Wait for user to complete merge
                print(color_text("\nStarting WinMerge...", "cyan"))
                launch_winmerge(file_merge_path.parent)
                
                # Wait for merge completion
                merge_complete = wait_for_merge_completion(merged_file_path)
                if not merge_complete["success"]:
                    raise ValueError(merge_complete["error"])
                
                # Validate merged result using new validation method
                if validate_merged_file(merged_file_path):
                    # Copy to repack directory
                    copy_to_repack(merged_file_path, file)
                    successful_merges.append(file)
                    print(color_text(f"✓ Successfully merged: {file}", "green"))
                else:
                    raise ValueError("Merged file validation failed")
                
            except Exception as e:
                error_context = {
                    "file": file,
                    "sources": [s[0] for s in sources],
                    "error": str(e)
                }
                failed_merges.append(error_context)
                print(color_text(f"\n❌ Merge failed for {file}: {str(e)}", "red"))
                
                if not yes_or_no("Would you like to continue with remaining files?"):
                    raise RuntimeError("Merge process cancelled by user")
        
        # Final summary
        print_merge_summary(successful_merges, failed_merges, total_conflicts)
        
    except Exception as e:
        error_context = {
            "operation": "File Comparison",
            "processed": f"{processed_count}/{total_conflicts}",
            "error": str(e),
            "impact": "Merge process interrupted",
            "solution": "Check error details and retry failed files"
        }
        log_error_context(error_context)
        raise RuntimeError(f"Compare files operation failed: {str(e)}")









# Helper functions for compare_files

def prepare_merge_workspace(merge_dir):
    """Version 1.0 - Prepares and validates merge workspace"""
    try:
        merge_dir.mkdir(parents=True, exist_ok=True)
        return merge_dir if merge_dir.exists() else None
    except Exception as e:
        print(color_text(f"Failed to prepare merge workspace: {e}", "red"))
        return None

def setup_file_merge(file, sources, merge_folder):
    """Version 1.0 - Sets up environment for merging a specific file"""
    result = {
        "success": False,
        "error": None,
        "merge_path": None
    }
    
    try:
        file_merge_path = merge_folder / file.replace('/', os.sep)
        file_merge_path.parent.mkdir(parents=True, exist_ok=True)
        
        result["success"] = True
        result["merge_path"] = file_merge_path
        return result
    except Exception as e:
        result["error"] = f"Failed to setup merge environment: {str(e)}"
        return result

def copy_source_files(sources, file, merge_dir):
    """Version 1.0 - Copies source files to merge directory"""
    result = {
        "success": False,
        "error": None,
        "copied_files": []
    }
    
    try:
        for source in sources:
            mod_name = source[0]
            pak_file = source[1]
            
            source_file_path = pak_cache.get_extracted_path(pak_file, file)
            if source_file_path and source_file_path.exists():
                dest_file_name = f"{mod_name}_{Path(file).name}"
                dest_file_path = merge_dir / dest_file_name
                shutil.copy2(source_file_path, dest_file_path)
                result["copied_files"].append(dest_file_path)
                print(color_text(f"✓ Copied {dest_file_name}", "green"))
            else:
                result["error"] = f"Source file not found in cache for {mod_name}"
                return result
        
        result["success"] = True
        return result
    except Exception as e:
        result["error"] = str(e)
        return result

def display_merge_instructions(merge_dir, output_filename):
    """Version 1.0 - Displays clear merge instructions"""
    print(color_text(f"# Script Version {SCRIPT_VERSION}\n", "cyan")) 
    print(color_text("\nMerge Instructions:", "cyan"))
    print(color_text("1. Open WinMerge", "white"))
    print(color_text("2. Use File -> Open to select files", "white"))
    print(color_text("3. Compare and merge the changes you want to keep", "white"))
    print(color_text(f"4. Save final result as '{output_filename}'", "white"))
    print(color_text(f"5. Save in this folder: {shorten_path(merge_dir)}", "white"))





def validate_existing_merge(merged_file_path):
    """Version 2.0 - Validates existing merged file with basic checks"""
    try:
        print(color_text(f"\n→ Checking existing merged file...", "cyan"))
        
        if not merged_file_path.exists():
            print(color_text("❌ Merged file not found", "red"))
            return False
            
        # Basic size check
        file_size = merged_file_path.stat().st_size
        if file_size == 0:
            print(color_text("❌ Existing merged file is empty", "red"))
            return False
            
        # Try reading the file
        try:
            with open(merged_file_path, 'rb') as f:
                # Read start and end to verify integrity
                f.seek(0)
                start = f.read(1024)
                f.seek(-min(1024, file_size), 2)
                end = f.read(1024)
                
                if not start or not end:
                    print(color_text("❌ File appears corrupted", "red"))
                    return False
                    
        except Exception as e:
            print(color_text(f"❌ Error reading file: {e}", "red"))
            return False
            
        print(color_text("✓ Existing merge appears valid", "green"))
        return True
        
    except Exception as e:
        print(color_text(f"❌ Validation failed: {e}", "red"))
        return False






def wait_for_merge_completion(merged_file_path):
    """Version 1.0 - Waits for and validates merge completion"""
    result = {
        "success": False,
        "error": None
    }
    
    
    max_wait_time = 3600  # 1 hour maximum wait
    check_interval = 6    # Check every x seconds
    elapsed_time = 0
    
    while elapsed_time < max_wait_time:
        if merged_file_path.exists():
            if validate_existing_merge(merged_file_path):
                result["success"] = True
                return result
            else:
                result["error"] = "Merged file exists but appears invalid"
                return result
                
        print(color_text("→ Waiting for merge completion...", "cyan"))
        time.sleep(check_interval)
        elapsed_time += check_interval
        
        if elapsed_time % 60 == 0:  # Every minute
            print(color_text(f"⚠️ Still waiting for merge... ({elapsed_time//60} minutes)", "yellow"))
    
    result["error"] = "Merge timeout exceeded"
    return result







def validate_merged_result(merged_file_path):
    """Version 2.1 - Complete merged result validation with detailed checks"""
    try:
        print(color_text(f"\n→ Validating merged result: {merged_file_path.name}", "cyan"))
        validation_steps = {
            "file_check": False,
            "size_check": False,
            "read_check": False,
            "content_check": False
        }
        
        # Step 1: Basic file check
        if not merged_file_path.exists():
            print(color_text("❌ Merged file does not exist", "red"))
            return False
        validation_steps["file_check"] = True
        
        # Step 2: Size validation
        try:
            file_size = merged_file_path.stat().st_size
            if file_size == 0:
                print(color_text("❌ Merged file is empty", "red"))
                return False
            if file_size < 100:  # Arbitrary minimum size
                print(color_text(f"⚠️ Warning: File suspiciously small ({file_size} bytes)", "yellow"))
            print(color_text(f"→ File size: {file_size/1024:.1f} KB", "cyan"))
            validation_steps["size_check"] = True
            
        except Exception as e:
            print(color_text(f"❌ Size check failed: {e}", "red"))
            return False
            
        # Step 3: Read validation
        try:
            with open(merged_file_path, 'rb') as f:
                # Check start of file
                start = f.read(1024)
                if not start:
                    print(color_text("❌ Cannot read file start", "red"))
                    return False
                    
                # Check end of file
                f.seek(-min(1024, file_size), 2)
                end = f.read()
                if not end:
                    print(color_text("❌ Cannot read file end", "red"))
                    return False
                    
            validation_steps["read_check"] = True
            
        except Exception as e:
            print(color_text(f"❌ Read check failed: {e}", "red"))
            return False
            
        # Step 4: Content type validation
        try:
            extension = merged_file_path.suffix.lower()
            
            # Text file validation
            if extension in ['.cfg', '.txt', '.json']:
                try:
                    with open(merged_file_path, 'r', encoding='utf-8') as f:
                        # Check first few lines
                        lines = [f.readline() for _ in range(5)]
                        if not any(lines):
                            print(color_text("⚠️ Warning: Empty text file", "yellow"))
                        elif not all(line.isprintable() for line in lines if line):
                            print(color_text("⚠️ Warning: Contains non-printable characters", "yellow"))
                except UnicodeDecodeError:
                    print(color_text("⚠️ Warning: Not a valid text file", "yellow"))
                except Exception as e:
                    print(color_text(f"⚠️ Warning: Text validation error: {e}", "yellow"))
                    
            validation_steps["content_check"] = True
            
        except Exception as e:
            print(color_text(f"⚠️ Content check warning: {e}", "yellow"))
            
        # Final validation summary
        print(color_text("\nValidation Summary:", "cyan"))
        for step, passed in validation_steps.items():
            status = "✓" if passed else "❌"
            color = "green" if passed else "red"
            print(color_text(f"{status} {step.replace('_', ' ').title()}", color))
            
        if all(validation_steps.values()):
            print(color_text("\n✓ Merged result validation passed", "green"))
            return True
        else:
            print(color_text("\n❌ Merged result validation failed", "red"))
            return False
            
    except Exception as e:
        print(color_text(f"\n❌ Validation failed with error: {e}", "red"))
        return False




def copy_to_repack(merged_file_path, original_file):
    """Version 1.0 - Copies merged file to repack directory"""
    try:
        destination_path = TEMP_REPACK_DIR / original_file.replace('/', os.sep)
        destination_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(merged_file_path, destination_path)
        return True
    except Exception as e:
        print(color_text(f"❌ Failed to copy to repack directory: {e}", "red"))
        return False

def launch_winmerge(merge_dir):
    """Version 1.0 - Launches WinMerge for file comparison"""
    try:
        files = sorted(list(merge_dir.glob('*')))
        if len(files) > 3:
            print(color_text("⚠️ More than 3 files detected. Please merge files manually.", "yellow"))
        # WinMerge will be launched by user as per instructions
        return True
    except Exception as e:
        print(color_text(f"❌ Failed to prepare WinMerge launch: {e}", "red"))
        return False

def print_merge_summary(successful_merges, failed_merges, total_conflicts):
    """Version 1.0 - Prints detailed merge operation summary"""
    print(color_text("\nMerge Operations Summary:", "magenta"))
    print(color_text(f"Total conflicts: {total_conflicts}", "white"))
    print(color_text(f"Successfully merged: {len(successful_merges)}", "green"))
    print(color_text(f"Failed merges: {len(failed_merges)}", "red" if failed_merges else "green"))
    
    if successful_merges:
        print(color_text("\nSuccessfully Merged Files:", "green"))
        for file in successful_merges:
            print(color_text(f"✓ {file}", "green"))
    
    if failed_merges:
        print(color_text("\nFailed Merges:", "red"))
        for fail in failed_merges:
            print(color_text(f"❌ {fail['file']}", "red"))
            print(color_text(f"   Error: {fail['error']}", "red"))
            print(color_text(f"   Affected mods: {', '.join(fail['sources'])}", "yellow"))












def offer_vanilla_comparison(conflicting_files):
    """Version 1.0"""
    if VANILLA_DIR.exists() and any(VANILLA_DIR.iterdir()):
        if all((VANILLA_DIR / file.replace('/', os.sep)).exists() for file in conflicting_files.keys()):
            if all(len(sources) > 2 for sources in conflicting_files.values()):
                print(color_text("\nAll conflicting files have more than 2 mods affecting them, skipping 'vanilla' base.", "yellow"))
                return False
            elif yes_or_no("Do you want to use 'vanilla' files as a base for comparisons?"):
                return True
        else:
            print(color_text("\n'Vanilla' folder does not contain all conflicting files, cannot use it as base.", "yellow"))
    else:
        print(color_text("\n'Vanilla' folder not found or is empty, cannot use it as base.", "yellow"))
    return False

def backup_file(file_path):
    """Version 1.0"""
    if file_path.exists():
        backup_folder = TEMP_BACKUP_DIR / file_path.parent.relative_to(TEMP_REPACK_DIR)
        backup_folder.mkdir(parents=True, exist_ok=True)
        backup_path = backup_folder / file_path.name
        shutil.copy2(file_path, backup_path)
        print(color_text(f"Backup created at {backup_path}", "cyan"))





def validate_merged_file(file_path):
    """Version 2.2 - Enhanced validation with smart file type handling"""
    try:
        print(color_text(f"\n→ Validating merged file: {Path(file_path).name}", "cyan"))
        
        # Basic existence check
        if not file_path.exists():
            print(color_text("❌ Merged file does not exist", "red"))
            return False
            
        # Size validation
        try:
            file_size = file_path.stat().st_size
            if file_size == 0:
                print(color_text("❌ Merged file is empty", "red"))
                return False
            print(color_text(f"→ File size: {file_size/1024:.1f} KB", "cyan"))
            
        except Exception as e:
            print(color_text(f"❌ Size check failed: {e}", "red"))
            return False
            
        # Content validation based on file type
        file_extension = file_path.suffix.lower()
        
        try:
            with open(file_path, 'rb') as f:
                # Check start of file
                start = f.read(1024)
                if not start:
                    print(color_text("❌ Cannot read file start", "red"))
                    return False
                    
                # For text-based files that aren't .cfg
                if file_extension not in ['.cfg'] and file_extension in ['.txt', '.json']:
                    try:
                        with open(file_path, 'r', encoding='utf-8') as text_file:
                            # Check first few lines
                            lines = [text_file.readline() for _ in range(5)]
                            if not any(lines):
                                print(color_text("⚠️ Warning: Empty text file", "yellow"))
                            elif not all(line.isprintable() for line in lines if line):
                                print(color_text("⚠️ Warning: Contains non-printable characters", "yellow"))
                    except UnicodeDecodeError:
                        print(color_text("⚠️ Warning: Not a valid text file", "yellow"))
                        
        except Exception as e:
            print(color_text(f"❌ Error reading file content: {e}", "red"))
            return False
            
        print(color_text("✓ File validation passed", "green"))
        return True
        
    except Exception as e:
        print(color_text(f"❌ Validation failed: {e}", "red"))
        return False



def validate_merged_pak_for_inclusion(pak_path):
    """Version 1.0 - Validates merged PAK before including in process"""
    try:
        print(color_text(f"\n→ Validating merged PAK: {shorten_path(pak_path)}", "cyan"))
        
        # Check if file exists and is readable
        if not pak_path.exists():
            return False, "PAK file not found"
        
        if not os.access(pak_path, os.R_OK):
            return False, "PAK file is not readable"
            
        # Check file size
        file_size = pak_path.stat().st_size
        if file_size == 0:
            return False, "PAK file is empty"
            
        # Try to read PAK structure
        result = subprocess.run(
            [REPAK_PATH, "list", str(pak_path)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False
        )
        
        if result.returncode != 0:
            return False, f"Invalid PAK structure: {result.stderr.strip()}"
            
        print(color_text("✓ Merged PAK validation passed", "green"))
        return True, None
        
    except Exception as e:
        return False, f"Validation error: {str(e)}"




def analyze_conflicts_only(pak_files):
    """Version 2.0 - Enhanced conflict analysis with validation"""
    
    # First verify critical dependencies
    if not os.path.isfile(REPAK_PATH):
        print(color_text(f"❌ Error: repak not found at {REPAK_PATH}", "red"))
        return False

    # Validate input PAKs before processing
    valid_paks = []
    invalid_paks = []
    
    print(color_text("\n=== Validating PAK Files ===", "cyan"))
    for pak_file in pak_files:
        try:
            pak_path = Path(pak_file)
            if not pak_path.exists():
                invalid_paks.append((pak_file, "File not found"))
                continue
            if not pak_path.is_file():
                invalid_paks.append((pak_file, "Not a file"))
                continue
            if pak_path.suffix.lower() != '.pak':
                invalid_paks.append((pak_file, "Not a .pak file"))
                continue
            if pak_path.stat().st_size == 0:
                invalid_paks.append((pak_file, "Empty file"))
                continue
                
            # Quick structure check
            result = subprocess.run(
                [REPAK_PATH, "list", str(pak_path)],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False
            )
            if result.returncode != 0:
                invalid_paks.append((pak_file, f"Invalid PAK structure: {result.stderr.strip()}"))
                continue
                
            valid_paks.append(pak_file)
            print(color_text(f"✓ Validated: {pak_path.name}", "green"))
            
        except Exception as e:
            invalid_paks.append((pak_file, f"Error: {str(e)}"))

    if invalid_paks:
        print(color_text("\n❌ Some PAKs failed validation:", "red"))
        for pak, reason in invalid_paks:
            print(color_text(f"  → {Path(pak).name}: {reason}", "red"))
        if not valid_paks:
            print(color_text("\nNo valid PAKs to analyze!", "red"))
            return False
        if not yes_or_no("\nContinue with valid PAKs only?"):
            return False

    try:
        print(color_text("\n=== Starting PAK Analysis ===", "cyan"))
        print(color_text(f"Processing {len(valid_paks)} valid PAK files...\n", "cyan"))

        # Initialize cache for analysis
        global pak_cache
        pak_cache = PakCache()

        # Process PAKs and build file tree with progress indicator
        print(color_text("→ Reading PAK contents...", "cyan"))
        pak_sources = process_pak_files(valid_paks, pak_cache)
        
        print(color_text("→ Building file tree...", "cyan"))
        file_tree, file_count, file_sources, file_hashes = build_file_tree(pak_sources)

        # Enhanced conflict analysis
        conflicting_files = {}
        conflict_details = defaultdict(list)
        non_conflicting = 0
        total_files = 0
        
        print(color_text("→ Analyzing conflicts...", "cyan"))
        for file, sources in file_sources.items():
            total_files += 1
            hashes = file_hashes[file]
            
            # Detailed hash analysis
            unique_hashes = set(hash_data[1] for hash_data in hashes.values() if hash_data[1] != 'Error')
            if len(unique_hashes) > 1:
                conflicting_files[file] = sources
                # Store detailed conflict info
                for mod_name, hash_data in hashes.items():
                    size, file_hash = hash_data
                    conflict_details[file].append({
                        'mod': mod_name,
                        'size': size,
                        'hash': file_hash
                    })
            else:
                non_conflicting += 1

        # Display Enhanced Results
        print(color_text("\n=== Analysis Results ===", "magenta"))
        print(color_text(f"Total PAKs analyzed: {len(valid_paks)}", "cyan"))
        print(color_text(f"Total files found: {total_files}", "cyan"))
        print(color_text(f"Compatible files: {non_conflicting}", "green"))
        print(color_text(f"Conflicting files: {len(conflicting_files)}", "yellow" if conflicting_files else "green"))

        if conflicting_files:
            print(color_text("\nDetailed Conflict Analysis:", "yellow"))
            
            # Enhanced conflict display with sizes and hashes
            for file, details in conflict_details.items():
                print(color_text(f"\nFile: {file}", "yellow"))
                print(color_text("Affected by:", "cyan"))
                for detail in details:
                    size_str = f"{detail['size']/1024:.1f}KB" if isinstance(detail['size'], (int, float)) else 'Unknown'
                    print(color_text(f"  → {detail['mod']}", "white"))
                    print(color_text(f"     Size: {size_str}", "white"))
                    print(color_text(f"     Hash: {detail['hash']}", "white"))
                print() # Spacing between files
        else:
            print(color_text("\n✓ No conflicts detected - all files are compatible!", "green"))

        return True

    except Exception as e:
        print(color_text(f"\n❌ Analysis error: {str(e)}", "red"))
        return False
    finally:
        print(color_text("\n→ Cleaning up temporary files...", "cyan"))
        cleanup_temp_files()




def main(pak_files):
    """Version 2.4 - Enhanced error handling and cleanup sequence"""
    print(color_text("\n# Python Merging for S2 HoC on nexusmods modified by nova", "cyan"))
    print(color_text("# credits to 63OR63 for original script", "cyan"))
    print(color_text("# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description", "cyan"))
    print(color_text(f"# Version {SCRIPT_VERSION}\n", "cyan")) 

    try:
        # IMPORTANT: Clean all temp folders and cache before doing anything
        print(color_text("\nEnsuring clean workspace...", "cyan"))
        cleanup_temp_files()  

        # Initialize cache and clean old temp files
        global pak_cache
        pak_cache = PakCache()

        # Handle any existing merged PAK before processing with new options
        merged_pak_result = handle_existing_merged_pak(MODS)
        if not merged_pak_result["success"]:
            if merged_pak_result.get("action") == "cancel":
                print(color_text("\nOperation cancelled by user.", "yellow"))
                input(color_text("\nPress Enter to close...", "cyan"))
                sys.exit(0)
            else:
                print(color_text(f"❌ Failed to handle existing merged PAK: {merged_pak_result.get('error', 'Unknown error')}", "red"))
                input(color_text("\nPress Enter to close...", "cyan"))
                sys.exit(1)

        # If user chose to include existing merged PAK, add it to pak_files
        if merged_pak_result.get("action") == "include":
            merged_pak_path = merged_pak_result["pak_path"]
            print(color_text(f"→ Adding existing merged PAK to processing list...", "cyan"))
            pak_files.append(str(merged_pak_path))

        print(color_text("\nProcessing PAK files...", "cyan"))
        pak_sources = process_pak_files(pak_files, pak_cache)
        file_tree, file_count, file_sources, file_hashes = build_file_tree(pak_sources)

        print(color_text("\nAnalyzing file structure:", "magenta"))
        display_file_tree(file_tree, file_count=file_count)

        # Determine conflicts using cached hashes
        conflicting_files = {}
        non_conflicting = 0
        for file, sources in file_sources.items():
            hashes = file_hashes[file]
            if len(set(hashes.values())) > 1:
                conflicting_files[file] = sources
            else:
                # Handle non-conflicting files using cache
                source = sources[0]
                mod_name = source[0]
                pak_file = source[1]
                source_file_path = pak_cache.get_extracted_path(pak_file, file)
                if source_file_path and source_file_path.exists():
                    destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
                    destination_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source_file_path, destination_path)
                    non_conflicting += 1

        if non_conflicting > 0:
            print(color_text(f"\n✓ Processed {non_conflicting} non-conflicting files", "green"))

        if not conflicting_files:
            print(color_text("\n✓ No conflicts found - all files are compatible!", "green"))
            print(color_text("\nRepacking files...", "white"))
            if not repack_pak():
                raise RuntimeError("Failed to create merged PAK")
                
            # Clean up before exiting successfully
            print(color_text("\nCleaning up temporary files...", "cyan"))
            cleanup_temp_files()
            
            input(color_text("\nPress Enter to close...", "cyan"))
            sys.exit(0)
        else:
            total_conflicts = len(conflicting_files)
            print(color_text(f"\nFound {total_conflicts} conflicting files that need merging:", "yellow"))
            display_conflicts(conflicting_files, file_hashes)

        if not winmerge_exists:
            print(color_text("\n❌ WinMerge is required for merging but was not found.", "red"))
            cleanup_temp_files()  # Clean up before error exit
            sys.exit(1)

        print(color_text("\nStarting merge process...", "cyan"))
        compare_files(conflicting_files)

        print(color_text(f"\nRepacking merged files...", "white"))
        if not repack_pak():
            cleanup_temp_files()  # Clean up before error
            raise RuntimeError("Failed to create merged PAK")

        print(color_text("\nBacking up original PAK files...", "cyan"))
        rename_conflicting_paks(conflicting_files)
        
        print(color_text("\nCleaning up temporary files...", "cyan"))
        cleanup_temp_files()

        print(color_text("\n✓ All operations completed successfully!", "green"))
        input(color_text("\nPress Enter to close...", "cyan"))
        sys.exit(0)
        
    except Exception as e:
        print(color_text(f"\n❌ An error occurred: {str(e)}", "red"))
        print(color_text("\nCleaning up after error...", "yellow"))
        try:
            cleanup_temp_files()
        except Exception as cleanup_error:
            print(color_text(f"Additional error during cleanup: {cleanup_error}", "red"))
        input(color_text("\nPress Enter to close...", "cyan"))
        sys.exit(1)









if __name__ == "__main__":
    missing_exe = False
    kdiff3_exists = os.path.isfile(KDIFF3_PATH)
    winmerge_exists = os.path.isfile(WINMERGE_PATH)

    if not os.path.isfile(REPAK_PATH):
        print(color_text(f"Error: repak does not exist at {REPAK_PATH}", "red"))
        print(color_text(f"\nPlease install it, correct the path at the top of the script, and try again.", "red"))
        missing_exe = True

    # if not kdiff3_exists:
        # print(color_text(f"Warning: kdiff3 does not exist at {KDIFF3_PATH}", "yellow"))

    if not winmerge_exists:
        print(color_text(f"Warning: WinMerge does not exist at {WINMERGE_PATH}", "yellow"))

    if not (kdiff3_exists or winmerge_exists):
        print(color_text(f"Error: Neither kdiff3 nor WinMerge exist at their respective paths.", "red"))
        print(color_text(f"\nPlease install at least one, correct the paths at the top of the script, and try again.", "red"))
        missing_exe = True

    if missing_exe:
        input(color_text("\nPress enter to close...", "cyan"))
        sys.exit(1)

    if len(sys.argv) < 2:
        print(color_text("\n# Python Merging for S2 HoC on nexusmods modified by nova", "cyan"))
        print(color_text("# credits to 63OR63 for original script", "cyan"))
        print(color_text("# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description", "cyan"))
        print(color_text(f"# Version {SCRIPT_VERSION}\n", "cyan")) 
        
        print(color_text("Usage:", "cyan"))
        print(color_text("  Regular merge: Drag and drop PAK files onto the BAT file", "white"))
        print(color_text("  Conflict check only: Add --analyze flag or use 2nd BAT file", "white"))
        print(color_text("\nExample:", "cyan"))
        print(color_text("  script.py --analyze file1.pak file2.pak", "white"))
        input(color_text("\nPress enter to close...", "cyan"))
        sys.exit(1)

    try:
        # Check for analysis mode
        if "--analyze" in sys.argv:
            pak_files = [f for f in sys.argv[1:] if f != "--analyze"]
            if not pak_files:
                print(color_text("❌ No PAK files specified!", "red"))
                sys.exit(1)
            analyze_conflicts_only(pak_files)
        else:
            pak_files = sys.argv[1:]
            main(pak_files)  # Original merge functionality
            
    except Exception as e:
        print(color_text(f"\n❌ Fatal error: {str(e)}", "red"))
    finally:
        input(color_text("\nPress Enter to close...", "cyan"))




    main(pak_files)



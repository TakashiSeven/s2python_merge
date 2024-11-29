import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import hashlib



# Python Merge on nexusmods modifed by nova

# credits to 63OR63 for original script
# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description



# Custom mods folder path - edit this if your Stalker 2 mods folder is in a different location
CUSTOM_MODS_PATH = r"E:\s2hoc\Stalker2\Content\Paks\~mods"



SCRIPT_VERSION = "2.1" 



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
    """Version 1.0"""
    try:
        result = subprocess.run(
            [REPAK_PATH, "list", "--size", pak_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            return 'Unknown'

        # Parse the output to find the file entry and extract its size
        for line in result.stdout.strip().splitlines():
            if file_entry in line:
                parts = line.strip().split()
                size = parts[-1]  # Assuming size is the last column
                return size
        return 'Unknown'
    except Exception as e:
        return 'Unknown'



def build_file_tree(pak_sources):
    """Version 2.2 - Improved organization and feedback"""
    file_tree = {}
    file_count = defaultdict(int)
    file_sources = defaultdict(list)
    file_hashes = defaultdict(dict)

    total_files = len(pak_sources)
    print(color_text(f"\nBuilding file tree from {total_files} entries...", "cyan"))

    # First pass - organize data
    processed = 0
    for pak_file, entry in pak_sources:
        processed += 1
        if processed % 100 == 0:  # Show progress every 100 files to avoid spam
            print(color_text(f"→ Processing entry {processed} of {total_files}", "cyan"))

        # Build tree structure
        parts = entry.split('/')
        current_level = file_tree
        for part in parts[:-1]:
            current_level = current_level.setdefault(part, {})
        file_name = parts[-1]
        current_level[file_name] = None

        # Track file occurrences
        file_count[entry] += 1
        mod_name = Path(pak_file).stem
        file_sources[entry].append([mod_name, pak_file])

        # Get size and hash from cache
        result = pak_cache.get_file_hash(pak_file, entry)
        if result is not None:
            file_size, file_hash = result
            file_hashes[entry][mod_name] = (file_size, file_hash)
        else:
            print(color_text(f"⚠️ Warning: Could not get hash for {entry} in {mod_name}", "yellow"))
            file_hashes[entry][mod_name] = ('Error', 'Error')

    # Summary statistics
    total_unique_files = len(file_sources)
    files_with_conflicts = sum(1 for count in file_count.values() if count > 1)
    
    print(color_text("\nFile Analysis Summary:", "magenta"))
    print(color_text(f"✓ Total entries processed: {total_files}", "green"))
    print(color_text(f"✓ Unique files found: {total_unique_files}", "green"))
    if files_with_conflicts > 0:
        print(color_text(f"⚠️ Files with multiple versions: {files_with_conflicts}", "yellow"))
    else:
        print(color_text("✓ No conflicting files found", "green"))

    # Validate tree structure
    if not file_tree:
        print(color_text("❌ Error: No valid file structure could be built", "red"))
        return {}, defaultdict(int), defaultdict(list), defaultdict(dict)

    return file_tree, file_count, file_sources, file_hashes






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
    """Version 2.6 - Improved feedback and organization"""
    pak_sources = []
    total_paks = len(pak_files)

    if not isinstance(pak_cache, PakCache):
        raise ValueError("Invalid pak_cache object provided")

    print(color_text(f"\nAnalyzing {total_paks} PAK files...", "cyan"))

    for index, pak_file in enumerate(pak_files, 1):
        if not os.path.isfile(pak_file):
            print(color_text(f"❌ File not found: {shorten_path(pak_file)}", "red"))
            continue

        print(color_text(f"\n[Processing PAK {index} of {total_paks}] {shorten_path(pak_file)}", "white"))
        
        # Initial PAK validation
        print(color_text("→ Validating PAK file...", "cyan"))
        is_valid, error_message = validate_pak_file(pak_file)
        if not is_valid:
            print(color_text(f"❌ Invalid PAK detected: {error_message}", "red"))
            log_corrupt_pak(pak_file, error_message)
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress Enter to close...", "cyan"))
                sys.exit(1)

        # Extract to cache
        print(color_text("→ Extracting PAK contents...", "cyan"))
        if not pak_cache.extract_pak(pak_file):
            print(color_text(f"❌ Failed to extract {shorten_path(pak_file)} to cache.", "red"))
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress Enter to close...", "cyan"))
                sys.exit(1)

        # Process file entries
        print(color_text("→ Reading file entries...", "cyan"))
        file_entries = execute_repak_list(pak_file)
        if file_entries is None:
            print(color_text(f"❌ Failed to process {shorten_path(pak_file)}.", "red"))
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress Enter to close...", "cyan"))
                sys.exit(1)
        else:
            num_entries = len(file_entries)
            print(color_text(f"✓ Found {num_entries} file entries", "green"))
            pak_sources.extend((pak_file, entry) for entry in file_entries)

    # Final summary
    total_processed = len(pak_sources)
    if total_processed == 0:
        print(color_text("\n❌ No valid PAK files were processed. Exiting.", "red"))
        input(color_text("\nPress Enter to close...", "cyan"))
        sys.exit(1)
    else:
        print(color_text(f"\n✓ Successfully processed {len(pak_files)} PAK files", "green"))
        print(color_text(f"✓ Total file entries found: {total_processed}", "green"))

    return pak_sources











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
    """Version 1.7 - Improved feedback and validation"""
    try:
        # Check if there are files to repack
        if is_folder_empty(TEMP_REPACK_DIR):
            raise Exception("No files found to repack.")

        print(color_text(f"\nPreparing to repack merged files...", "white"))

        merged_pak = "ZZZZZZZ_Merged.pak"
        merged_pak_path = Path(MODS) / merged_pak

        # Remove 'final_merged_' prefix from filenames
        print(color_text("→ Processing merged files...", "cyan"))
        files_processed = 0
        for root, _, files in os.walk(TEMP_REPACK_DIR):
            for file in files:
                file_path = Path(root) / file
                if file.startswith('final_merged_'):
                    original_name = file.replace('final_merged_', '', 1)
                    new_file_path = file_path.parent / original_name
                    file_path.rename(new_file_path)
                    files_processed += 1
                    if files_processed % 10 == 0:  # Show progress every 10 files
                        print(color_text(f"→ Processed {files_processed} files...", "cyan"))

        print(color_text(f"✓ Processed {files_processed} files for repacking", "green"))

        # Pack the files
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
            text=True
        )

        if result.returncode != 0:
            error_msg = result.stderr.strip()
            print(color_text(f"\n❌ Error during repacking: {error_msg}", "red"))
            sys.exit(1)

        # Validate the created PAK
        if merged_pak_path.exists():
            size_mb = merged_pak_path.stat().st_size / (1024 * 1024)
            print(color_text(f"\n✓ Successfully created merged PAK: {shorten_path(merged_pak_path)}", "green"))
            print(color_text(f"✓ PAK size: {size_mb:.2f} MB", "green"))

            # Validate merged pak if enabled
            if VALIDATE_MERGED_PAK:
                print(color_text("\n→ Validating merged PAK...", "cyan"))
                is_valid, message = validate_merged_pak(merged_pak_path)
                if not is_valid:
                    print(color_text(f"\n❌ Validation Failed: {message}", "red"))
                    if yes_or_no("Would you like to keep the merged pak anyway?"):
                        print(color_text("→ Keeping merged PAK despite validation failure.", "yellow"))
                    else:
                        merged_pak_path.unlink()
                        print(color_text("→ Merged PAK deleted due to validation failure.", "red"))
                        sys.exit(1)
                else:
                    print(color_text("\n✓ Merged PAK validation successful!", "green"))
        else:
            print(color_text(f"\n❌ Failed to create merged PAK file", "red"))
            sys.exit(1)

    except subprocess.CalledProcessError as e:
        print(color_text(f"\n❌ Error during repacking process: {e}", "red"))
        sys.exit(1)
    except Exception as e:
        print(color_text(f"\n❌ Unexpected error during repacking: {e}", "red"))
        sys.exit(1)












def cleanup_temp_files():
    """Version 2.4 - Ensures complete cleanup of all cached data"""
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







def validate_merged_pak(merged_pak_path):
    """Version 1.0 - Validates merged pak file integrity"""
    if not VALIDATE_MERGED_PAK:
        return True, "Validation skipped"

    print(color_text("\nValidating merged pak file...", "cyan"))
    
    try:
        # Clear validation directory if it exists
        if VALIDATION_DIR.exists():
            shutil.rmtree(VALIDATION_DIR)
        VALIDATION_DIR.mkdir(parents=True)

        # Extract merged pak for validation
        result = subprocess.run(
            [REPAK_PATH, "unpack", merged_pak_path, "--output", str(VALIDATION_DIR)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if result.returncode != 0:
            return False, f"Failed to extract merged pak: {result.stderr.strip()}"

        # Compare files with original merged files
        return compare_extracted_files(TEMP_REPACK_DIR, VALIDATION_DIR)

    except Exception as e:
        return False, f"Validation error: {str(e)}"
    finally:
        # Cleanup validation directory
        if VALIDATION_DIR.exists():
            shutil.rmtree(VALIDATION_DIR)




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
    """Version 1.1 - Generates validation report with shortened paths"""
    report_path = Path(__file__).parent / "validation_report.txt"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        with open(report_path, "w", encoding='utf-8') as f:
            f.write(f"Validation Report - {timestamp}\n")
            f.write("="* 50 + "\n\n")
            
            if validation_errors:
                f.write("ERRORS:\n")
                f.write("-"* 20 + "\n")
                for error in validation_errors:
                    # Keep full paths in the report file
                    f.write(f"ERROR: {error}\n")
                f.write("\n")

            f.write("SUCCESSFUL VALIDATIONS:\n")
            f.write("-"* 20 + "\n")
            for entry in validation_report:
                # Keep full paths in the report file
                f.write(f"{entry}\n")

        # Use shortened path for console output
        print(color_text(f"Validation report saved to {shorten_path(report_path)}", "cyan"))
    except Exception as e:
        print(color_text(f"Failed to save validation report: {e}", "red"))





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
    """Version 1.1 - Improved PAK validation without using unsupported test flag
    Returns: (is_valid, error_message)"""
    try:
        # Check if file exists and has size
        if not os.path.exists(pak_file):
            return False, "PAK file does not exist"
        if os.path.getsize(pak_file) == 0:
            return False, "PAK file is empty"

        # Try to list contents using repak list command
        result = subprocess.run(
            [REPAK_PATH, "list", pak_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        if result.returncode != 0:
            return False, f"Failed to list PAK contents: {result.stderr.strip()}"

        # Verify we got some file listings
        file_listings = result.stdout.strip()
        if not file_listings:
            return False, "PAK contains no files"

        # Basic structure check - verify we got actual file entries
        if not any(line.strip() for line in file_listings.splitlines()):
            return False, "PAK structure appears invalid - no valid file entries found"

        return True, "PAK file is valid"

    except Exception as e:
        return False, f"Error validating PAK: {str(e)}"







def rename_conflicting_paks(conflicting_files):
    """Version 1.2 - Improved feedback and organization"""
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
            if pak_path.exists() and pak_path not in renamed_files:
                total_paks += 1

    if total_paks == 0:
        print(color_text("→ No PAK files found to backup", "yellow"))
        return

    print(color_text(f"→ Found {total_paks} PAK files to backup", "cyan"))

    # Process the renames
    for sources in conflicting_files.values():
        for mod_name, pak_file in sources:
            pak_path = Path(pak_file)
            
            # Skip if already processed
            if pak_path in renamed_files:
                continue

            backup_path = pak_path.with_suffix('.pakbackup')
            
            try:
                if not pak_path.exists():
                    print(color_text(f"⚠️ PAK not found, skipping: {shorten_path(pak_path)}", "yellow"))
                    skipped_count += 1
                    continue
                    
                if backup_path.exists():
                    print(color_text(f"⚠️ Backup already exists: {shorten_path(backup_path)}", "yellow"))
                    skipped_count += 1
                    continue

                pak_path.rename(backup_path)
                renamed_count += 1
                renamed_files.add(pak_path)
                print(color_text(f"✓ Backed up: {shorten_path(pak_path)} → {shorten_path(backup_path)}", "green"))
                
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
    """Version 2.2 - Improved user guidance and feedback"""
    total_conflicts = len(conflicting_files)
    print(color_text(f"\nPreparing to merge {total_conflicts} conflicting files...", "cyan"))

    merge_folder = TEMP_MERGE_DIR
    merge_folder.mkdir(parents=True, exist_ok=True)

    processed_count = 0
    for file, sources in conflicting_files.items():
        processed_count += 1
        print(color_text(f"\n[Processing {processed_count} of {total_conflicts}] File: {file}", "magenta"))

        file_merge_path = merge_folder / file.replace('/', os.sep)
        file_merge_path.parent.mkdir(parents=True, exist_ok=True)

        merged_file_name = f"final_merged_{Path(file).name}"
        merged_file_path = file_merge_path.parent / merged_file_name

        if merged_file_path.exists():
            print(color_text(f"✓ Final merged file already exists for {file}. Skipping merge.", "green"))
            destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(merged_file_path, destination_path)
            print(color_text(f"✓ Copied existing merged file to {shorten_path(destination_path)}", "green"))
            continue

        # Copy files from cache with improved feedback
        files_copied = 0
        for source in sources:
            mod_name = source[0]
            pak_file = source[1]
            
            source_file_path = pak_cache.get_extracted_path(pak_file, file)
            if source_file_path and source_file_path.exists():
                dest_file_name = f"{mod_name}_{Path(file).name}"
                dest_file_path = file_merge_path.parent / dest_file_name
                shutil.copy2(source_file_path, dest_file_path)
                files_copied += 1
                print(color_text(f"✓ Copied {shorten_path(source_file_path)} to merge folder", "green"))
            else:
                print(color_text(f"⚠️ File {file} not found in cache for {mod_name}.", "red"))

        if files_copied == 0:
            print(color_text(f"❌ Failed to copy any files for {file}. Skipping.", "red"))
            continue

        print(color_text("\nMerge Instructions:", "cyan"))
        print(color_text("Files are ready in merge folder:", "yellow"))
        print(color_text(f"{merge_folder}", "yellow"))
        print(color_text("\nStep-by-step merge process:", "cyan"))
        print(color_text("1. Open WinMerge", "white"))
        print(color_text("2. Use File -> Open to select files", "white"))
        print(color_text("3. Compare and merge the changes you want to keep", "white"))
        print(color_text(f"4. Save final result as '{merged_file_name}'", "white"))
        print(color_text("5. Ensure you save in the correct subfolder", "white"))

        print(color_text("\nStarting WinMerge...", "cyan"))
        input(color_text("Press Enter when you have completed the merge...", "cyan"))

        if merged_file_path.exists():
            destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(merged_file_path, destination_path)
            print(color_text(f"✓ Successfully merged and saved: {shorten_path(destination_path)}", "green"))
        else:
            print(color_text(f"❌ No merged file named '{merged_file_name}' found.", "red"))
            print(color_text("Please ensure you saved the merged file with the correct name.", "red"))
            input(color_text("Press Enter to retry this file or Ctrl+C to exit...", "cyan"))
            return compare_files({file: conflicting_files[file]})

    print(color_text(f"\n✓ Successfully processed all {total_conflicts} conflicting files.", "green"))














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
    """Version 1.1"""
    if not file_path.exists() or file_path.stat().st_size == 0:
        raise Exception(f"Merged file {file_path} is invalid or empty.")
    # Additional validation checks can be added here
    print(color_text(f"Validated merged file: {file_path}", "cyan"))





def main(pak_files):
    """Version 2.1 - Improved user feedback and organization"""
    print(color_text("\n# Python Merging for S2 HoC on nexusmods modified by nova", "cyan"))
    print(color_text("# credits to 63OR63 for original script", "cyan"))
    print(color_text("# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description", "cyan"))
    print(color_text(f"# Version {SCRIPT_VERSION}\n", "cyan")) 

    # IMPORTANT: Clean all temp folders and cache before doing anything
    print(color_text("\nEnsuring clean workspace...", "cyan"))
    cleanup_temp_files()  

    # Initialize cache and clean old temp files
    global pak_cache
    pak_cache = PakCache()

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
        repack_pak()
        input(color_text("\nPress Enter to close...", "cyan"))
        sys.exit(0)
    else:
        total_conflicts = len(conflicting_files)
        print(color_text(f"\nFound {total_conflicts} conflicting files that need merging:", "yellow"))
        display_conflicts(conflicting_files, file_hashes)

    if not winmerge_exists:
        print(color_text("\n❌ WinMerge is required for merging but was not found.", "red"))
        sys.exit(1)

    print(color_text("\nStarting merge process...", "cyan"))
    compare_files(conflicting_files)

    print(color_text(f"\nRepacking merged files...", "white"))
    repack_pak()

    print(color_text("\nBacking up original PAK files...", "cyan"))
    rename_conflicting_paks(conflicting_files)
    
    print(color_text("\nCleaning up temporary files...", "cyan"))
    cleanup_temp_files()

    print(color_text("\n✓ All operations completed successfully!", "green"))
    input(color_text("\nPress Enter to close...", "cyan"))
    sys.exit(0)






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
        print(color_text("Usage: drag and drop .pak files onto this script.", "yellow"))
        input(color_text("\nPress enter to close...", "cyan"))
        sys.exit(1)

    pak_files = sys.argv[1:]




    main(pak_files)


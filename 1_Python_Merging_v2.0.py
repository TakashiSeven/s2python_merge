import os
import subprocess
import sys
import shutil
import time
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import hashlib


# Python Merge v2 on nexusmods modifed by nova

# credits to 63OR63 for original script
# https://www.nexusmods.com/stalker2heartofchornobyl/mods/413?tab=description


# Put correct paths to the executables here:
REPAK_PATH = r"C:\Program Files\repak_cli\bin\repak.exe"
# REPAK_PATH = r"C:\Program Files\repak_cli\repak.exe"

WINMERGE_PATH = fr"{os.path.join(os.environ['LOCALAPPDATA'], 'Programs', 'WinMerge', 'WinMergeU.exe')}"
# or sometimes also : c:\Program Files\WinMerge\WinMergeU.exe

# Ensure this is correct and points to your stalker 2 ~mods folder
MODS = r"E:\s2hoc\Stalker2\Content\Paks\~mods"


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
    """Version 2.1 - Uses file size comparison before hashing"""
    
    global pak_cache  # Make it explicit we're using global pak_cache
    file_tree = {}
    file_count = defaultdict(int)
    file_sources = defaultdict(list)
    file_hashes = defaultdict(dict)

    for pak_file, entry in pak_sources:
        parts = entry.split('/')
        current_level = file_tree

        for part in parts[:-1]:
            current_level = current_level.setdefault(part, {})
        file_name = parts[-1]

        current_level[file_name] = None
        file_count[entry] += 1
        mod_name = Path(pak_file).stem
        file_sources[entry].append([mod_name, pak_file])

        # Get size and hash from cache
        result = pak_cache.get_file_hash(pak_file, entry)
        if result is not None:
            file_size, file_hash = result
            file_hashes[entry][mod_name] = (file_size, file_hash)
        else:
            file_hashes[entry][mod_name] = ('Error', 'Error')

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
    """Version 2.4 - Updated to handle new validation method
    - Removed references to test flag validation
    - Improved error messaging
    - Added more informative validation status messages"""
    pak_sources = []

    if not isinstance(pak_cache, PakCache):
        raise ValueError("Invalid pak_cache object provided")

    for pak_file in pak_files:
        if not os.path.isfile(pak_file):
            print(color_text(f"File not found: {pak_file}", "red"))
            continue

        print(color_text(f"Processing {pak_file}...", "white"))
        
        # Initial PAK validation
        is_valid, error_message = validate_pak_file(pak_file)
        if not is_valid:
            print(color_text(f"Invalid PAK detected: {error_message}", "red"))
            log_corrupt_pak(pak_file, error_message)
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress enter to close...", "cyan"))
                sys.exit(1)

        # Extract to cache if validation passed
        if not pak_cache.extract_pak(pak_file):
            print(color_text(f"Failed to extract {pak_file} to cache.", "red"))
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress enter to close...", "cyan"))
                sys.exit(1)

        file_entries = execute_repak_list(pak_file)
        if file_entries is None:
            print(color_text(f"Failed to process {pak_file}.", "red"))
            if yes_or_no("Would you like to skip it and continue?"):
                continue
            else:
                print(color_text("Terminating the process.", "red"))
                input(color_text("\nPress enter to close...", "cyan"))
                sys.exit(1)
        else:
            num_entries = len(file_entries)
            print(color_text(f"Found {num_entries} file entries in {pak_file}", "white"))
            pak_sources.extend((pak_file, entry) for entry in file_entries)

    if not pak_sources:
        print(color_text("No valid .pak files were processed. Exiting.", "red"))
        input(color_text("\nPress enter to close...", "cyan"))
        sys.exit(1)

    return pak_sources










def display_conflicts(conflicting_files, file_hashes):
    """Version 1.3 - Added file size comparison"""
    print(color_text("\nConflicting Files Analysis:", "magenta"))
    for file, sources in conflicting_files.items():
        hashes = file_hashes[file]
        unique_sizes = set(hash_data[0] for hash_data in hashes.values() if hash_data[0] != 'Error')
        unique_hashes = set(hash_data[1] for hash_data in hashes.values() if hash_data[1] != 'Error')
        
        if len(unique_sizes) > 1:
            print(color_text(f"\n- {file}", "yellow"))
            print(color_text(f"    Affected by {len(sources)} mods with different file sizes:", "red"))
            for mod_name, pak_file in sources:
                size, hash_value = hashes.get(mod_name, ('Unknown', 'Unknown'))
                print(color_text(f"    - {mod_name}.pak (Size: {size} bytes, Hash: {hash_value})", "white"))
        elif len(unique_hashes) > 1:
            print(color_text(f"\n- {file}", "yellow"))
            print(color_text(f"    Affected by {len(sources)} mods with same size but different contents:", "red"))
            for mod_name, pak_file in sources:
                size, hash_value = hashes.get(mod_name, ('Unknown', 'Unknown'))
                print(color_text(f"    - {mod_name}.pak (Hash: {hash_value})", "white"))
        else:
            print(color_text(f"\n- {file}", "green"))
            print(color_text(f"    Affected by {len(sources)} mods but files are identical.", "green"))
            for mod_name, pak_file in sources:
                print(color_text(f"    - {mod_name}.pak", "white"))






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
    """Version 1.6 - Added merged pak validation"""
    try:
        if is_folder_empty(TEMP_REPACK_DIR):
            raise Exception("No merged files found to repack.")

        print(color_text(f"\nRepacking merged files...", "white"))

        merged_pak = "ZZZZZZZ_Merged.pak"
        merged_pak_path = Path(MODS) / merged_pak

        # Remove 'final_merged_' prefix from filenames
        for root, _, files in os.walk(TEMP_REPACK_DIR):
            for file in files:
                file_path = Path(root) / file
                if file.startswith('final_merged_'):
                    original_name = file.replace('final_merged_', '', 1)
                    new_file_path = file_path.parent / original_name
                    file_path.rename(new_file_path)
                    print(color_text(f"Renamed {file_path.name} to {new_file_path.name}", "cyan"))

        # Pack the files
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
            print(color_text(f"\nError repacking: {error_msg}", "red"))
            sys.exit(1)

        print(color_text(f"\nSuccessfully merged to {merged_pak_path}", "green"))

        # Validate merged pak if enabled
        if VALIDATE_MERGED_PAK:
            is_valid, message = validate_merged_pak(merged_pak_path)
            if not is_valid:
                print(color_text(f"\nValidation Failed: {message}", "red"))
                if yes_or_no("Would you like to keep the merged pak anyway?"):
                    print(color_text("Keeping merged pak despite validation failure.", "yellow"))
                else:
                    merged_pak_path.unlink()
                    print(color_text("Merged pak deleted due to validation failure.", "red"))
                    sys.exit(1)
            else:
                print(color_text("\nMerged pak validation successful!", "green"))

    except subprocess.CalledProcessError as e:
        print(color_text(f"\nSubprocess error during repacking: {e}", "red"))
        sys.exit(1)
    except Exception as e:
        print(color_text(f"\nException during repacking: {e}", "red"))
        sys.exit(1)











def cleanup_temp_files():
    """Version 2.1 - Enhanced error handling and reporting"""
    print(color_text("\nCleaning up temporary files...", "white"))
    
    # Clear the cache references first
    try:
        pak_cache.extracted_paks.clear()
        pak_cache.file_hashes.clear()
    except Exception as e:
        print(color_text(f"Warning: Failed to clear cache references: {e}", "yellow"))
    
    # Define cleanup directories
    cleanup_dirs = [
        (TEMP_UNPACK_DIR, "unpacking"),
        (TEMP_REPACK_DIR, "repacking"),
        (TEMP_HASH_DIR, "hash"),
        (TEMP_MERGE_DIR, "merge"),
        (TEMP_VALIDATION_DIR, "validation")
    ]
    
    for dir_path, dir_type in cleanup_dirs:
        if dir_path.exists():
            try:
                # First try to remove read-only attributes if any
                for root, dirs, files in os.walk(dir_path):
                    for item in dirs + files:
                        item_path = Path(root) / item
                        try:
                            item_path.chmod(item_path.stat().st_mode | 0o666)
                        except Exception as e:
                            print(color_text(f"Warning: Could not modify permissions for {item_path}: {e}", "yellow"))

                # Now try to remove the directory
                shutil.rmtree(dir_path)
                print(color_text(f"Cleaned up {dir_type} directory: {dir_path}", "green"))
                
            except PermissionError as pe:
                print(color_text(f"Permission error cleaning up {dir_type} directory {dir_path}: {pe}", "red"))
                print(color_text("Some files may need to be removed manually.", "yellow"))
            except OSError as oe:
                print(color_text(f"OS error cleaning up {dir_type} directory {dir_path}: {oe}", "red"))
                print(color_text("Directory may be in use or locked.", "yellow"))
            except Exception as e:
                print(color_text(f"Unexpected error cleaning up {dir_type} directory {dir_path}: {e}", "red"))




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
    """Version 1.0 - Generates validation report"""
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
                    f.write(f"ERROR: {error}\n")
                f.write("\n")

            f.write("SUCCESSFUL VALIDATIONS:\n")
            f.write("-"* 20 + "\n")
            for entry in validation_report:
                f.write(f"{entry}\n")

        print(color_text(f"Validation report saved to {report_path}", "cyan"))
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
    """Version 1.1 - Renames conflicting .pak files to .pakbackup."""
    print(color_text("\nRenaming conflicting .pak files to .pakbackup...", "white"))
    renamed_files = set()
    for sources in conflicting_files.values():
        for mod_name, pak_file in sources:
            pak_path = Path(pak_file)
            if pak_path.exists() and pak_path not in renamed_files:
                backup_path = pak_path.with_suffix('.pakbackup')
                try:
                    pak_path.rename(backup_path)
                    print(color_text(f"Renamed {pak_path.name} to {backup_path.name}", "green"))
                    renamed_files.add(pak_path)
                except Exception as e:
                    print(color_text(f"Error renaming {pak_path.name}: {e}", "red"))




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
    """Version 2.0 - Uses PakCache for improved performance"""
    print(color_text("\nPreparing to merge conflicting files...", "cyan"))

    merge_folder = TEMP_MERGE_DIR
    merge_folder.mkdir(parents=True, exist_ok=True)

    for file, sources in conflicting_files.items():
        print(color_text(f"\nProcessing file: {file}", "magenta"))

        file_merge_path = merge_folder / file.replace('/', os.sep)
        file_merge_path.parent.mkdir(parents=True, exist_ok=True)

        merged_file_name = f"final_merged_{Path(file).name}"
        merged_file_path = file_merge_path.parent / merged_file_name

        if merged_file_path.exists():
            print(color_text(f"Final merged file already exists for {file}. Skipping merge.", "green"))
            destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(merged_file_path, destination_path)
            print(color_text(f"Copied existing merged file to {destination_path}", "green"))
            continue

        # Copy files from cache instead of unpacking again
        for source in sources:
            mod_name = source[0]
            pak_file = source[1]
            
            # Get file from cache
            source_file_path = pak_cache.get_extracted_path(pak_file, file)
            if source_file_path and source_file_path.exists():
                dest_file_name = f"{mod_name}_{Path(file).name}"
                dest_file_path = file_merge_path.parent / dest_file_name
                shutil.copy2(source_file_path, dest_file_path)
                print(color_text(f"Copied {source_file_path} to {dest_file_path}", "green"))
            else:
                print(color_text(f"File {file} not found in cache for {mod_name}.", "red"))

        # User instructions and merge handling remain the same
        print(color_text("\nAll conflicting files have been copied to the merge folder:", "cyan"))
        print(color_text(f"{merge_folder}\n", "yellow"))
        print(color_text("Instructions for merging:", "cyan"))
        print(color_text("1. Open WinMerge.", "white"))
        print(color_text("2. In WinMerge, select 'File' -> 'Open...'.", "white"))
        print(color_text("3. In the 'Left' field, select one of the mod files to start with.", "white"))
        print(color_text("4. In the 'Right' field, select another mod file to compare and merge.", "white"))
        print(color_text("5. Perform the merge as needed.", "white"))
        print(color_text("6. Repeat steps 3-5 until all files are merged.", "white"))
        print(color_text(f"7. Save the final merged file with prefix as '{merged_file_name}' in the same folder with the conflicting files.", "white"))
        print(color_text("8. Ensure the final merged file is saved in the correct subdirectory inside the merge folder.", "white"))
        print(color_text("9. Close WinMerge when done to continue.", "white"))

        input(color_text("\nPress Enter after you have completed the merges in WinMerge...", "cyan"))

        if merged_file_path.exists():
            destination_path = TEMP_REPACK_DIR / file.replace('/', os.sep)
            destination_path.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(merged_file_path, destination_path)
            print(color_text(f"Final merged file saved to {destination_path}", "green"))
        else:
            print(color_text(f"No merged file named '{merged_file_name}' found for {file}.", "red"))
            print(color_text("Please ensure you have saved the merged file with the correct prefix.", "red"))
            input(color_text("Press Enter to retry or Ctrl+C to exit...", "cyan"))
            return compare_files({file: conflicting_files[file]})

    print(color_text("\nAll files have been processed.", "green"))













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
    """Version 2.0 - Integrated with PakCache for improved performance"""
    SCRIPT_NAME = "Mod Merging Helper"
    SCRIPT_VERSION = "1.0"
    SCRIPT_AUTHOR = "63OR63"
    print(color_text(f"{SCRIPT_NAME} v{SCRIPT_VERSION} by {SCRIPT_AUTHOR}", "magenta"))

    # Initialize cache and clean old temp files
    global pak_cache
    pak_cache = PakCache()  # Ensure pak_cache is initialized
    cleanup_temp_files()

    # Pass pak_cache to process_pak_files
    pak_sources = process_pak_files(pak_files, pak_cache)
    file_tree, file_count, file_sources, file_hashes = build_file_tree(pak_sources)

    print(color_text("\nCombined File Tree:", "magenta"))
    display_file_tree(file_tree, file_count=file_count)

    # Determine conflicts based on cached hashes
    conflicting_files = {}
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
                print(color_text(f"Copied non-conflicting file to {destination_path}", "green"))

    if not conflicting_files:
        print(color_text("\nNo conflicting files with differing contents found.", "green"))
        print(color_text("Repacking merged files...", "white"))
        repack_pak()
        input(color_text("\nPress Enter to close...", "cyan"))
        sys.exit(0)
    else:
        display_conflicts(conflicting_files, file_hashes)

    if not winmerge_exists:
        print(color_text("\nWinMerge is required for merging but was not found.", "red"))
        sys.exit(1)

    print(color_text("\nStarting manual merging process using WinMerge...", "cyan"))
    compare_files(conflicting_files)

    print(color_text(f"\nRepacking merged files...", "white"))
    repack_pak()

    rename_conflicting_paks(conflicting_files)
    cleanup_temp_files()

    input(color_text("\nProcess completed. Press Enter to close...", "cyan"))
    sys.exit(0)












if __name__ == "__main__":
    missing_exe = False
    kdiff3_exists = os.path.isfile(KDIFF3_PATH)
    winmerge_exists = os.path.isfile(WINMERGE_PATH)

    if not os.path.isfile(REPAK_PATH):
        print(color_text(f"Error: repak does not exist at {REPAK_PATH}", "red"))
        print(color_text(f"\nPlease install it, correct the path at the top of the script, and try again.", "red"))
        missing_exe = True

    if not kdiff3_exists:
        print(color_text(f"Warning: kdiff3 does not exist at {KDIFF3_PATH}", "yellow"))

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


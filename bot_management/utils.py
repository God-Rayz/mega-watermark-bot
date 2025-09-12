import zlib
import base64
import re
import os
import json
import shutil

def create_folder_names_mapping(mega_links, names):
    """
    Creates a mapping from each MEGA folder URL to its corresponding name.
    The mapping is based on the order in the provided lists:
    the first link gets the first name, etc.

    Args:
        mega_links (list[str]): List of processed MEGA folder URLs.
        names (list[str]): List of names corresponding to each link.

    Returns:
        dict: A dictionary mapping each mega link to its corresponding name.
    """
    mapping = {}
    for link, name in zip(mega_links, names):
        # Remove the "$" flag if present.
        if link.startswith("$"):
            link = link.lstrip("$")
        mapping[link] = name
    return mapping
    
def copy_bulk_files_to_process(process_folder, bulk_folder="bulk_process"):
    """
    Copies the three TXT files (emails.txt, megas.txt, names.txt) from the bulk folder to the process folder.
    
    Args:
        process_folder (str): The destination folder path.
        bulk_folder (str): The source folder where the files are stored.
    """
    file_names = ["emails.txt", "megas.txt", "names.txt"]
    for file_name in file_names:
        src_path = os.path.join(bulk_folder, file_name)
        dst_path = os.path.join(process_folder, file_name)
        if os.path.exists(src_path):
            shutil.copy(src_path, dst_path)

def optimize_account_allocation(accounts, folder_sizes, process_folder, account_remaining=None):
    """
    Distribute folders among accounts using a best-fit strategy,
    taking into account the current remaining capacity of each account.
    
    For folders with size <= 20GB (the original threshold), assign each to the account
    whose remaining capacity is the closest match (minimal waste). For folders > 20GB,
    assign exclusively to an account with no allocations if its remaining capacity is sufficient.
    
    Args:
        accounts (list[str]): List of account identifiers.
        folder_sizes (dict): Mapping {folder_link: size_in_GB} for pending folders.
        process_folder (str): Path to the process folder where a JSON file will be saved.
        account_remaining (dict, optional): Current remaining capacity per account.
            If not provided, each account is initialized with 20.0 GB.
    
    Returns:
        tuple: (account_allocations, unallocated_folders)
            account_allocations: dict mapping each account to a list of (folder, size) tuples.
            unallocated_folders: list of (folder, size) tuples that could not be allocated.
    """
    initial_capacity = 20.0
    if account_remaining is None:
        account_remaining = {account: initial_capacity for account in accounts}
    
    account_allocations = {account: [] for account in accounts}
    unallocated_folders = []
    
    # Sort folders from largest to smallest.
    sorted_folders = sorted(folder_sizes.items(), key=lambda item: item[1], reverse=True)
    
    for folder, size in sorted_folders:
        # For folders not larger than 20GB, use best-fit allocation.
        if size <= 20.0:
            best_account = None
            min_waste = None
            for account in accounts:
                remaining = account_remaining[account]
                if remaining >= size:
                    waste = remaining - size
                    if best_account is None or waste < min_waste:
                        best_account = account
                        min_waste = waste
            if best_account is not None:
                account_allocations[best_account].append((folder, size))
                account_remaining[best_account] -= size
            else:
                unallocated_folders.append((folder, size))
        else:
            # For folders >20GB, assign exclusively to an account with no allocations if possible.
            empty_account = None
            for account in accounts:
                if len(account_allocations[account]) == 0 and account_remaining[account] >= size:
                    empty_account = account
                    break
            if empty_account is not None:
                account_allocations[empty_account].append((folder, size))
                account_remaining[empty_account] -= size
            else:
                unallocated_folders.append((folder, size))
    
    # Second pass: try to allocate remaining folders by finding any available space
    # This time, be more aggressive about finding space
    remaining_unallocated = []
    for folder, size in unallocated_folders:
        allocated = False
        
        # Try to find any account with enough space, but NEVER exceed the limit
        for account in accounts:
            remaining = account_remaining[account]
            if remaining >= size:
                account_allocations[account].append((folder, size))
                account_remaining[account] -= size
                allocated = True
                break
        
        if not allocated:
            # If still not allocated, try to find any account with any remaining space
            # but still respect the hard limit
            for account in accounts:
                remaining = account_remaining[account]
                if remaining > 0 and remaining >= size:
                    account_allocations[account].append((folder, size))
                    account_remaining[account] -= size
                    allocated = True
                    break
        
        if not allocated:
            # Final attempt: find any account that can fit it without exceeding 19.9GB total
            for account in accounts:
                # Calculate total size this account would have after adding this folder
                current_total = sum(size for _, size in account_allocations[account] if size)
                if current_total + size <= initial_capacity:  # Strict limit enforcement
                    account_allocations[account].append((folder, size))
                    allocated = True
                    break
        
        if not allocated:
            remaining_unallocated.append((folder, size))
    
    # Save the allocation mapping to file.
    mapping = {
        "account_allocations": account_allocations,
        "unallocated_folders": remaining_unallocated,
        "account_remaining": account_remaining
    }
    output_file = os.path.join(process_folder, "allocation_mapping.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)
    
    return account_allocations, remaining_unallocated
     
def create_process_folder(base_folder="bulk_processes"):
    """
    Creates a new process folder (e.g., process_1, process_2, etc.) inside the base folder.
    After creating the new folder, it ensures that only the last 3 process folders remain 
    in the base folder by deleting older ones.

    Args:
        base_folder (str): The base folder where process folders will be created.
        
    Returns:
        str: The path to the newly created process folder.
    """

    if not os.path.exists(base_folder):
        os.makedirs(base_folder)
    
    # Get a list of existing process folders that start with "process_"
    existing = [d for d in os.listdir(base_folder)
                if os.path.isdir(os.path.join(base_folder, d)) and d.startswith("process_")]

    if existing:
        # Extract numeric part and compute the maximum index
        indices = [int(d.split("_")[1]) for d in existing if d.split("_")[1].isdigit()]
        new_index = max(indices) + 1
    else:
        new_index = 1
    process_folder = os.path.join(base_folder, f"process_{new_index}")
    os.makedirs(process_folder)
    
    # Now, re-read the list of process folders (including the new one)
    process_folders = [d for d in os.listdir(base_folder)
                       if os.path.isdir(os.path.join(base_folder, d)) and d.startswith("process_")]
    # Extract numeric index and sort folders by that index in ascending order.
    process_folders_sorted = sorted(
        process_folders,
        key=lambda d: int(d.split("_")[1])
    )
    
    # If more than 3 process folders exist, delete the oldest ones (keep only the last 3).
    while len(process_folders_sorted) > 3:
        oldest = process_folders_sorted.pop(0)
        shutil.rmtree(os.path.join(base_folder, oldest))
    
    return process_folder

def is_valid_email(email: str) -> bool:
    """
    Validate an email address using a simple regex.
    """
    # Basic email regex pattern; adjust as needed.
    pattern = r'^[\w\.-]+@[\w\.-]+\.\w+$'
    return re.match(pattern, email) is not None

def trim_mega_url(url: str) -> str:
    """
    Trim a MEGA URL so that only the original folder remains.
    Example:
    Input:  "https://mega.nz/folder/LnoQDLiA#YseWFgisvki74zefweEOdw/folder/Tq40HbDZ"
    Output: "https://mega.nz/folder/LnoQDLiA#YseWFgisvki74zefweEOdw"
    """
    # Split on '/folder'
    parts = url.split("/folder")
    if len(parts) < 2:
        # No '/folder' found, return as is.
        return url

    # Reassemble the URL using only the first folder part.
    # parts[0] is the URL before the first occurrence, parts[1] is the first folder.
    trimmed_url = parts[0] + "/folder" + parts[1].split()[0]
    return trimmed_url
    
def extract_email_password(file_path):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
            
        if len(lines) < 2:
            return False, False
        
        email = lines[0].strip()
        password = lines[1].strip()
        
        return email, password
    
    except FileNotFoundError:
        return False, False

def update_email_password(file_path, new_email=None, new_password=None):
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        if len(lines) < 1:
            lines.append('\n')
        if len(lines) < 2:
            lines.append('\n')

        if new_email is not None:
            lines[0] = new_email.strip() + '\n'

        if new_password is not None:
            lines[1] = new_password.strip() + '\n'

        with open(file_path, 'w') as file:
            file.writelines(lines)

        return True

    except FileNotFoundError:
        return False

def compress_link(mega_link):
    compressed = zlib.compress(mega_link.encode())
    encoded = base64.urlsafe_b64encode(compressed).decode()
    return encoded

def decompress_link(encoded_link):
    decoded = base64.urlsafe_b64decode(encoded_link.encode())
    decompressed = zlib.decompress(decoded).decode()
    return decompressed

def split_large_folders_and_optimize_allocation(accounts, folder_sizes, process_folder, account_remaining=None):
    """
    Split large folders (>20GB) by importing the entire mega link and selectively deleting content.
    
    This function:
    1. Identifies large folders (>20GB) that need chunking
    2. Creates a plan to import the entire mega into multiple accounts
    3. For each account, determines what content to keep and what to delete
    4. Ensures no account exceeds 19.9GB while maximizing content retention
    
    IMPORTANT: NO ACCOUNT WILL EVER EXCEED 19.9GB UNDER ANY CIRCUMSTANCES.
    
    Args:
        accounts (list[str]): List of account identifiers.
        folder_sizes (dict): Mapping {folder_link: size_in_GB} for pending folders.
        process_folder (str): Path to the process folder where a JSON file will be saved.
        account_remaining (dict, optional): Current remaining capacity per account.
            If not provided, each account is initialized with 19.9 GB.
    
    Returns:
        tuple: (account_allocations, unallocated_folders, chunked_folders)
            account_allocations: dict mapping each account to a list of (folder, size, chunk_plan, account_index) tuples.
            unallocated_folders: list of (folder, size) tuples that could not be allocated.
            chunked_folders: dict mapping original large folders to their chunking plans.
    """
    initial_capacity = 19.9  # Maximum chunk size - HARD LIMIT
    if account_remaining is None:
        account_remaining = {account: initial_capacity for account in accounts}
    
    # Create a working copy of folder sizes
    working_folder_sizes = folder_sizes.copy()
    chunked_folders = {}
    
    # Step 1: Identify large folders that need chunking
    folders_to_chunk = []
    for folder, size in folder_sizes.items():
        if size and size > 20.0:
            folders_to_chunk.append((folder, size))
    
    # Step 2: Create chunking plans for large folders
    for folder, size in folders_to_chunk:
        # Calculate how many accounts we need for this folder
        num_accounts_needed = max(1, int(size / initial_capacity) + (1 if size % initial_capacity > 0 else 0))
        
        # Create a chunking plan
        chunk_plan = {
            'original_folder': folder,
            'total_size': size,
            'num_accounts': num_accounts_needed,
            'accounts_needed': num_accounts_needed,
            'chunks': []
        }
        
        # Create virtual chunks for allocation purposes
        remaining_size = size
        for i in range(num_accounts_needed):
            chunk_size = min(remaining_size, initial_capacity)
            chunk_id = f"{folder}_chunk_{i + 1}"
            chunk_plan['chunks'].append({
                'chunk_id': chunk_id,
                'size': chunk_size,
                'account_index': i,
                'content_plan': {
                    'keep_folders': [],  # Will be populated during processing
                    'delete_folders': [],  # Will be populated during processing
                    'keep_files': [],  # Will be populated during processing
                    'delete_files': []  # Will be populated during processing
                }
            })
            remaining_size -= chunk_size
        
        chunked_folders[folder] = chunk_plan
    
    # Step 3: Optimize allocation of all folders (including chunks)
    account_allocations = {account: [] for account in accounts}
    unallocated_folders = []
    
    # Create virtual allocation problem
    virtual_folders = {}
    
    # Add regular folders
    for folder, size in folder_sizes.items():
        if folder not in chunked_folders:
            virtual_folders[folder] = size
    
    # Add virtual chunks
    for folder, chunk_plan in chunked_folders.items():
        for chunk in chunk_plan['chunks']:
            virtual_folders[chunk['chunk_id']] = chunk['size']
    
    # Sort all virtual folders (including chunks) from largest to smallest
    sorted_folders = sorted(virtual_folders.items(), key=lambda item: item[1], reverse=True)
    
    # First pass: try to allocate optimally
    for folder, size in sorted_folders:
        if not size:
            # If no size is detected, use a completely empty account
            for account in accounts:
                if len(account_allocations[account]) == 0 and account_remaining[account] == initial_capacity:
                    account_allocations[account].append((folder, size, None, None))
                    break
            else:
                unallocated_folders.append((folder, size))
            continue
        
        # Find the best account for this folder/chunk
        best_account = None
        min_waste = None
        
        for account in accounts:
            remaining = account_remaining[account]
            if remaining >= size:
                waste = remaining - size
                if best_account is None or waste < min_waste:
                    best_account = account
                    min_waste = waste
        
        if best_account is not None:
            # For chunks, include the chunking plan
            chunk_plan = None
            account_index = None
            if folder in [chunk['chunk_id'] for chunk_plan in chunked_folders.values() for chunk in chunk_plan['chunks']]:
                # This is a chunk, find its plan
                for orig_folder, plan in chunked_folders.items():
                    for chunk in plan['chunks']:
                        if chunk['chunk_id'] == folder:
                            chunk_plan = plan
                            account_index = chunk['account_index']
                            break
                    if chunk_plan:
                        break
            
            account_allocations[best_account].append((folder, size, chunk_plan, account_index))
            account_remaining[best_account] -= size
        else:
            unallocated_folders.append((folder, size))
    
    # Second pass: try to allocate remaining folders by finding any available space
    # This time, be more aggressive about finding space, but NEVER exceed 19.9GB
    remaining_unallocated = []
    for folder, size in unallocated_folders:
        allocated = False
        
        # Try to find any account with enough space, but NEVER exceed the limit
        for account in accounts:
            remaining = account_remaining[account]
            if remaining >= size:
                account_allocations[account].append((folder, size, None, None))
                account_remaining[account] -= size
                allocated = True
                break
        
        if not allocated:
            # If still not allocated, try to find any account with any remaining space
            # but still respect the hard limit
            for account in accounts:
                remaining = account_remaining[account]
                if remaining > 0 and remaining >= size:
                    account_allocations[account].append((folder, size, None, None))
                    account_remaining[account] -= size
                    allocated = True
                    break
        
        if not allocated:
            # Final attempt: find any account that can fit it without exceeding 19.9GB total
            for account in accounts:
                # Calculate total size this account would have after adding this folder
                current_total = sum(size for _, size, _, _ in account_allocations[account] if size)
                if current_total + size <= initial_capacity:  # Strict limit enforcement
                    account_allocations[account].append((folder, size, None, None))
                    allocated = True
                    break
        
        if not allocated:
            remaining_unallocated.append((folder, size))
    
    # Step 4: Save the allocation mapping to file
    mapping = {
        "account_allocations": account_allocations,
        "unallocated_folders": remaining_unallocated,
        "account_remaining": account_remaining,
        "chunked_folders": chunked_folders
    }
    output_file = os.path.join(process_folder, "allocation_mapping.json")
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(mapping, f, indent=4)
    
    return account_allocations, remaining_unallocated, chunked_folders

def cleanup_processed_content_files():
    """
    Automatically delete all processed_content_*.json files from the root directory.
    These files are created during watermarking to track processed content across accounts
    and should be cleaned up after the watermarking process is complete.
    
    Returns:
        int: Number of files deleted
    """
    import glob
    
    # Find all processed_content_*.json files in the root directory
    pattern = "processed_content_*.json"
    files_to_delete = glob.glob(pattern)
    
    deleted_count = 0
    for file_path in files_to_delete:
        try:
            os.remove(file_path)
            deleted_count += 1
            print(f"✅ Deleted processed content file: {file_path}")
        except Exception as e:
            print(f"❌ Error deleting {file_path}: {e}")
    
    if deleted_count > 0:
        print(f"🧹 Cleanup completed: {deleted_count} processed content file(s) deleted")
    else:
        print("🧹 No processed content files found to clean up")
    
    return deleted_count

def chunk_text(text, chunk_size=3000):
    """
    Split text into chunks of specified size to avoid Telegram's message length limit.
    
    Args:
        text (str): The text to chunk
        chunk_size (int): Maximum size of each chunk (default: 3000, safe margin below 4096 limit)
    
    Yields:
        str: Text chunks
    """
    for i in range(0, len(text), chunk_size):
        yield text[i:i+chunk_size]

async def send_long_message(call, message_text, header="", chunk_size=3000):
    """
    Send a long message in chunks to avoid Telegram's MESSAGE_TOO_LONG error.
    
    Args:
        call: The callback object used for sending messages
        message_text (str): The message text to send
        header (str): Optional header to prepend to the first chunk
        chunk_size (int): Maximum size of each chunk (default: 3000)
    """
    full_text = header + message_text
    chunks = list(chunk_text(full_text, chunk_size))
    
    # Send the first chunk (with header)
    await call.message.reply_text(chunks[0])
    
    # Send any additional chunks without header
    for chunk in chunks[1:]:
        await call.message.reply_text(chunk)
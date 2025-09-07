from bot_management import FILE_NAME, FOLDER_NAME, UPLOADS_FOLDER, DELETE_FILES, PICS_KEYWORDS, VIDS_KEYWORDS, PPV_KEYWORDS, SITERIP_KEYWORDS, LOGS
from collections import Counter
import subprocess
import time
import re
import os
import shutil

class MEGA:
    def __init__(self, email, password, proxy_url=None, proxy_username=None, proxy_password=None):
        self.email = email
        self.password = password
        self.proxy_url = proxy_url
        self.proxy_username = proxy_username
        self.proxy_password = proxy_password
        self.proxy_status = False  

    def run_raw_command(self, command):
        try:
            log_file_path = os.path.join(os.path.dirname(__file__), 'logs', 'mega_debug.log')
            with open(log_file_path, 'a', encoding='utf-8') as log_file:
                result = subprocess.run(
                    command, shell=True, capture_output=True, text=True, timeout=30, encoding='utf-8'
                )
                log_file.write(f"--- COMMAND ---\n{command}\n")
                log_file.write(f"--- STDOUT ---\n{result.stdout}\n")
                
                # Filter out unwanted stderr messages
                filtered_stderr_lines = []
                for line in result.stderr.splitlines():
                    # Skip upgrade messages and other informational messages
                    skip_patterns = [
                        "You have exeeded your available storage.",
                        "You are running out of available storage.",
                        "You can change your account plan to increase your quota limit.",
                        "See \"help --upgrade\" for further details.",
                        "You are currently using",
                        "of your",
                        "storage quota.",
                        "Upgrade your account to get more storage.",
                        "Your account is currently",
                        "You can upgrade your account",
                        "For more information, see",
                        "help --upgrade",
                        "---",
                        "|",
                        "You have exceeded your available storage.",
                        "You are running out of available storage."
                    ]
                    
                    should_skip = any(pattern in line for pattern in skip_patterns)
                    if not should_skip:
                        filtered_stderr_lines.append(line)
                
                filtered_stderr = "\n".join(filtered_stderr_lines)
                
                log_file.write(f"--- STDERR ---\n{filtered_stderr}\n")
                log_file.write(f"--- RETURN CODE ---\n{result.returncode}\n\n")

            stdout = result.stdout if result.stdout is not None else ""
            stderr = result.stderr if result.stderr is not None else ""
            if result.returncode != 0:
                return stderr.strip(), result.returncode
            return stdout.strip(), result.returncode
        except subprocess.TimeoutExpired:
            print(f"⚠️ Command timed out after 30 seconds: {command}")
            return "Command timed out after 30 seconds.", 1

    def run_command(self, command, use_proxy=False):
        """
        Run MEGAcmd command with an optional proxy status check.
        
        Args:
            command (str): The command to execute.
            use_proxy (bool): If True, check and reconfigure proxy if needed.
                              Defaults to False.
        
        Returns:
            tuple: (output, returncode) from running the command.
        """
        if use_proxy:
            if not self.proxy_status and self.proxy_url:
                self.check_proxy_status()
        return self.run_raw_command(command)

    def check_proxy_status(self):
        """
        Check if the proxy is active in MEGAcmd.
        """
        result, returncode = self.run_raw_command("mega-proxy")
        if "No proxy configuration found" in result:
            print("Proxy is disabled; reactivating.")
            self.configure_proxy()
        else:
            print("Proxy is active.")

    def configure_proxy(self):
        """
        Configure MEGAcmd proxy if specified.
        """
        if self.proxy_url:
            command = f"mega-proxy {self.proxy_url}"
            if self.proxy_username and self.proxy_password:
                command += f" --username={self.proxy_username} --password={self.proxy_password}"
            result, returncode = self.run_raw_command(command)
            if returncode == 0:
                print("Proxy configured successfully.")
                self.proxy_status = True
            else:
                print(f"Failed to configure proxy: {result}")

    def server_status(self):
        command = 'mega-help'
        output, returncode = self.run_command(command)

        if returncode == 0:
            print("MEGAcmd server is running.")
            return True
        else:
            print(f"MEGAcmd server is not running: {output}")
            return False

    def login(self):
        command = f'mega-login {self.email} {self.password}'
        output, returncode = self.run_command(command)
        if returncode == 0:
            print(f"Login successful for {self.email}")
            return True
        else:
            print(f"Login failed for {self.email}: {output}")
            print(f"Return code: {returncode}")
            return False

    def logout(self):
        command = 'mega-logout'
        output, returncode = self.run_command(command)
    
        if returncode == 0:
            print("Logged out successfully.")
            return True
        else:
            print(f"Failed to log out: {output}")
            return False

    def whoami(self):
        command = 'mega-whoami'
        output, returncode = self.run_command(command)
        
        if returncode == 57:
            return False
        else:
            return True

    def import_mega_link(self, link):
        command = f'mega-import {link}'
        output, returncode = self.run_command(command)

        if "NO_KEY" in output:
            print(f"The folder is corrupted (NO_KEY)")
            return False

        if returncode == 0:
            print(f"Imported link: {output}")
            return output
        else:
            print(f"Failed to import MEGA link: {output}")

    def rename_folder(self, current_folder_name, model_name):
        final_folder_name = f"{model_name} {FOLDER_NAME}".strip()
    
        folder_name_variations = [
            current_folder_name.strip(),  # No trailing space
            current_folder_name + " ",    # 1 trailing space
            current_folder_name + "  ",   # 2 trailing spaces
            current_folder_name + "   "   # 3 trailing spaces
        ]

        for attempt, folder_name in enumerate(folder_name_variations, 1):
            print(f"Attempt {attempt}: Renaming folder '{folder_name}'")
        
            command = f'mega-mv "{folder_name.lstrip("/")}" "{final_folder_name.lstrip("/")}"'
            output, returncode = self.run_command(command)
        
            if returncode == 0:
                print(f"Successfully renamed folder: {folder_name} to /{final_folder_name}")
                return f'/{final_folder_name}'
            else:
                print(f"Failed to rename folder '{folder_name}' on attempt {attempt}: {output}")
    
        print(f"Failed to rename folder {current_folder_name} after multiple attempts.")
        return False

    def fix_trailing_spaces_in_subfolders(self, root_folder):
        command = f'mega-find "{root_folder.lstrip("/")}" --type=d'
        output, returncode = self.run_command(command)

        if returncode != 0:
            print(f"Failed to list subfolders in {root_folder}: {output}")
            return False

        subfolders = output.splitlines()

        for folder_path in subfolders:
            if folder_path == root_folder:
                continue

            list_files_command = f'mega-ls "{folder_path.lstrip("/")}"'
            _, returncode = self.run_command(list_files_command)

            if returncode == 0:
                print(f"Folder '{folder_path}' is accessible, no trailing spaces.")
                continue  

            original_folder_name = folder_path.split("/")[-1]
            parent_path = "/".join(folder_path.split("/")[:-1])  

            folder_name_variations = [
                original_folder_name.strip(),      # No trailing space
                original_folder_name.strip() + " ",  # 1 trailing space
                original_folder_name.strip() + "  ", # 2 trailing spaces
                original_folder_name.strip() + "   " # 3 trailing spaces
            ]

            renamed = False
            for attempt, new_folder_name in enumerate(folder_name_variations, 1):
                new_folder_path = f"{parent_path}/{new_folder_name}"
                rename_command = f'mega-mv "{folder_path.lstrip("/")}" "{new_folder_path.lstrip("/")}"'
                output, returncode = self.run_command(rename_command)

                if returncode == 0:
                    print(f"Successfully renamed folder: '{folder_path}' -> '{new_folder_path}'")
                    folder_path = new_folder_path  
                    renamed = True
                    break
                else:
                    print(f"Attempt {attempt}: Failed to rename folder to '{new_folder_name}': {output}")

            if not renamed:
                print(f"Failed to fix trailing spaces for folder: {folder_path}")

        return True

    def delete_unwanted_files(self, folder_path):
        allowed_extensions = re.compile(r'\.(mp3|wav|flac|jpg|jpeg|png|gif|mp4|mkv|avi|mov|m4v)$', re.IGNORECASE)
        video_extensions = re.compile(r'\.(mp4|mkv|avi|mov|m4v)$', re.IGNORECASE)

        command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
        output, returncode = self.run_command(command)

        if returncode != 0:
            print(f"Failed to list files in MEGA folder: {output}")
            return False

        for file_path in output.splitlines():
            file_name = file_path.split("/")[-1]
            file_base_name = os.path.splitext(file_name)[0]

            if folder_path == "/".join(file_path.split("/")[:-1]):
                if video_extensions.search(file_name):
                    print(f"Skipping video file in root: {file_path}")
                    continue

                print(f"Deleting non-video file in root: {file_path}")
                delete_command = f'mega-rm "{file_path.lstrip("/")}"'
                self.run_command(delete_command)
                continue

            if file_base_name in DELETE_FILES or not allowed_extensions.search(file_name):
                print(f"Deleting file: {file_path}")
                delete_command = f'mega-rm "{file_path.lstrip("/")}"'
                self.run_command(delete_command)

        folder_command = f'mega-find "{folder_path.lstrip("/")}" --type=d'
        folder_output, folder_returncode = self.run_command(folder_command)

        if folder_returncode == 0:
            for folder in folder_output.splitlines():
                folder_name = folder.split("/")[-1]  

                if folder_name in DELETE_FILES:
                    print(f"Deleting folder (matched DELETE_FILES): {folder}")
                    delete_folder_command = f'mega-rm -r -f "{folder.lstrip("/")}"'
                    self.run_command(delete_folder_command)
                    continue

                folder_ls_command = f'mega-ls "{folder.lstrip("/")}"'
                folder_ls_output, _ = self.run_command(folder_ls_command)

                if not folder_ls_output.strip():  
                    print(f"Deleting empty folder: {folder}")
                    delete_folder_command = f'mega-rm -r -f "{folder.lstrip("/")}"'
                    self.run_command(delete_folder_command)

        print("Unwanted files and empty folders have been deleted.")
        return True

    def rename_files_in_subfolders(self, mega_folder_path, base_name=FILE_NAME):
        command = f'mega-find "{mega_folder_path.lstrip("/")}"'
        output, returncode = self.run_command(command)
        
        if returncode != 0:
            print(f"Failed to list files in MEGA folder: {output}")
            return False
        
        folder_file_count = {}

        valid_file_extensions = re.compile(r'\.(mp3|wav|flac|jpg|jpeg|png|gif|mp4|mkv|avi|mov|m4v)$', re.IGNORECASE)

        for file_path in output.splitlines():
            if not valid_file_extensions.search(file_path):
                continue

            folder_path = "/".join(file_path.split("/")[:-1])  
            file_extension = os.path.splitext(file_path)[1]    

            if folder_path not in folder_file_count:
                folder_file_count[folder_path] = 1  

            new_file_name = f"{base_name} {folder_file_count[folder_path]}{file_extension}"
            
            new_file_path = f"{folder_path}/{new_file_name}"

            rename_command = f'mega-mv "{file_path.lstrip("/")}" "{new_file_path.lstrip("/")}"'
            rename_output, rename_returncode = self.run_command(rename_command)

            if rename_returncode == 0:
                print(f"Renamed: {file_path} -> {new_file_path}")
            else:
                print(f"Failed to rename {file_path}: {rename_output}")

            folder_file_count[folder_path] += 1

        print("File renaming completed.")
        return True

    def rename_subfolders(self, mega_folder_path, multiple_models, watermark_text=FOLDER_NAME):
        command = f'mega-find "{mega_folder_path.lstrip("/")}" --type=d'
        output, returncode = self.run_command(command)

        if returncode != 0:
            print(f"Failed to list subfolders: {output}")
            return False

        subfolders = output.splitlines()
        if not subfolders or (len(subfolders) == 1 and subfolders[0] == mega_folder_path):
            print("No subfolders to rename.")
            return True

        folder_name_count = {}

        # Sort subfolders by depth to rename from the inside out, preventing path changes from breaking subsequent renames.
        subfolders.sort(key=lambda x: x.count('/'), reverse=True)

        for folder_path in subfolders:
            if folder_path == mega_folder_path.lstrip('/'):
                continue

            original_folder_name = folder_path.split("/")[-1]
            folder_name_lower = original_folder_name.lower()
            new_folder_name = ""  # Initialize new_folder_name

            # Determine the new folder name based on keywords or content type
            if any(kw.lower() in folder_name_lower for kw in PICS_KEYWORDS):
                new_folder_name = f"Pics {watermark_text}"
            elif any(kw.lower() in folder_name_lower for kw in VIDS_KEYWORDS):
                new_folder_name = f"Vids {watermark_text}"
            elif any(kw.lower() in folder_name_lower for kw in PPV_KEYWORDS):
                new_folder_name = f"PPV {watermark_text}"
            elif any(kw.lower() in folder_name_lower for kw in SITERIP_KEYWORDS):
                new_folder_name = f"Siterip {watermark_text}"
            else:
                # Fallback to content checking if no keywords match
                folder_content_type = self.check_folder_content(folder_path)
                if folder_content_type == 'pics':
                    new_folder_name = f"Pics {watermark_text}"
                elif folder_content_type == 'vids':
                    new_folder_name = f"Vids {watermark_text}"
                elif folder_content_type == 'audio':
                    new_folder_name = f"Audio {watermark_text}"
                else:
                    new_folder_name = f"Other {watermark_text}"

            # Handle duplicate folder names by appending a counter
            if new_folder_name:
                base_name = new_folder_name
                count = folder_name_count.get(base_name, 1)
                if count > 1:
                    new_folder_name = f"{base_name} {count}"
                
                folder_name_count[base_name] = count + 1

                # Perform the rename
                if new_folder_name != original_folder_name:
                    parent_path = "/".join(folder_path.split("/")[:-1])
                    new_folder_path = f"{parent_path}/{new_folder_name}"
                    
                    rename_command = f'mega-mv "{folder_path.lstrip("/")}" "{new_folder_path.lstrip("/")}"'
                    print(f"   🔄 Attempting rename: '{folder_path}' -> '{new_folder_path}'")
                    
                    rename_output, rename_returncode = self.run_command(rename_command)

                    if rename_returncode == 0:
                        print(f"   ✅ Successfully renamed: {folder_path} -> {new_folder_path}")
                    else:
                        print(f"   ❌ Failed to rename {folder_path}: {rename_output}")
                else:
                    print(f"   ⚠️ Folder '{folder_path}' already has the correct name.")

        print("Folder renaming completed.")
        return True

    def append_watermark(self, base_name, watermark_text):
        return f"{base_name} {watermark_text}"

    def check_folder_content(self, folder_path):
        command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
        output, returncode = self.run_command(command)
        
        if returncode != 0:
            print(f"Failed to list files in folder {folder_path}: {output}")
            return None

        pics_extensions = re.compile(r'\.(jpg|jpeg|png|gif|bmp)$', re.IGNORECASE)
        vids_extensions = re.compile(r'\.(mp4|mkv|avi|mov|wmv|m4v)$', re.IGNORECASE)
        audios_extensions = re.compile(r'\.(mp3|wav|flac|aac)$', re.IGNORECASE)

        file_types = []
        for file_path in output.splitlines():
            if pics_extensions.search(file_path):
                file_types.append('pics')
            elif vids_extensions.search(file_path):
                file_types.append('vids')
            elif audios_extensions.search(file_path):
                file_types.append('audio')

        total_files = len(file_types)
        if total_files == 0:
            return 'other'

        file_type_counts = Counter(file_types)

        pics_count = file_type_counts['pics']
        vids_count = file_type_counts['vids']

        if pics_count / total_files >= 0.8:
            return 'pics'
        elif vids_count / total_files >= 0.8:
            return 'vids'
        elif pics_count > 0 and vids_count > 0:
            return 'other'  
        else:
            return 'audio'  

    def upload_files_to_subfolders(self, mega_folder_path, local_directory=UPLOADS_FOLDER):
        command = f'mega-find "{mega_folder_path.lstrip("/")}" --type=d'
        output, returncode = self.run_command(command)
        
        if returncode != 0:
            print(f"Failed to list subfolders in MEGA folder: {output}")
            return False

        subfolders = output.splitlines()

        files_to_upload = [os.path.join(local_directory, f) for f in os.listdir(local_directory) if os.path.isfile(os.path.join(local_directory, f))]

        if not files_to_upload:
            print(f"No files found in the local directory: {local_directory}")
            return False

        for subfolder in subfolders:
            for file_path in files_to_upload:
                file_name = os.path.basename(file_path)
                upload_command = f'mega-put "{file_path}" "{subfolder.lstrip("/")}/{file_name}"'
                upload_output, upload_returncode = self.run_command(upload_command)

                if upload_returncode == 0:
                    print(f"Uploaded {file_name} to {subfolder}")
                else:
                    print(f"Failed to upload {file_name} to {subfolder}: {upload_output}")

        print("File upload completed.")
        return True
    
    def delayed_yes_command(self, command, delay=12):

        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, text=True, encoding='utf-8')

        time.sleep(delay)

        if process.poll() is None:  
            try:
                process.stdin.write("yes\n")
                process.stdin.flush()
            except OSError as e:
                print(f"Error while sending 'yes': {e}")
        
        stdout, stderr = process.communicate()

        return stdout, stderr

    def get_public_link(self, mega_folder_path):
        command = f'mega-export -a "{mega_folder_path.lstrip("/")}"'
        output, error = self.delayed_yes_command(command)

        output = output if output is not None else ""
        error = error if error is not None else ""

        combined_output = output + error

        public_link = None
        for line in combined_output.splitlines():
            if "Exported" in line:
                public_link = line.split(": ")[-1].strip()
                break

        if public_link:
            print(f"Public link for {mega_folder_path}: {public_link}")
        else:
            print(f"Failed to get public link for the folder: {combined_output}")

        return public_link

    def list_main_folders(self):
        command = 'mega-find / --type=d'
        output, returncode = self.run_command(command)
    
        if returncode != 0:
            print(f"Failed to list folders: {output}")
            return []
    
        main_folders = []
        for folder in output.splitlines():
            if folder.count('/') == 1:
                main_folders.append(folder)
    
        print(f"Main folders: {main_folders}")
        return main_folders

    def signup(self):
        command = f'mega-signup {self.email} {self.password}'

        output, returncode = self.run_command(command, use_proxy=True)
        print(output)

        if returncode == 0:
            print(f"✅ User registered successfully with email: {self.email}")
            print(output)
            return True
        else:
            print(f"❌ Registration failed: {output}")
            return False

    def confirm_MEGA_account(self, confirmation_link):
        command = f'mega-confirm {confirmation_link} {self.email} {self.password}'

        output, returncode = self.run_command(command, use_proxy=True)

        if returncode == 0:
            LOGS.info(f"Account confirmed successfully for {self.email}")
            return True
        else:
            LOGS.error(f"Failed to confirm account for {self.email}")
            return False

    def clear_cache(self):
        """
        Closes any running MegaCMD processes, clears its cache, and restarts it.
        """
        # Attempt to kill potential MegaCMD processes.
        process_names = ["megacmd.exe", "MEGAcmdServer.exe"]
        for proc in process_names:
            try:
                subprocess.run(["taskkill", "/F", "/IM", proc], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print(f"✅ Process {proc} closed successfully.")
            except subprocess.CalledProcessError as e:
                print(f"WARNING: Process {proc} not found or could not be killed: {e}")
        
        # Give processes time to terminate.
        time.sleep(3)
        
        # Determine cache directory.
        if os.name == "nt":
            cache_dir = os.path.join(os.environ["LOCALAPPDATA"], "MEGAcmd", ".megaCmd")
        else:
            cache_dir = os.path.join(os.path.expanduser("~"), ".megaCmd")
        
        # Attempt to remove the lock file separately.
        lock_file = os.path.join(cache_dir, "lockMCMD")
        if os.path.exists(lock_file):
            try:
                os.remove(lock_file)
                print("✅ Lock file removed.")
            except Exception as e:
                print(f"❌ Could not remove lock file: {e}")
        
        # Now try to remove the cache directory.
        if os.path.exists(cache_dir):
            try:
                shutil.rmtree(cache_dir)
                print("✅ Local cache cleared successfully.")
                self.proxy_status = False
            except Exception as e:
                print(f"❌ Failed to clear local cache: {e}")
                return False
        else:
            print("⚠️ Cache directory not found. Skipping cache clearing.")
        
        # Restart MegaCMD.
        try:
            # Update the path below to match your installation path for megacmd.exe.
            megacmd_path = r"C:\Users\Administrator\AppData\Local\MEGAcmd\MEGAcmdServer.exe"
            subprocess.Popen([megacmd_path])
            print("✅ MegaCMD restarted successfully.")
        except Exception as e:
            print(f"❌ Failed to restart MegaCMD: {e}")
            return False
            
        return True

    def check_account_usage(self):
        """
        Checks the account usage using the 'mega-df -h' command.
        
        Expected output sample:
        
        Cloud drive:             676.23 MB in      56 file(s) and       3 folder(s)
        Inbox:                    0.00   B in       0 file(s) and       0 folder(s)
        Rubbish bin:              0.00   B in       0 file(s) and       0 folder(s)
        ---------------------------------------------------------------------------
        USED STORAGE:            676.23 MB                        3.30% of 20.00 GB
        ---------------------------------------------------------------------------
        Total size taken up by file versions:     0.00   B
        
        This method extracts the used storage and total quota from the "USED STORAGE:" line.
        It assumes that the used value is provided in MB (if in MB, it divides by 1000 to get GB)
        and that the total is given in GB. It then calculates the available space as (total - used).
        
        Returns:
            dict: A dictionary with keys 'used', 'available', and 'total', each as a float in GB.
                For example: {"used": 0.68, "available": 19.32, "total": 20.00}
                Returns None if an error occurs.
        """
        import re

        command = 'mega-df -h'
        output, returncode = self.run_command(command)
        
        if returncode != 0:
            print(f"Failed to get usage: {output}")
            return None

        used = None
        total = None

        # Look for the line starting with "USED STORAGE:"
        for line in output.splitlines():
            if line.startswith("USED STORAGE:"):
                # Expected format: "USED STORAGE:            676.23 MB                        3.30% of 20.00 GB"
                m = re.search(r"USED STORAGE:\s+([\d.]+)\s+([A-Z]+).*of\s+([\d.]+)\s+GB", line)
                if m:
                    used_val, used_unit, total_val = m.groups()
                    used_val = float(used_val)
                    total_val = float(total_val)
                    
                    # Convert used value to GB
                    if used_unit.upper() == "KB":
                        used_gb = used_val / 1000000.0
                    elif used_unit.upper() == "MB":
                        used_gb = used_val / 1000.0
                    elif used_unit.upper() == "GB":
                        used_gb = used_val
                    elif used_unit.upper() == "B":
                        used_gb = used_val / (1000.0 ** 3)
                    else:
                        used_gb = used_val  # fallback
                    
                    used = used_gb
                    total = total_val
                break

        if used is None or total is None:
            print("Failed to parse account usage from output:")
            print(output)
            return None

        available = total - used
        # Ensure that we do not overestimate free space.
        available = max(0, round(available, 2))
        
        usage_info = {
            "used": round(used, 2),
            "available": available,
            "total": round(total, 2)
        }
        print(f"Account usage: {usage_info}")
        return usage_info

    def split_folder_into_chunks(self, folder_path, max_chunk_size_gb=19.9):
        """
        Split a large folder into chunks of specified maximum size.
        
        This method creates subfolders within the original folder, each containing
        a portion of the content that fits within the specified size limit.
        
        Args:
            folder_path (str): Path to the folder to split
            max_chunk_size_gb (float): Maximum size per chunk in GB (default: 19.9)
        
        Returns:
            list: List of chunk folder paths created
        """
        max_chunk_size_bytes = max_chunk_size_gb * 1024 * 1024 * 1024  # Convert GB to bytes
        
        # List all files in the folder with their sizes
        command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
        output, returncode = self.run_command(command)
        
        if returncode != 0:
            print(f"Failed to list files in folder: {output}")
            return []
        
        files = []
        current_size = 0
        chunks = []
        current_chunk = []
        chunk_number = 1
        
        # Parse file listing and group into chunks
        for line in output.splitlines():
            if not line.strip():
                continue
            
            # Extract file size and path (this is a simplified parser)
            # You may need to adjust based on actual mega-find output format
            parts = line.split()
            if len(parts) >= 2:
                try:
                    size = int(parts[0])  # Assuming first part is size in bytes
                    file_path = " ".join(parts[1:])  # Rest is the file path
                    
                    if current_size + size > max_chunk_size_bytes and current_chunk:
                        # Current chunk is full, create it
                        chunk_name = f"{folder_path}_chunk_{chunk_number}"
                        chunks.append({
                            'name': chunk_name,
                            'files': current_chunk,
                            'size': current_size
                        })
                        
                        # Reset for next chunk
                        current_chunk = [file_path]
                        current_size = size
                        chunk_number += 1
                    else:
                        current_chunk.append(file_path)
                        current_size += size
                        
                except ValueError:
                    # Skip lines that don't have size information
                    continue
        
        # Add the last chunk if it has content
        if current_chunk:
            chunk_name = f"{folder_path}_chunk_{chunk_number}"
            chunks.append({
                'name': chunk_name,
                'files': current_chunk,
                'size': current_size
            })
        
        # Create chunk folders and move files
        created_chunks = []
        for chunk in chunks:
            chunk_path = chunk['name']
            
            # Create chunk folder
            create_command = f'mega-mkdir "{chunk_path.lstrip("/")}"'
            output, returncode = self.run_command(create_command)
            
            if returncode == 0:
                print(f"Created chunk folder: {chunk_path}")
                
                # Move files to chunk folder
                for file_path in chunk['files']:
                    move_command = f'mega-mv "{file_path.lstrip("/")}" "{chunk_path.lstrip("/")}/"'
                    output, returncode = self.run_command(move_command)
                    
                    if returncode != 0:
                        print(f"Failed to move file {file_path} to chunk {chunk_path}: {output}")
                
                created_chunks.append(chunk_path)
            else:
                print(f"Failed to create chunk folder {chunk_path}: {output}")
        
        return created_chunks

    def _parse_du_output(self, output, returncode):
        """
        Parses the output of mega-du to extract size in bytes.
        """
        if returncode != 0:
            return None
        
        # The output is in the format:
        # FILENAME                                                                 SIZE
        # Koabuddhaxxx - ✨Downloaded Fr...From Leakifyhub.com✨ - 3.mp4:  1320308265
        # -----------------------------------------------------------------------------
        # Total storage used:                                                1320308265
        lines = output.splitlines()
        for line in lines:
            if ":" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    try:
                        return int(parts[1].strip())
                    except (ValueError, IndexError):
                        continue
        return None

    def calculate_keep_plan(self, folder_structure, chunk_plan, account_index):
        """
        Calculates what content to keep for a specific chunk based on the user's requirements.
        This version iterates through folders and the files within them to create a granular keep/delete plan.
        """
        max_size_gb = 19.9
        print(f"🎯 Target size for chunk {account_index + 1}: < {max_size_gb}GB")

        keep_plan = {
            'keep_folders': [], 'delete_folders': [],
            'keep_files': [], 'delete_files': [],
            'processed_for_next_chunk': {'folders': set(), 'files': set()}
        }
        
        current_size_gb = 0
        processed_content = self.get_processed_content(chunk_plan, account_index)

        # Combine and sort all items: folders first, then root files
        all_items = sorted(folder_structure['folders'], key=lambda x: x['name']) + sorted(folder_structure['files'], key=lambda x: x['name'])

        for item in all_items:
            is_folder = 'files' in item
            item_name = item['name']
            
            if is_folder:
                # --- FOLDER PROCESSING --- #
                if self.is_folder_processed(item_name, processed_content):
                    print(f"⏭️ Folder '{item_name}' was fully processed in a previous chunk. Deleting.")
                    keep_plan['delete_folders'].append(item)
                    continue

                # Check if this is a picture folder
                if item.get('is_picture_folder', False):
                    # Treat picture folders as single files - either keep the whole folder or delete it
                    if current_size_gb + item['size'] <= max_size_gb:
                        print(f"📸 Picture folder '{item_name}' ({item['size']:.2f}GB) fits as single unit. Keeping entire folder.")
                        current_size_gb += item['size']
                        keep_plan['keep_folders'].append(item)
                        keep_plan['processed_for_next_chunk']['folders'].add(item_name)
                    else:
                        print(f"🗑️ Picture folder '{item_name}' ({item['size']:.2f}GB) doesn't fit as single unit. Deleting entire folder.")
                        keep_plan['delete_folders'].append(item)
                else:
                    # Regular folder processing
                    # Check if the whole folder and its contents fit
                    if current_size_gb + item['size'] <= max_size_gb:
                        print(f"✅ Entire folder '{item_name}' ({item['size']:.2f}GB) fits. Keeping all.")
                        current_size_gb += item['size']
                        keep_plan['keep_folders'].append(item)
                        # Mark folder and all its files as processed for the next chunk
                        keep_plan['processed_for_next_chunk']['folders'].add(item_name)
                        for file_in_folder in item['files']:
                            keep_plan['processed_for_next_chunk']['files'].add(f"{item_name}:{file_in_folder['name']}")
                    else:
                        # Folder does not fit. Iterate through its files.
                        print(f"📦 Folder '{item_name}' ({item['size']:.2f}GB) is too large to fit. Processing files individually.")
                        files_to_keep_in_folder = []
                        for file_in_folder in sorted(item['files'], key=lambda x: x['name']):
                            file_key = f"{item_name}:{file_in_folder['name']}"
                            if file_key in processed_content['files']:
                                print(f"⏭️ File '{file_in_folder['name']}' in folder '{item_name}' was already processed. Deleting.")
                                keep_plan['delete_files'].append(file_in_folder)
                                continue
                            
                            if current_size_gb + file_in_folder['size'] <= max_size_gb:
                                print(f"✅ Keeping file '{file_in_folder['name']}' ({file_in_folder['size']:.2f}GB). Chunk size: {current_size_gb:.2f}GB")
                                current_size_gb += file_in_folder['size']
                                files_to_keep_in_folder.append(file_in_folder)
                                keep_plan['processed_for_next_chunk']['files'].add(file_key)
                            else:
                                print(f"🗑️ File '{file_in_folder['name']}' ({file_in_folder['size']:.2f}GB) doesn't fit. Deleting.")
                                keep_plan['delete_files'].append(file_in_folder)
                        
                        if files_to_keep_in_folder:
                            # If we kept some files, we need to keep the parent folder structure
                            # but only with the files we decided to keep.
                            # The move-and-replace deletion handles this implicitly.
                            keep_plan['keep_files'].extend(files_to_keep_in_folder)
                        else:
                            # No files from this folder were kept
                            keep_plan['delete_folders'].append(item)

            else:
                # --- ROOT FILE PROCESSING --- #
                parent_folder_name = item.get('parent_folder', 'root')
                if self.is_file_processed(item_name, parent_folder_name, processed_content):
                    print(f"⏭️ Root file '{item_name}' already processed. Deleting.")
                    keep_plan['delete_files'].append(item)
                    continue
                
                if current_size_gb + item['size'] <= max_size_gb:
                    print(f"✅ Keeping root file '{item_name}' ({item['size']:.2f}GB). Chunk size: {current_size_gb:.2f}GB")
                    current_size_gb += item['size']
                    keep_plan['keep_files'].append(item)
                    keep_plan['processed_for_next_chunk']['files'].add(f"{parent_folder_name}:{item_name}")
                else:
                    print(f"🗑️ Root file '{item_name}' ({item['size']:.2f}GB) doesn't fit. Deleting.")
                    keep_plan['delete_files'].append(item)

        print(f"\n📊 Keep Plan Summary for Chunk {account_index + 1}:")
        print(f"   - Final Chunk Size: {current_size_gb:.2f}GB / {max_size_gb}GB")
        print(f"   - Items to keep: {len(keep_plan['keep_folders'])} folders, {len(keep_plan['keep_files'])} files")
        print(f"   - Items to delete: {len(keep_plan['delete_folders'])} folders, {len(keep_plan['delete_files'])} files")

        return keep_plan

    def get_files_in_folder(self, folder_path):
        """
        Get detailed file information within a folder.
        """
        try:
            command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
            output, returncode = self.run_command(command)
            
            files = []
            if returncode == 0:
                for file_line in output.splitlines():
                    if file_line.strip():
                        file_name = file_line.split("/")[-1]
                        
                        du_command = f'mega-du "{file_line.lstrip("/")}"'
                        du_output, du_returncode = self.run_command(du_command)
                        size_bytes = self._parse_du_output(du_output, du_returncode)
                        file_size_gb = size_bytes / (1024*1024*1024) if size_bytes is not None else 0
                        
                        files.append({
                            'name': file_name,
                            'path': file_line,
                            'size': file_size_gb
                        })
            
            return files
            
        except Exception as e:
            print(f"Error getting files in folder {folder_path}: {e}")
            return []

    def get_processed_content(self, chunk_plan, account_index):
        """
        Get content that has already been processed in previous accounts.
        """
        processed = {'folders': set(), 'files': set()}
        if account_index == 0:
            return processed
        return self.load_processed_content(chunk_plan, account_index)

    def save_processed_content(self, chunk_plan, account_index, processed_content):
        """
        Save information about processed content for tracking across accounts.
        """
        try:
            import json
            import os
            
            original_folder = chunk_plan['original_folder']
            safe_name = "".join(c for c in original_folder if c.isalnum() or c in ('-', '_')).rstrip()
            tracking_file = f"processed_content_{safe_name}.json"
            
            existing_data = {}
            if os.path.exists(tracking_file):
                try:
                    with open(tracking_file, 'r', encoding='utf-8') as f:
                        existing_data = json.load(f)
                except: # Handle empty or corrupted file
                    existing_data = {}
            
            # Combine new processed content with existing
            all_processed_folders = set(existing_data.get('folders', []))
            all_processed_files = set(existing_data.get('files', []))
            all_processed_folders.update(processed_content['folders'])
            all_processed_files.update(processed_content['files'])

            existing_data['folders'] = list(all_processed_folders)
            existing_data['files'] = list(all_processed_files)
            
            with open(tracking_file, 'w', encoding='utf-8') as f:
                json.dump(existing_data, f, indent=4)
            
            print(f"✅ Saved processed content state to {tracking_file}")
            
        except Exception as e:
            print(f"❌ Error saving processed content: {e}")

    def load_processed_content(self, chunk_plan, account_index):
        """
        Load information about previously processed content.
        """
        try:
            import json
            import os
            
            original_folder = chunk_plan['original_folder']
            safe_name = "".join(c for c in original_folder if c.isalnum() or c in ('-', '_')).rstrip()
            tracking_file = f"processed_content_{safe_name}.json"
            
            if not os.path.exists(tracking_file):
                return {'folders': set(), 'files': set()}
            
            with open(tracking_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                processed = {
                    'folders': set(data.get('folders', [])),
                    'files': set(data.get('files', []))
                }
            
            print(f"✅ Loaded processed content from {tracking_file}: {len(processed['folders'])} folders, {len(processed['files'])} files")
            return processed
            
        except Exception as e:
            print(f"❌ Error loading processed content: {e}")
            return {'folders': set(), 'files': set()}

    def is_folder_processed(self, folder_name, processed_content):
        return folder_name in processed_content['folders']

    def is_file_processed(self, file_name, parent_folder, processed_content):
        file_key = f"{parent_folder}:{file_name}"
        return file_key in processed_content['files']

    def delete_unwanted_content(self, folder_path, keep_plan):
        """
        Delete unwanted content based on the keep plan with enhanced logging and verification.
        """
        try:
            print(f"🗑️ Starting deletion process for folder: {folder_path}")
            
            # If there's nothing to delete, we can stop early.
            if not keep_plan['delete_folders'] and not keep_plan['delete_files']:
                print("✅ Nothing to delete based on the keep plan.")
                return True

            # It is much safer and more efficient to move the content we want to KEEP
            # to a new folder, and then delete the entire original folder.

            # 1. Create a temporary folder for the content we want to keep.
            temp_keep_folder = f"{folder_path}_keep"
            create_command = f'mega-mkdir "{temp_keep_folder.lstrip("/")}"'
            print(f"Creating temp folder: {create_command}")
            output, returncode = self.run_command(create_command)
            if returncode != 0:
                print(f"❌ CRITICAL: Failed to create temp folder '{temp_keep_folder}'. Aborting deletion. Error: {output}")
                return False

            # 2. Move all the items we want to keep into the new folder.
            items_to_move = keep_plan['keep_folders'] + keep_plan['keep_files']
            for item in items_to_move:
                source_path = item['path']
                move_command = f'mega-mv "{source_path.lstrip("/")}" "{temp_keep_folder.lstrip("/")}/"'
                print(f"Moving item to keep: {move_command}")
                output, returncode = self.run_command(move_command)
                if returncode != 0:
                    print(f"⚠️ Failed to move '{item['name']}' to temp folder. Error: {output}")

            # 3. Delete the original folder, which now only contains unwanted items.
            delete_command = f'mega-rm -r -f "{folder_path.lstrip("/")}"'
            print(f"Deleting original folder: {delete_command}")
            output, returncode = self.run_command(delete_command)
            if returncode != 0:
                print(f"❌ CRITICAL: Failed to delete original folder '{folder_path}'. Error: {output}")
                # Attempt to clean up the temp folder we created
                self.run_command(f'mega-rm -r -f "{temp_keep_folder.lstrip("/")}"' )
                return False

            # 4. Rename the temporary folder back to the original folder's name.
            rename_command = f'mega-mv "{temp_keep_folder.lstrip("/")}" "{folder_path.lstrip("/")}"'
            print(f"Renaming temp folder back: {rename_command}")
            output, returncode = self.run_command(rename_command)
            if returncode != 0:
                print(f"❌ CRITICAL: Failed to rename temp folder back to '{folder_path}'. Manual cleanup may be required. Error: {output}")
                return False

            # 5. Empty the trash to reclaim space immediately.
            print("🗑️ Emptying trash bin...")
            trash_command = 'mega-emptytrash' # Corrected command
            trash_output, trash_returncode = self.run_command(trash_command)
            if trash_returncode != 0:
                print(f"⚠️ Warning: Failed to empty trash: {trash_output}")
            else:
                print("✅ Trash bin emptied successfully")

            print("✅ Deletion process completed successfully.")
            return True

        except Exception as e:
            print(f"❌ An exception occurred during the deletion process: {e}")
            return False

    def _parse_du_output(self, output, returncode):
        """
        Parses the output of mega-du to extract size in bytes.
        """
        if returncode != 0:
            return None
        
        # The output is in the format:
        # FILENAME                                                                 SIZE
        # Koabuddhaxxx - ✨Downloaded Fr...From Leakifyhub.com✨ - 3.mp4:  1320308265
        # -----------------------------------------------------------------------------
        # Total storage used:                                                1320308265
        lines = output.splitlines()
        for line in lines:
            if ":" in line:
                parts = line.split(":")
                if len(parts) == 2:
                    try:
                        return int(parts[1].strip())
                    except (ValueError, IndexError):
                        continue
        return None

    def get_folder_size(self, folder_path):
        """
        Get the current size of a folder in GB. More robust parsing.
        """
        try:
            command = f'mega-du "{folder_path.lstrip("/")}"'
            output, returncode = self.run_command(command)
            
            size_bytes = self._parse_du_output(output, returncode)
            
            if size_bytes is not None:
                return size_bytes / (1024 * 1024 * 1024)  # Convert to GB
            
            print(f"Failed to get folder size for {folder_path}: {output}")
            return 0
            
        except Exception as e:
            print(f"Error getting folder size for {folder_path}: {e}")
            return 0

    def is_picture_folder(self, folder_name):
        """
        Determines if a folder is likely a picture folder based on common naming patterns.
        """
        picture_keywords = ['pic', 'photo', 'image', 'img', 'picture', 'pictures', 'photos', 'images', 'gallery', 'gallery']
        folder_lower = folder_name.lower()
        return any(keyword in folder_lower for keyword in picture_keywords)

    def analyze_folder_structure(self, folder_path):
        """
        Analyzes the folder structure, including nested folders, using mega-du for file sizes.
        Treats picture folders as single files for optimization.
        """
        try:
            print(f"🔍 Analyzing folder structure for: {folder_path}")
            folder_path = folder_path.lstrip("/")
            
            file_command = f'mega-find "{folder_path}" --type=f'
            file_output, file_returncode = self.run_command(file_command)
            if file_returncode != 0:
                print(f"❌ Failed to list files: {file_output}")
                return None

            folders = {}
            root_files = []
            
            all_files = file_output.splitlines()
            print(f"Found {len(all_files)} total files in mega-find output.")

            # First pass: identify picture folders and their files
            picture_folders = set()
            for file_line in all_files:
                if not file_line.strip():
                    continue
                
                file_line = file_line.lstrip("/")
                parent_path = os.path.dirname(file_line)
                parent_folder_name = os.path.basename(parent_path)
                
                # Check if this file is in a picture folder
                if parent_path != folder_path and self.is_picture_folder(parent_folder_name):
                    picture_folders.add(parent_path)

            for file_line in all_files:
                if not file_line.strip():
                    continue
                
                file_line = file_line.lstrip("/")
                file_name = os.path.basename(file_line)
                parent_path = os.path.dirname(file_line)

                # Get file size using mega-du
                du_command = f'mega-du "{file_line}"'
                du_output, du_returncode = self.run_command(du_command)
                size_bytes = self._parse_du_output(du_output, du_returncode)
                file_size_gb = size_bytes / (1024*1024*1024) if size_bytes is not None else 0

                file_data = {'name': file_name, 'path': file_line, 'size': file_size_gb, 'parent_folder': os.path.basename(parent_path)}

                if parent_path == folder_path:
                    root_files.append(file_data)
                else:
                    # Check if this is a picture folder
                    if parent_path in picture_folders:
                        # Treat picture folders as single files - only add the folder once
                        if parent_path not in folders:
                            # Get total size of the picture folder
                            folder_du_command = f'mega-du "{parent_path}"'
                            folder_du_output, folder_du_returncode = self.run_command(folder_du_command)
                            folder_size_bytes = self._parse_du_output(folder_du_output, folder_du_returncode)
                            folder_size_gb = folder_size_bytes / (1024*1024*1024) if folder_size_bytes is not None else 0
                            
                            folders[parent_path] = {
                                'name': os.path.basename(parent_path), 
                                'path': parent_path, 
                                'size': folder_size_gb, 
                                'files': [],
                                'is_picture_folder': True
                            }
                            print(f"📸 Treating picture folder '{os.path.basename(parent_path)}' as single file ({folder_size_gb:.2f}GB)")
                        # Don't add individual files from picture folders
                    else:
                        # Regular folder processing
                        if parent_path not in folders:
                            folders[parent_path] = {'name': os.path.basename(parent_path), 'path': parent_path, 'size': 0, 'files': [], 'is_picture_folder': False}
                        folders[parent_path]['files'].append(file_data)
                        folders[parent_path]['size'] += file_size_gb
            
            structure = {
                'folders': list(folders.values()),
                'files': root_files
            }
            
            picture_folder_count = sum(1 for folder in structure['folders'] if folder.get('is_picture_folder', False))
            print(f"📊 Analysis complete: {len(structure['folders'])} folders ({picture_folder_count} picture folders), {len(structure['files'])} files")
            return structure

        except Exception as e:
            print(f"❌ Error analyzing folder structure: {e}")
            return None

    async def process_large_folder_with_chunking(self, mega_link, chunk_plan, account_index, call, folder_structure=None):
        """
        Process a large folder by importing the entire mega link and selectively deleting content.
        
        This method:
        1. For first account: Imports the entire mega link and processes it
        2. For subsequent accounts: Creates a folder with remaining files from previous accounts
        3. Analyzes the folder structure (if not provided)
        4. Selectively deletes content to stay under 19.9GB
        5. Optimizes for maximum content retention
        
        Args:
            mega_link (str): The MEGA folder URL to process
            chunk_plan (dict): The chunking plan for this folder
            account_index (int): Which chunk/account this is (0-based)
            call: Callback object for sending update messages
            folder_structure (dict, optional): Pre-analyzed folder structure. Defaults to None.
            
        Returns:
            tuple: (folder_name, success) if successful, or (False, False) if failed
        """
        await call.message.reply_text(f"🔄 Processing chunk {account_index + 1} of {chunk_plan['original_folder']}")
        
        # Step 1: Import the entire mega link
        folder_name = self.import_mega_link(mega_link)
        if not folder_name:
            await call.message.reply_text("❌ Failed to import mega link")
            return False, False
        
        folder_name = folder_name.replace("Imported folder complete: ", "").lstrip("/")
        await call.message.reply_text(f"✅ Imported folder: {folder_name}")
        
        # Step 2: Analyze folder structure (only if not already done)
        if folder_structure is None:
            await call.message.reply_text("🔍 Analyzing folder structure...")
            folder_structure = self.analyze_folder_structure(folder_name)
        
        if not folder_structure:
            await call.message.reply_text("❌ Failed to analyze folder structure")
            return False, False
        
        # Step 3: Calculate what to keep and what to delete
        keep_plan = self.calculate_keep_plan(folder_structure, chunk_plan, account_index)
        
        if not keep_plan:
            await call.message.reply_text("❌ Failed to calculate keep plan")
            return False, False
        
        # Debug: Show what the keep plan contains
        await call.message.reply_text(f"📊 Keep plan generated: {len(keep_plan['keep_folders'])} folders to keep, {len(keep_plan['delete_folders'])} folders to delete")
        await call.message.reply_text(f"📊 Files: {len(keep_plan['keep_files'])} to keep, {len(keep_plan['delete_files'])} to delete")
        
        # Step 4: Delete unwanted content
        await call.message.reply_text("🗑️ Deleting unwanted content...")
        
        # Add a small delay to ensure the deletion is processed
        import time
        time.sleep(2)
        
        deletion_result = self.delete_unwanted_content(folder_name, keep_plan)
        await call.message.reply_text(f"🗑️ Deletion result: {deletion_result}")
        
        if not deletion_result:
            await call.message.reply_text("❌ Failed to delete unwanted content")
            return False, False
        
        # Verify deletion by checking folder size again
        await call.message.reply_text("🔍 Verifying deletion...")
        time.sleep(3)  # Give MEGA time to process
        verification_size = self.get_folder_size(folder_name)
        await call.message.reply_text(f"📊 Size after deletion: {verification_size:.2f}GB")
        
        # Step 5: Verify final size
        final_size = self.get_folder_size(folder_name)
        if final_size > 19.9:
            await call.message.reply_text(f"❌ Final size {final_size:.1f}GB exceeds 19.9GB limit")
            return False, False
        
        await call.message.reply_text(f"✅ Chunk processed successfully. Final size: {final_size:.1f}GB")
        await call.message.reply_text(f"📊 Kept {len(keep_plan['keep_folders'])} folders and {len(keep_plan['keep_files'])} files")
        await call.message.reply_text(f"🗑️ Deleted {len(keep_plan['delete_folders'])} folders and {len(keep_plan['delete_files'])} files")
        
        # Return tuple format expected by the calling code
        return (folder_name, True, keep_plan)



    def force_delete_videos_for_testing(self, folder_path):
        """
        FORCE DELETE VIDEOS FOR TESTING - This will delete ALL video files in the folder!
        Use this to test if deletion is working at all.
        """
        try:
            print(f"🧪 FORCE DELETING ALL VIDEOS in {folder_path}")
            
            # Find all video files
            command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
            output, returncode = self.run_command(command)
            
            if returncode != 0:
                print(f"❌ Failed to list files: {output}")
                return False
            
            video_extensions = ['.mp4', '.mkv', '.avi', '.mov', '.m4v']
            deleted_count = 0
            
            for file_path in output.splitlines():
                if file_path.strip():
                    file_name = file_path.lower()
                    if any(ext in file_name for ext in video_extensions):
                        print(f"🧪 FORCE DELETING VIDEO: {file_path}")
                        delete_command = f'mega-rm "{file_path.lstrip("/")}"'
                        self.run_command(delete_command)
                        
                        if delete_returncode == 0:
                            print(f"✅ FORCE DELETED: {file_path}")
                            deleted_count += 1
                        else:
                            print(f"❌ FAILED TO DELETE: {file_path} - {delete_output}")
            
            # Empty trash
            print("🧪 Emptying trash...")
            trash_command = 'mega-emptytrash'
            self.run_command(trash_command)
            
            print(f"🧪 FORCE DELETION COMPLETE: Deleted {deleted_count} video files")
            return True
            
        except Exception as e:
            print(f"❌ FORCE DELETE ERROR: {e}")
            return False

    def debug_file_size_parsing(self, folder_path):
        """
        Debug method to understand the format of mega-du output.
        """
        try:
            print(f"🔍 DEBUGGING FILE SIZE PARSING for {folder_path}")
            
            # Get first few files
            command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
            output, returncode = self.run_command(command)
            
            if returncode != 0:
                print(f"❌ Failed to list files: {output}")
                return
            
            file_count = 0
            for file_path in output.splitlines():
                if file_path.strip() and file_count < 3:  # Only test first 3 files
                    file_name = file_path.split("/")[-1]
                    print(f"\n📄 Testing file: {file_name}")
                    print(f"   Full path: {file_path}")
                    
                    # Test mega-du command
                    du_command = f'mega-du "{file_path.lstrip("/")}"'
                    du_output, du_returncode = self.run_command(du_command)
                    
                    print(f"   mega-du return code: {du_returncode}")
                    print(f"   mega-du raw output: '{du_output}'")
                    
                    if du_returncode == 0:
                        # Try to parse the size
                        lines = du_output.splitlines()
                        for line in lines:
                            if file_path in line:
                                print(f"   Matching line: '{line}'")
                                parts = line.split()
                                print(f"   Split parts: {parts}")
                                
                                # Try to find the size
                                for i, part in enumerate(parts):
                                    if part.isdigit():
                                        size_bytes = int(part)
                                        size_gb = size_bytes / (1024 * 1024 * 1024)
                                        print(f"   Found size at position {i}: {size_bytes} bytes = {size_gb:.2f}GB")
                                        break
                                else:
                                    print(f"   No numeric size found in parts")
                                break
                        else:
                            print(f"   No matching line found")
                    
                    # Test if we can access the file directly
                    print(f"   Testing direct file access...")
                    test_command = f'mega-ls "{file_path.lstrip("/")}"'
                    test_output, test_returncode = self.run_command(test_command)
                    print(f"   Direct access return code: {test_returncode}")
                    print(f"   Direct access output: '{test_output}'")
                    
                    file_count += 1
            
        except Exception as e:
            print(f"❌ DEBUG ERROR: {e}")

    def debug_imported_folder_structure(self, folder_path):
        """
        Debug method to understand the actual imported folder structure.
        """
        try:
            print(f"🔍 DEBUGGING IMPORTED FOLDER STRUCTURE for {folder_path}")
            
            # List the imported folder contents
            command = f'mega-ls "{folder_path.lstrip("/")}"'
            output, returncode = self.run_command(command)
            
            print(f"   mega-ls return code: {returncode}")
            print(f"   mega-ls output: '{output}'")
            
            # List all folders in the imported folder
            folder_command = f'mega-find "{folder_path.lstrip("/")}" --type=d'
            folder_output, folder_returncode = self.run_command(folder_command)
            
            print(f"   mega-find folders return code: {folder_returncode}")
            print(f"   Folders found: '{folder_output}'")
            
            # List all files in the imported folder
            file_command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
            file_output, file_returncode = self.run_command(file_command)
            
            print(f"   mega-find files return code: {file_returncode}")
            print(f"   First few files found:")
            for i, file_path in enumerate(file_output.splitlines()[:5]):  # Show first 5 files
                print(f"     {i+1}. {file_path}")
            
        except Exception as e:
            print(f"❌ DEBUG IMPORTED FOLDER ERROR: {e}")

    def debug_actual_file_paths(self, folder_path):
        """
        Debug method to understand the actual file paths as they exist in MEGA.
        """
        try:
            print(f"🔍 DEBUGGING ACTUAL FILE PATHS for {folder_path}")
            
            # List all files in the imported folder
            file_command = f'mega-find "{folder_path.lstrip("/")}" --type=f'
            file_output, file_returncode = self.run_command(command)
            
            print(f"   mega-find files return code: {file_returncode}")
            print(f"   All files found:")
            for i, file_path in enumerate(file_output.splitlines()[:10]):  # Show first 10 files
                print(f"     {i+1}. '{file_path}'")
            
            # Test if we can access a specific file directly
            if file_output.splitlines():
                test_file = file_output.splitlines()[0]
                print(f"\n   Testing access to first file: '{test_file}'")
                
                # Try to get info about this file
                info_command = f'mega-ls "{test_file.lstrip("/")}"'
                info_output, info_returncode = self.run_command(info_command)
                print(f"   mega-ls return code: {info_returncode}")
                print(f"   mega-ls output: '{info_output}'")
                
                # Try to get size of this file
                du_command = f'mega-du "{test_file.lstrip("/")}"'
                du_output, du_returncode = self.run_command(du_command)
                print(f"   mega-du return code: {du_returncode}")
                print(f"   mega-du output: '{du_output}'")
            
        except Exception as e:
            print(f"❌ DEBUG ACTUAL FILE PATHS ERROR: {e}")
import os
import json
import asyncio
from bot_management.mega.mega import MEGA
from bot_management.leakutopia_links import newPaste
from bot_management.extractor import extract_folder_size
from bot_management.utils import split_large_folders_and_optimize_allocation
from bot_management.license_checker import license_checker

async def run_single_folder_watermarking(mega, mega_link, model_name, multiple_models, call, folder_size):
    """
    Executes the watermarking process for a single MEGA folder.
    
    Args:
        mega: An instance of the MEGA class.
        mega_link (str): The MEGA folder URL.
        model_name (str): The desired model name for renaming the folder.
        multiple_models (int): Flag for processing multiple models.
        call: The callback object used for sending update messages.
        
    Returns:
        str: The public link if the process is successful, or False if any step fails.
    """
    # Check license limits
    can_watermark, message = license_checker.check_watermark_limit()
    if not can_watermark:
        await call.message.reply(f"🚫 **LIMITED VERSION RESTRICTION**\n\n{message}\n\n💡 **Upgrade to Full Version:**\n- Unlimited daily watermarks\n- Advanced features\n- Priority support\n\nContact developer for licensing information.")
        return False
    
    print(multiple_models)
    if not mega.server_status:
        await call.message.reply("❌ MEGAcmdServer not running correctly.\n\nPlease (re)start it.")
        return False

    # Confirm server is running.
    await call.message.reply("✅ MEGAcmdServer running correctly.")

    # Logout if already logged in.
    login_status = mega.whoami()
    if login_status:
        if mega.logout():
            await call.message.reply("✅ Logged out from previous session successfully.")
        else:
            await call.message.reply("❌ Log-out failed.\n\nPlease check the console.")
            return False

    # Attempt to log in.
    if mega.login():
        await call.message.reply("✅ Login worked successfully.")
    else:
        await call.message.reply("❌ Login failed.\n\nPlease check your credentials.")
        return False

    # Import the folder.
    folder_name = mega.import_mega_link(mega_link)
    if not folder_name:
        await call.message.reply("❌ Import failed.\n\nPlease check your link.")
        return False
    folder_name = folder_name.replace("Imported folder complete: ", "")
    await call.message.reply("✅ Folder imported successfully.")

    # Rename the folder.
    renamed_folder = mega.rename_folder(folder_name, model_name)
    if not renamed_folder:
        await call.message.reply("❌ Renaming failed.\n\nPlease check your console.")
        return False
    await call.message.reply("✅ Folder renamed successfully.")

    # Fix trailing spaces in subfolders.
    if not mega.fix_trailing_spaces_in_subfolders(renamed_folder):
        await call.message.reply("❌ Fixing trailing spaces failed.\n\nPlease check your console.")
        return False
    await call.message.reply("✅ Trailing spaces fixed in subfolders.")

    # Delete unwanted files FIRST (more efficient).
    if not mega.delete_unwanted_files(renamed_folder):
        await call.message.reply("❌ Unwanted files removal failed.\n\nPlease check your console.")
        return False
    await call.message.reply("✅ Unwanted files have been deleted.")

    # Rename subfolders.
    if not mega.rename_subfolders(renamed_folder, multiple_models):
        await call.message.reply("❌ Rename of subfolders failed.\n\nPlease check your console.")
        return False
    await call.message.reply("✅ All subfolders were renamed.")

    # Rename files in subfolders LAST (after deleting unwanted files).
    files_rename_message = await call.message.reply("⚙️ Renaming all files...")
    if not mega.rename_files_in_subfolders(renamed_folder):
        await files_rename_message.edit_text("❌ Rename of all files failed.\n\nPlease check your console.")
        return False
    await files_rename_message.edit_text("✅ All files were renamed.")

    # Upload watermark files.
    if not folder_size or folder_size > 20:
        await call.message.reply("⚠️ Folder size exceeds 20GB; watermark files upload skipped.")
    else:
        upload_files_message = await call.message.reply("⚙️ Uploading watermark files...")
        if not mega.upload_files_to_subfolders(renamed_folder):
            await upload_files_message.edit_text("❌ Watermark files upload failed.\n\nPlease check your console.")
            return False
        await upload_files_message.edit_text("✅ Watermark files uploaded.")

    # Get the public link.
    public_link = mega.get_public_link(renamed_folder)
    await call.message.reply(f"✅ <b>Process Completed:</b> {public_link}")
    
    # Increment usage counter
    license_checker.increment_watermark()

    return public_link

async def run_bulk_watermarking(process_folder, call, folder_names, leak_mapping, non_mega_links, accounts, folder_sizes):
    """
    Processes mega folders with chunking for large folders and optimal account allocation.
    
    This function:
    1. Splits large folders (>20GB) into virtual chunks of 19.9GB or less
    2. Distributes all folders and chunks optimally across accounts
    3. Ensures no account exceeds 19.9GB of content
    4. Maintains existing optimization logic for smaller folders
    
    Args:
        process_folder (str): Folder where logs will be saved.
        call: Callback object for sending update messages.
        folder_names (dict): Mapping from each folder (mega link) to its corresponding name.
        leak_mapping (dict): Mapping from leakutopia URLs to extra data.
        non_mega_links (dict): Mapping for non-mega links.
        accounts (list[str]): List of account identifiers.
        folder_sizes (dict): Mapping {folder: initially allocated size in GB}.
    
    Returns:
        tuple: (watermarking_log, final_account_allocations, final_unallocated_folders)
    """
    # Check bulk processing limits
    can_process, message = license_checker.check_bulk_process_limit()
    if not can_process:
        await call.message.reply(f"🚫 **LIMITED VERSION RESTRICTION**\n\n{message}\n\n💡 **Upgrade to Full Version:**\n- Unlimited bulk processing\n- Advanced automation\n- Priority support\n\nContact developer for licensing information.")
        return {}, {}, {}
    
    # Check file count limits
    total_files = len(folder_names)
    can_process_files, file_message = license_checker.check_file_limit(total_files)
    if not can_process_files:
        await call.message.reply(f"🚫 **LIMITED VERSION RESTRICTION**\n\n{file_message}\n\n💡 **Upgrade to Full Version:**\n- Unlimited file processing\n- Advanced features\n- Priority support\n\nContact developer for licensing information.")
        return {}, {}, {}
    
    watermarking_log = {}

    # Process non-mega links as before.
    for link in non_mega_links.keys():
        extra = leak_mapping.get(link, {}).get("extra", {})
        # Compose new leakutopia.click content
        at_prefix = ""
        if link in leak_mapping and leak_mapping[link].get("original", "").strip().startswith("@"):
            at_prefix = "@"
        content = f"{at_prefix}{link}\n" if at_prefix else ""
        seen = set()
        if isinstance(extra, dict) and extra.get("all_urls"):
            for l in extra["all_urls"]:
                if "mega.nz/folder/" in l:
                    continue
                if l not in seen:
                    content += f"{l}\n"
                    seen.add(l)
        new_leak_link = newPaste(content.strip())
        watermarking_log[link] = {
            "account": "N/A",
            "size": None,
            "model_name": folder_names.get(link, "default_model"),
            "status": "success",
            "public_link": new_leak_link,
            "error": None
        }
        if link in leak_mapping:
            original_leak_link = leak_mapping[link].get("original", "")
            await call.message.reply_text(
                f"Rebuilt leakutopia link: {new_leak_link}\nSource: {original_leak_link}"
            )
        else:
            await call.message.reply_text(f"Rebuilt leakutopia link: {new_leak_link}")

    # Use the new chunking algorithm to split large folders and optimize allocation
    print(folder_sizes)
    account_allocations, unallocated_folders, chunked_folders = split_large_folders_and_optimize_allocation(
        accounts, folder_sizes, process_folder
    )

    # These will hold the final mapping.
    final_account_allocations = {account: [] for account in accounts}
    final_unallocated_folders = []

    # Process chunked folders and create the final allocation mapping
    for account, allocations in account_allocations.items():
        for allocation in allocations:
            # Handle the new 4-value allocation structure: (folder, size, chunk_plan, account_index)
            if len(allocation) == 4:
                folder, size, chunk_plan, account_index = allocation
            elif len(allocation) == 3:
                folder, size, chunk_plan = allocation
                account_index = None
            elif len(allocation) == 2:
                folder, size = allocation
                chunk_plan = None
                account_index = None
            else:
                continue  # Skip invalid allocations
            
            # Check if this is a chunk by looking for chunk_id pattern
            if folder.endswith("_chunk_") or "_chunk_" in folder:
                # This is a chunk, find the original folder from chunked_folders
                original_folder = None
                for orig_folder, chunk_plan_data in chunked_folders.items():
                    for chunk_data in chunk_plan_data['chunks']:
                        if chunk_data['chunk_id'] == folder:
                            original_folder = orig_folder
                            break
                    if original_folder:
                        break
                
                if original_folder:
                    # Store chunk info for later processing
                    final_account_allocations[account].append((folder, size, original_folder, chunk_plan, account_index))
                else:
                    final_account_allocations[account].append((folder, size))
            else:
                final_account_allocations[account].append((folder, size))
    
    final_unallocated_folders = unallocated_folders
    
    # Display chunking information
    if chunked_folders:
        chunk_info = "📦 Large folders split into chunks:\n"
        for original_folder, chunk_plan_data in chunked_folders.items():
            chunk_info += f"• {original_folder} ({folder_sizes[original_folder]:.1f}GB) → "
            chunk_info += ", ".join([f"{chunk_data['chunk_id']} ({chunk_data['size']:.1f}GB)" for chunk_data in chunk_plan_data['chunks']]) + "\n"
        await call.message.reply_text(chunk_info)
    
    # Create a mapping from chunks back to original folders for processing
    chunk_to_original = {}
    for original_folder, chunk_plan_data in chunked_folders.items():
        for chunk_data in chunk_plan_data['chunks']:
            chunk_to_original[chunk_data['chunk_id']] = original_folder

    # Track processed mega links for large leakutopia folders
    large_leakutopia_processed_links = {}  # {original_mega_link: [processed_links]}
    large_leakutopia_extra_data = {}       # {original_mega_link: extra_data}

    # Process all allocated folders (including chunks)
    for account, allocations in final_account_allocations.items():
        for allocation in allocations:
            is_chunk = False
            if len(allocation) == 5:  # This is a chunk with chunk_plan
                folder, size, original_folder, chunk_plan, account_index = allocation
                is_chunk = True
            elif len(allocation) == 2:
                folder, size = allocation
                original_folder = None
                chunk_plan = None
                account_index = None
            else:
                continue # Should not happen

            
            # For chunks, we need to process the original mega link but track it as a chunk
            if is_chunk:
                original_mega_link = original_folder
                await call.message.reply_text(
                    f"🔄 Processing chunk {account_index + 1} of {original_mega_link} ({size:.1f}GB) on account: {account}"
                )
                
                # Use the original mega link for processing
                processing_link = original_mega_link
                processing_size = size
            else:
                processing_link = folder
                processing_size = size
                account_index = None

            # Process the folder.
            if processing_link in leak_mapping:
                original_leak_link = leak_mapping[processing_link].get("original", "")
                await call.message.reply_text(
                        f"🔄 Starting watermarking for mega link: {processing_link} on account: {account}\nSource: {original_leak_link}"
                )
            else:
                await call.message.reply_text(
                        f"🔄 Starting watermarking for mega link: {processing_link} on account: {account}"
                )

            result = False # Initialize result to False
            try:
                flag = 1 if processing_link.startswith("$") else 0
                if flag:
                    original_folder_name = processing_link
                    processing_link = processing_link.lstrip("$")
                    # Update dictionaries:
                    if original_folder_name in folder_sizes:
                        folder_sizes[processing_link] = folder_sizes.pop(original_folder_name)
                    if original_folder_name in leak_mapping:
                        leak_mapping[processing_link] = leak_mapping.pop(original_folder_name)
                    if original_folder_name in watermarking_log:
                        watermarking_log[processing_link] = watermarking_log.pop(original_folder_name)
                    if original_folder_name in folder_names:
                        folder_names[processing_link] = folder_names.pop(original_folder_name)
                multiple_models = flag

                # Use original folder name for watermarking
                watermark_model_name = folder_names.get(processing_link, "default_model")

                # Create a unique key for the watermarking log
                log_key = f"{processing_link}_chunk_{account_index + 1}" if is_chunk else processing_link
                
                watermarking_log[log_key] = {
                    "account": account,
                    "size": processing_size,
                    "model_name": watermark_model_name,
                    "status": None,
                    "public_link": None,
                    "error": None,
                    "original_folder": original_folder if is_chunk else None,
                    "chunk_number": account_index + 1 if is_chunk else None,
                    "is_chunk": is_chunk
                }

                # Instantiate the MEGA client.
                mega = MEGA(account, "qwqwqw12")
                
                # Logout if already logged in before attempting to login
                login_status = mega.whoami()
                if login_status:
                    if not mega.logout():
                        raise Exception(f"Failed to logout from {account}")
                
                # Login to the account
                if not mega.login():
                    raise Exception(f"Failed to login to {account}")

                # Use the new physical chunking method for large folders
                if is_chunk:
                    await call.message.reply_text(f"🔧 Using physical chunking for large folder...")
                    await call.message.reply_text(f"📊 Chunk info: size={size:.1f}GB, account_index={account_index}")
                    
                    result_tuple = await mega.process_large_folder_with_chunking(
                        processing_link, chunk_plan, account_index, call
                    )
                    
                    if not result_tuple:
                        raise Exception("Chunking process failed")
                    
                    chunked_folder_name, success, keep_plan = result_tuple
                    
                    if not success:
                        raise Exception("Chunking process was not successful")
                    
                    if chunked_folder_name:
                        # Save processed content for next account after chunking is complete
                        mega.save_processed_content(chunk_plan, account_index, keep_plan['processed_for_next_chunk'])
                        # Now apply watermarking to the chunked folder
                        await call.message.reply_text(f"🔄 Applying watermarking to chunked folder: {chunked_folder_name}")
                        
                        # Rename the chunked folder with account index for large folders
                        if processing_size and processing_size > 20:
                            # For large folders, add account index to the name
                            indexed_name = f"{watermark_model_name} {account_index + 1}"
                            renamed_folder = mega.rename_folder(chunked_folder_name, indexed_name)
                        else:
                            renamed_folder = mega.rename_folder(chunked_folder_name, watermark_model_name)
                        if not renamed_folder:
                            raise Exception("Renaming chunked folder failed.")
                        
                        await call.message.reply_text("✅ Chunked folder renamed successfully.")
                        
                        # Fix trailing spaces in subfolders
                        if not mega.fix_trailing_spaces_in_subfolders(renamed_folder):
                            raise Exception("Fixing trailing spaces failed.")
                        await call.message.reply_text("✅ Trailing spaces fixed in subfolders.")
                            
                        # Delete unwanted files (spam/advertising files)
                        if not mega.delete_unwanted_files(renamed_folder):
                            raise Exception("Unwanted files removal failed.")
                        await call.message.reply_text("✅ Unwanted files have been deleted.")
                                
                        # Rename subfolders
                        if not mega.rename_subfolders(renamed_folder, multiple_models):
                            raise Exception("Rename of subfolders failed.")
                        await call.message.reply_text("✅ All subfolders were renamed.")
                                    
                        # Rename files in subfolders
                        files_rename_message = await call.message.reply("⚙️ Renaming all files...")
                        if not mega.rename_files_in_subfolders(renamed_folder):
                            try:
                                await files_rename_message.edit_text("❌ Rename of all files failed.")
                            except Exception as edit_error:
                                if "MESSAGE_NOT_MODIFIED" not in str(edit_error):
                                    print(f"Edit error: {edit_error}")
                            raise Exception("Rename of all files failed.")
                        
                        try:
                            await files_rename_message.edit_text("✅ All files were renamed.")
                        except Exception as edit_error:
                            if "MESSAGE_NOT_MODIFIED" not in str(edit_error):
                                print(f"Edit error: {edit_error}")
                            # If edit fails, send a new message
                            await call.message.reply_text("✅ All files were renamed.")
                                        
                        # Upload watermark files (skip for large folders)
                        if not processing_size or processing_size > 20:
                            await call.message.reply_text("⚠️ Folder size exceeds 20GB; watermark files upload skipped.")
                        else:
                            upload_files_message = await call.message.reply("⚙️ Uploading watermark files...")
                            if not mega.upload_files_to_subfolders(renamed_folder):
                                try:
                                    await upload_files_message.edit_text("❌ Watermark files upload failed.")
                                except Exception as edit_error:
                                    if "MESSAGE_NOT_MODIFIED" not in str(edit_error):
                                        print(f"Edit_error: {edit_error}")
                                raise Exception("Watermark files upload failed.")
                            
                            try:
                                await upload_files_message.edit_text("✅ Watermark files uploaded.")
                            except Exception as edit_error:
                                if "MESSAGE_NOT_MODIFIED" not in str(edit_error):
                                    print(f"Edit error: {edit_error}")
                                # If edit fails, send a new message
                                await call.message.reply_text("✅ Watermark files uploaded.")
                                        
                        # Get the public link
                        public_link = mega.get_public_link(renamed_folder)
                        await call.message.reply_text(f"✅ <b>Chunk Process Completed:</b> {public_link}")
                        result = public_link
                else:
                    result = await run_single_folder_watermarking(mega, processing_link, watermark_model_name, multiple_models, call, processing_size)
            
                if result:
                    # Check if this is a leakutopia link and if it's a large folder
                    is_large_leakutopia = (processing_link in leak_mapping and 
                                         processing_link in folder_sizes and 
                                         folder_sizes[processing_link] and 
                                         folder_sizes[processing_link] > 20)
                    
                    if is_large_leakutopia:
                        # For large leakutopia folders, collect the processed link but don't create the leakutopia link yet
                        if processing_link not in large_leakutopia_processed_links:
                            large_leakutopia_processed_links[processing_link] = []
                            large_leakutopia_extra_data[processing_link] = leak_mapping[processing_link].get("extra", {})
                        large_leakutopia_processed_links[processing_link].append(result)
                        
                        # Store the result in the watermarking log but mark it as pending leakutopia creation
                        watermarking_log[log_key]["public_link"] = result
                        watermarking_log[log_key]["pending_leakutopia"] = True
                        
                        await call.message.reply_text(f"📦 Collected processed link for large leakutopia folder: {result}")
                    else:
                        # For regular folders or small leakutopia folders, rebuild leakutopia link as before
                        if processing_link in leak_mapping:
                            extra = leak_mapping[processing_link].get("extra", {})
                            # Compose new leakutopia.click content
                            at_prefix = ""
                            if "original" in leak_mapping[processing_link] and leak_mapping[processing_link]["original"].strip().startswith("@"):
                                at_prefix = "@"
                            content = f"{at_prefix}{result}\n"
                            # Only include non-mega links, and deduplicate
                            if extra and isinstance(extra, dict) and "all_urls" in extra:
                                seen = set()
                                for link in extra["all_urls"]:
                                    if "mega.nz/folder/" in link:
                                        continue  # skip old MEGA links
                                    if link not in seen:
                                        content += f"{link}\n"
                                        seen.add(link)
                            new_leak_link = newPaste(content.strip())
                            watermarking_log[log_key]["public_link"] = new_leak_link
                            if processing_link in leak_mapping:
                                original_leak_link = leak_mapping[processing_link].get("original", "")
                                await call.message.reply_text(
                                    f"Rebuilt leakutopia link: {new_leak_link}\nSource: {original_leak_link}"
                                )
                            else:
                                await call.message.reply_text(f"Rebuilt leakutopia link: {new_leak_link}")
                        else:
                            watermarking_log[log_key]["public_link"] = result

                    final_size = extract_folder_size(result)  # Final size in GB or False if error.
                    if final_size is not False:
                        watermarking_log[log_key]["size"] = final_size
                        watermarking_log[log_key]["status"] = "success"
                    else:
                        watermarking_log[log_key]["status"] = "failed"
                        watermarking_log[log_key]["error"] = "Could not retrieve final folder size"
                else:
                    watermarking_log[log_key]["status"] = "failed"
                    watermarking_log[log_key]["error"] = "Process returned False"
            except Exception as e:
                watermarking_log[log_key]["status"] = "failed"
                watermarking_log[log_key]["error"] = str(e)
                await call.message.reply_text(f"❌ Watermarking error for folder {processing_link}: {e}")
            finally:
                mega.logout()

    # Now create leakutopia links for large folders that were chunked
    for original_mega_link, processed_links in large_leakutopia_processed_links.items():
        if original_mega_link in leak_mapping:
            extra = large_leakutopia_extra_data[original_mega_link]
            # Compose new leakutopia.click content with all processed mega links
            at_prefix = ""
            if "original" in leak_mapping[original_mega_link] and leak_mapping[original_mega_link]["original"].strip().startswith("@"):
                at_prefix = "@"
            
            # Start with the @ prefix if needed
            content = f"{at_prefix}" if at_prefix else ""
            
            # Add all processed mega links
            for processed_link in processed_links:
                content += f"{processed_link}\n"
            
            # Add non-mega links from the original content
            if extra and isinstance(extra, dict) and "all_urls" in extra:
                seen = set()
                for link in extra["all_urls"]:
                    if "mega.nz/folder/" in link:
                        continue  # skip old MEGA links
                    if link not in seen:
                        content += f"{link}\n"
                        seen.add(link)
            
            new_leak_link = newPaste(content.strip())
            
            # Update all chunk entries in the watermarking log
            for log_key, log_entry in watermarking_log.items():
                if (log_entry.get("original_folder") == original_mega_link and 
                    log_entry.get("is_chunk") and 
                    log_entry.get("pending_leakutopia")):
                    log_entry["public_link"] = new_leak_link
                    log_entry.pop("pending_leakutopia", None)
            
            original_leak_link = leak_mapping[original_mega_link].get("original", "")
            await call.message.reply_text(
                f"✅ Rebuilt large leakutopia link with {len(processed_links)} chunks: {new_leak_link}\nSource: {original_leak_link}"
            )

    # Write the watermarking log to file.
    log_file_path = os.path.join(process_folder, "watermarking_log.json")
    with open(log_file_path, "w", encoding="utf-8") as f:
        json.dump(watermarking_log, f, indent=4)

    # Build the final allocation mapping.
    allocation_mapping = {
        "account_allocations": final_account_allocations,
        "unallocated_folders": final_unallocated_folders,
        "chunked_folders": chunked_folders
    }
    mapping_file_path = os.path.join(process_folder, "allocation_mapping.json")
    with open(mapping_file_path, "w", encoding="utf-8") as f:
        json.dump(allocation_mapping, f, indent=4)

    await call.message.reply_text("✅ Watermarking process completed. Logs saved.")
    
    # Increment usage counters
    license_checker.increment_bulk_process()
    license_checker.increment_files(total_files)

    return watermarking_log, final_account_allocations, final_unallocated_folders

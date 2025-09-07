"""
Module: bulk_process.py
This module orchestrates the bulk watermarking process.
"""

import asyncio
import os
from bot_management.utils import create_process_folder, optimize_account_allocation, copy_bulk_files_to_process, create_folder_names_mapping
from bot_management.extractor import extract_folder_sizes
from bot_management.watermark import run_bulk_watermarking
from bot_management.leakutopia_links import process_leakutopia_links

async def run_bulk_process(emails, mega_links, names, call):
    """
    Orchestrates the entire bulk process.

    This function creates a process folder, extracts folder sizes from each MEGA link,
    computes account allocations (mapping folders to accounts) using the provided emails,
    and sends update messages for each step.

    Args:
        emails (list[str]): List of email addresses (accounts).
        mega_links (list[str]): List of MEGA folder URLs.
        names (list[str]): List of names.
        call: The callback object used for sending update messages.

    Returns:
        tuple: (account_allocations, unallocated_folders, folder_sizes)
    """
    # Clear the debug log at the beginning of the process
    log_file_path = os.path.join(os.path.dirname(__file__), 'logs', 'mega_debug.log')
    if os.path.exists(log_file_path):
        os.remove(log_file_path)

    # Create a new process folder
    process_folder = create_process_folder()
    copy_bulk_files_to_process(process_folder)
    await call.message.reply_text(f"✅ Process folder created: {process_folder}")

    # Process leakutopia links in the mega_links list.
    mega_links, leakutopia_mapping = process_leakutopia_links(mega_links, process_folder)
    await call.message.reply_text("✅ Leakutopia links processed. Mega links updated.")

    # Extract folder sizes using the extractor wrapper.
    folder_sizes, non_mega_links = extract_folder_sizes(mega_links, process_folder)
    await call.message.reply_text("✅ Folder sizes extracted and saved successfully.")

    # Compute the account allocation mapping and save it.
    #account_allocations, unallocated_folders = optimize_account_allocation(emails, folder_sizes, process_folder)
    #await call.message.reply_text("✅ Account allocations computed and mapping saved successfully.")

    # Create folder names mapping from the processed mega links and names.
    folder_names_mapping = create_folder_names_mapping(mega_links, names)
    await call.message.reply_text("✅ Folder names mapping created successfully.")

    # Run the bulk watermarking process using the mapping.
    watermarking_log, account_allocations, unallocated_folders = await run_bulk_watermarking(
        process_folder, call, folder_names_mapping, leakutopia_mapping,
        non_mega_links, emails, folder_sizes
    )
    
    await call.message.reply_text("✅ Bulk watermarking process completed.")

    return account_allocations, unallocated_folders, folder_sizes, watermarking_log, process_folder
from bot_management import app, LOGS
from bot_management.markup.InlineMarkup import InlineMarkup
from bot_management.utils import *
from bot_management.bulk_process import run_bulk_process
from bot_management.mega.mega import MEGA
from bot_management.account_creation import create_accounts
from pyrogram import Client, filters
from pyrogram.types import CallbackQuery
import asyncio 
import hashlib
import json
import os
import zipfile

@app.on_callback_query()
async def on_callback_query(client: Client, call: CallbackQuery):
    
    try:
        delete = await app.listen.Cancel(str(call.message.chat.id))
    except Exception as e:
        pass

    if call.data == 'home':
        email, password = extract_email_password('credentials.txt')

        start_message = (
    f"""‣ <i><b>Email:</b> {email if email else 'Not set'}</i>
‣ <i><b>Password:</b> {password if password else 'Not set'}</i>

After you set your credentials, send a MEGA link 🔗"""
    )

        await call.message.edit_text(start_message, reply_markup=InlineMarkup.start_markup())

    elif call.data == 'set_email':

        email, password = extract_email_password('credentials.txt')

        await call.message.edit_text(
            text=f"<i><b>Current Email:</b> {email if email else 'Not set'}</i>\n\nSend the new email (10 Minutes Timeout) ⏬", 
            reply_markup=InlineMarkup.set_credentials_markup()
        )

        try:
            answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)

            if answer is None:
                return

            if answer.text:

                new_email = answer.text
                update_email_password('credentials.txt', new_email=new_email)

                update_message = (f"<i><b>New Email:</b> {new_email}</i>\n\n"
                                  "Press <i>Continue</i> to go to the menu.")

                await call.message.edit_text(update_message, reply_markup=InlineMarkup.updated_credentials_markup())

                await answer.delete()

        except asyncio.TimeoutError:
            await call.answer("⌛ Time is finished")

    elif call.data == 'set_password':

        email, password = extract_email_password('credentials.txt')

        await call.message.edit_text(
            text=f"<i><b>Current Password:</b> {password if password else 'Not set'}</i>\n\nSend the new password (10 Minutes Timeout) ⏬", 
            reply_markup=InlineMarkup.set_credentials_markup()
        )

        try:
            answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)

            if answer is None:
                return

            if answer.text:

                new_password = answer.text
                update_email_password('credentials.txt', new_password=new_password)

                update_message = (f"<i><b>New Password:</b> {new_password}</i>\n\n"
                                  "Press <i>Continue</i> to go to the menu.")

                await call.message.edit_text(update_message, reply_markup=InlineMarkup.updated_credentials_markup())

                await answer.delete()

        except asyncio.TimeoutError:
            await call.answer("⌛ Time is finished")

    elif call.data == 'cancel':

        await call.message.edit_text("Process cancelled ❌", reply_markup=InlineMarkup.set_credentials_markup())

    elif call.data == 'rename_back':

        with open('folder_map.json', 'w') as f:
            json.dump({}, f)

        try:
            delete = await app.listen.Cancel(str(message.chat.id))
        except Exception as e:
            pass

        email, password = extract_email_password('credentials.txt')

        mega = MEGA(email, password)

        if mega.server_status:

            notification_message = await call.message.reply("✅ MEGAcmdServer running correctly.")

            login_status = mega.whoami()
            if login_status:
                if mega.logout():
                    await notification_message.edit_text("✅ Logged out from previous session succesfully.")
                else:
                    await notification_message.edit_text("❌ Log-out failed.\n\nPlease check the console.")
                    return

            if mega.login():
                await notification_message.edit_text("✅ Login worked succesfully.")

                folders = mega.list_main_folders()
                await notification_message.edit_text("✅ Folders retrieved.")

        else:
            await call.message.reply("❌ MEGAcmdServer not running correctly.\n\nPlease (re)start it.")

        rename_message = (

    f"""‣ <i><b>Email:</b> {email if email else 'Not set'}</i>
    ‣ <i><b>Password:</b> {password if password else 'Not set'}</i>

    Please select a folder 🗂"""

        )

        await call.message.reply(rename_message, reply_markup=InlineMarkup.folder_buttons_markup(folders))

    elif call.data == 'bulk_upload':

        # Prompt the user to upload a text file with emails (one per line)
        prompt_message = (
            "Please upload a text file containing a list of emails (one per line) within 10 minutes."
        )
        await call.message.edit_text(prompt_message, reply_markup=InlineMarkup.set_credentials_markup())

        try:
            # Wait for a file upload from the user
            answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)
            if not answer.document:
                await call.message.reply_text("No document received. Please try again.", reply_markup=InlineMarkup.set_credentials_markup())
                return

            file_name = answer.document.file_name
            if not file_name.endswith('.txt'):
                await call.message.reply_text("Invalid file type. Please upload a .txt file.")
                return

            # Create bulk_process folder if it doesn't exist
            bulk_folder = "bulk_process"
            if not os.path.exists(bulk_folder):
                os.makedirs(bulk_folder)

            # Download the file into bulk_process/emails.txt
            target_file_path = os.path.join(bulk_folder, "emails.txt")
            file_path = await answer.download(file_name=target_file_path)

            # Read the file and extract emails with validation
            with open(file_path, 'r', encoding='utf-8') as file:
                raw_emails = [line.strip() for line in file if line.strip()]

            valid_emails = []
            invalid_emails = []

            for email in raw_emails:
                if is_valid_email(email):
                    valid_emails.append(email)
                else:
                    invalid_emails.append(email)

            # Alert the user if any invalid emails were found
            if invalid_emails:
                alert_message = f"❌ {len(invalid_emails)} invalid email(s) found and skipped."
                await call.message.reply_text(alert_message)
                return

            # Build the top message with only valid emails
            top_message = f"Successfully processed {len(valid_emails)} valid emails:\n\n"

            # Format each email as a code block
            formatted_emails = "\n".join(f"<code>{email}</code>" for email in valid_emails)

            # Combine both parts
            final_message = top_message + formatted_emails

            # Telegram's maximum message length is 4096 characters
            max_length = 4096
            if len(final_message) > max_length:
                final_message = final_message[:max_length - 30] + "\n<code>...truncated...</code>"

            await call.message.reply_text(final_message)

            # Prompt the user to upload a text file with MEGA links (one per line)
            mega_prompt = "Now, please upload a text file containing a list of MEGA links (one per line) within 10 minutes."
            await call.message.reply_text(mega_prompt, reply_markup=InlineMarkup.set_credentials_markup())

            try:
                mega_answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)
                if not mega_answer.document:
                    await call.message.reply_text("No document received for MEGA links. Please try again.", reply_markup=InlineMarkup.set_credentials_markup())
                    return

                mega_file_name = mega_answer.document.file_name
                if not mega_file_name.endswith('.txt'):
                    await call.message.reply_text("Invalid file type. Please upload a .txt file for MEGA links.")
                    return

                # Ensure the bulk_process folder exists
                bulk_folder = "bulk_process"
                if not os.path.exists(bulk_folder):
                    os.makedirs(bulk_folder)

                # Download the MEGA links file into bulk_process as megas.txt
                target_mega_path = os.path.join(bulk_folder, "megas.txt")
                mega_file_path = await mega_answer.download(file_name=target_mega_path)

                # Process the file to extract MEGA links with validation and URL trimming
                with open(mega_file_path, 'r', encoding='utf-8') as file:
                    raw_links = [line.strip() for line in file if line.strip()]

                valid_mega_links = []
                invalid_links = []

                for link in raw_links:
                    if "mega.nz" in link:
                        trimmed_link = trim_mega_url(link)
                    else:
                        trimmed_link = link

                    if trimmed_link.startswith("https://mega.nz/folder/") or trimmed_link.startswith("$https://mega.nz/folder/") or trimmed_link.startswith("https://leakutopia.click/") or trimmed_link.startswith("$https://leakutopia.click/"):
                        valid_mega_links.append(trimmed_link)
                    else:
                        invalid_links.append(link)

                if invalid_links:
                    alert_message = f"❌ {len(invalid_links)} invalid MEGA link(s) were found."
                    await call.message.reply_text(alert_message)
                    return

                mega_links = valid_mega_links

                # Build a top message for MEGA links
                top_message_links = f"Successfully processed {len(mega_links)} MEGA links:\n\n"

                # Format each link as an ordered list item
                formatted_links = "\n".join(f"{i+1}. <code>{link}</code>" for i, link in enumerate(mega_links))

                # Combine both parts
                final_message_links = top_message_links + formatted_links

                # Trim the message if it exceeds Telegram's limit
                max_length = 4096
                if len(final_message_links) > max_length:
                    final_message_links = final_message_links[:max_length - 30] + "\n<code>...truncated...</code>"

                await call.message.reply_text(final_message_links)

                # Prompt the user to upload a text file with names (one per line)
                names_prompt = "Now, please upload a text file containing a list of names (one per line) within 10 minutes."
                await call.message.reply_text(names_prompt, reply_markup=InlineMarkup.set_credentials_markup())

                try:
                    names_answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)
                    if not names_answer.document:
                        await call.message.reply_text("No document received for names. Please try again.", reply_markup=InlineMarkup.set_credentials_markup())
                        return

                    names_file_name = names_answer.document.file_name
                    if not names_file_name.endswith('.txt'):
                        await call.message.reply_text("Invalid file type. Please upload a .txt file for names.")
                        return

                    # Ensure the bulk_process folder exists
                    bulk_folder = "bulk_process"
                    if not os.path.exists(bulk_folder):
                        os.makedirs(bulk_folder)

                    # Download the names file into bulk_process as names.txt
                    target_names_path = os.path.join(bulk_folder, "names.txt")
                    names_file_path = await names_answer.download(file_name=target_names_path)

                    # Process the file to extract names
                    with open(names_file_path, 'r', encoding='utf-8') as file:
                        names_list = [line.strip() for line in file if line.strip()]

                    if len(names_list) != len(mega_links):
                        alert_message = (
                            f"❌ The number of names ({len(names_list)}) does not match "
                            f"the number of MEGA links ({len(mega_links)}). Please review your files."
                        )
                        await call.message.reply_text(alert_message)
                        return

                    # Build a confirmation message
                    top_message_names = f"Successfully processed {len(names_list)} names:\n\n"
                    formatted_names = "\n".join(f"{i+1}. <code>{name}</code>" for i, name in enumerate(names_list))
                    final_message_names = top_message_names + formatted_names

                    max_length = 4096
                    if len(final_message_names) > max_length:
                        final_message_names = final_message_names[:max_length - 30] + "\n<code>...truncated...</code>"

                    await call.message.reply_text(final_message_names)

                    # At the end of the names file processing block, send the final confirmation message:
                    final_confirmation_message = (
                        "All files have been processed and stored in the bulk_process folder.\n\n"
                        "Do you want to start the bulk watermarking process now?"
                    )
                    await call.message.reply_text(final_confirmation_message, reply_markup=InlineMarkup.confirm_bulk_watermarking_markup())

                except asyncio.TimeoutError:
                    await call.answer("⌛ Time is finished")

            except asyncio.TimeoutError:
                await call.answer("⌛ Time is finished")

        except asyncio.TimeoutError:
            await call.answer("⌛ Time is finished")

    elif call.data == 'start_bulk':
        try:
            bulk_folder = "bulk_process"
            emails_file = os.path.join(bulk_folder, "emails.txt")
            megas_file = os.path.join(bulk_folder, "megas.txt")
            names_file = os.path.join(bulk_folder, "names.txt")

            # Verify that all required files exist.
            if not (os.path.exists(emails_file) and os.path.exists(megas_file) and os.path.exists(names_file)):
                await call.message.reply_text(
                    "Required bulk files are missing. Please upload emails, MEGA links, and names first.",
                    reply_markup=InlineMarkup.set_credentials_markup()
                )
                return

            # Read the files.
            with open(emails_file, "r", encoding="utf-8") as f:
                emails = [line.strip() for line in f if line.strip()]
            with open(megas_file, "r", encoding="utf-8") as f:
                mega_links = [line.strip() for line in f if line.strip()]
            with open(names_file, "r", encoding="utf-8") as f:
                names = [line.strip() for line in f if line.strip()]

            await call.message.reply_text(
                f"Bulk process starting:\nEmails: {len(emails)}\nMEGA links: {len(mega_links)}\nNames: {len(names)}"
            )

            # After run_bulk_process returns the watermarking_log
            account_allocations, unallocated_folders, folder_sizes, watermarking_log, process_folder = await run_bulk_process(emails, mega_links, names, call)

            success_output = ""
            fail_output = ""
            
            successful_folders = {}

            for folder, log in watermarking_log.items():

                name = log.get("model_name", "default_model")
                link = log.get("public_link") if log.get("public_link") else folder

                if log.get("status") == "failed":
                    error_msg = log.get("error", "Unknown error")
                    fail_output += f"{name}\n{link}\n<i>({error_msg})</i>\n\n"
                else:
                    if name not in successful_folders:
                        successful_folders[name] = []
                    # Only add the link if it's not already in the list (deduplicate leakutopia links)
                    if link not in successful_folders[name]:
                        successful_folders[name].append(link)

            for name, links in successful_folders.items():
                success_output += f"{name}\n"
                for link in links:
                    success_output += f"{link}\n"
                success_output += "\n"

            # After the existing loop for watermarking_log, add this loop to append unallocated folders to the failed output.
            for folder, size in unallocated_folders:
                fail_output += f"{folder}\n<i>(Unallocated due to insufficient capacity)</i>\n\n"

            # Trim each message if needed
            def chunk_text(text, chunk_size=3000):
                """Yield successive chunk_size pieces from text."""
                for i in range(0, len(text), chunk_size):
                    yield text[i:i+chunk_size]

            async def send_long_message(message_text, header=""):
                """Send a long message in 3000-character chunks, prepending a header to the first chunk."""
                full_text = header + message_text
                chunks = list(chunk_text(full_text, 3000))
                # Send the first chunk (with header)
                await call.message.reply_text(chunks[0])
                # Send any additional chunks without header
                for chunk in chunks[1:]:
                    await call.message.reply_text(chunk)

            # Use the helper for successful output:
            if success_output:
                await send_long_message(success_output, header="✅ Successful folders:\n\n")

            # Use the helper for failed output:
            if fail_output:
                await send_long_message(fail_output, header="❌ Failed folders:\n\n")

            unused_accounts = []
            low_usage_accounts = []

            for account, allocations in account_allocations.items():
                total_used = sum((size if size is not None else 0) for (_, size) in allocations)
                if total_used == 0:
                    unused_accounts.append(account)
                elif total_used < 10:
                    low_usage_accounts.append((account, total_used))

            msg_parts = []
            if unused_accounts:
                msg_parts.append("Unused accounts:\n" + "\n".join(unused_accounts))
            if low_usage_accounts:
                msg_parts.append("Low usage accounts (<10GB):\n" +
                                "\n".join(f"{acct} ({used:.2f} GB)" for acct, used in low_usage_accounts))

            # For account usage summary:
            if msg_parts:
                summary_text = "\n\n".join(msg_parts)
                await send_long_message(summary_text, header="📭 Account Usage Summary:\n\n")

            # Create a ZIP archive of the process folder
            zip_path = process_folder + ".zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(process_folder):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Store the file with a relative path to the process folder
                        arcname = os.path.relpath(file_path, start=process_folder)
                        zipf.write(file_path, arcname)

            await call.message.reply_document(document=zip_path, caption="📦 Here is the zipped process folder.")

        except Exception as e:
            await call.message.reply_text(f"An error occurred during bulk processing: {e}")

    elif call.data.startswith('folder_'):

        with open('folder_map.json', 'r') as f:
            folder_map = json.load(f)

        with open('folder_map.json', 'w') as f:
            json.dump({}, f)

        old_name_hash = call.data.split('folder_')[1]
        old_name = folder_map.get(old_name_hash, "Unknown Folder")

        new_name_message = (

f"""‣ <i><b>Folder name:</b> {old_name}</i>

Send the new folder name (10 Minutes Timeout) ⏬"""

    )

        await call.message.edit_text(
            text=new_name_message, 
            reply_markup=InlineMarkup.set_new_folder_markup()
        )

        try:
            answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)

            if answer is None:
                return

            if answer.text:

                new_folder_name = answer.text
                new_name_hash = hashlib.md5(new_folder_name.encode('utf-8')).hexdigest()[:10]

                update_message = (

f"""‣ <i><b>Folder name:</b> {old_name}</i>
‣ <i><b>New folder name:</b> {new_folder_name}</i>

Press <i>☑️ Confirm</i> to continue"""

    )

                folder_map = {}
                folder_map[old_name_hash] = old_name
                folder_map[new_name_hash] = new_folder_name

                multiple_models = 0 
                skip_upload = 0

                with open('folder_map.json', 'w') as f:
                    json.dump(folder_map, f)

                await call.message.edit_text(update_message, reply_markup=InlineMarkup.confirm_rename_markup(old_name_hash, new_name_hash, multiple_models, skip_upload))

                await answer.delete()

        except asyncio.TimeoutError:
            await call.answer("⌛ Time is finished")

    elif call.data.startswith("mm|") or call.data.startswith("su|"):
        # Handle toggle for Multiple Models or Skip Upload for leakutopia.click (cache_key) flows
        action, cache_key = call.data.split("|")
        from bot_management.plugins.messages import leakutopia_extra_cache
        cache_data = leakutopia_extra_cache.get(cache_key)
        if not cache_data:
            await call.message.reply("❌ Session expired or invalid. Please try again.")
            return
        # Toggle the value
        if action == "mm":
            cache_data['multiple_models'] = 0 if cache_data['multiple_models'] else 1
        elif action == "su":
            cache_data['skip_upload'] = 0 if cache_data['skip_upload'] else 1
        # Re-render the message with updated buttons
        mega_link = cache_data['mega_link']
        model_name = cache_data['model_name']
        multiple_models = cache_data['multiple_models']
        skip_upload = cache_data['skip_upload']
        await call.message.edit_text(
            f"<i><b>MEGA Link:</b> {mega_link}</i>\n<i><b>Model Name:</b> {model_name}</i>\n\nPress <i>☑️ Confirm</i> to continue",
            reply_markup=InlineMarkup.confirm_process_markup(cache_key=cache_key, multiple_models=multiple_models, skip_upload=skip_upload),
            disable_web_page_preview=True
        )
        return

    elif call.data.startswith("rnmm|"):

        multiple_models = 0 if int(call.data.split("|")[-3]) else 1
        old_name_hash = call.data.split("|")[-2]
        new_name_hash = call.data.split("|")[-1]

        with open('folder_map.json', 'r') as f:
            folder_map = json.load(f)

        old_name = folder_map.get(old_name_hash, "Unknown Folder")
        new_name = folder_map.get(new_name_hash, "Unknown Folder")

        rename_message = (

f"""‣ <i><b>Folder name:</b> {old_name}</i>
‣ <i><b>New folder name:</b> {new_name}</i>

Press <i>☑️ Confirm</i> to continue"""

    )

        await call.message.edit_text(rename_message, reply_markup=InlineMarkup.confirm_rename_markup(old_name_hash, new_name_hash, multiple_models), disable_web_page_preview=True)

    elif call.data.startswith("c|"):
        parts = call.data.split("|")
        # If only 2 parts, this is the leakutopia.click flow with cache_key
        if len(parts) == 2:
            cache_key = parts[1]
            try:
                from bot_management.plugins.messages import leakutopia_extra_cache
                cache_data = leakutopia_extra_cache.pop(cache_key, None)
            except ImportError:
                cache_data = None
            if not cache_data:
                await call.message.reply("❌ Session expired or invalid. Please try again.")
                return
            mega_link = cache_data['mega_link']
            model_name = cache_data['model_name']
            multiple_models = cache_data['multiple_models']
            skip_upload = cache_data['skip_upload']
            extra = cache_data['extra']
            
            # Check if this is a multi-account processing request
            if cache_data.get('is_multi_account', False):
                accounts = cache_data['accounts']
                folder_size = cache_data['folder_size']
                
                # Process with multi-account chunking
                await call.message.reply("🚀 Starting multi-account processing...")
                
                # Create a process folder for this single upload
                process_folder = create_process_folder()
                
                # Create folder sizes mapping
                folder_sizes = {mega_link: folder_size}
                
                # Create folder names mapping
                folder_names = {mega_link: model_name}
                
                # Create empty leak mapping and non-mega links
                leak_mapping = {}
                non_mega_links = {}
                
                # Use the chunking algorithm for allocation
                from bot_management.utils import split_large_folders_and_optimize_allocation
                account_allocations, unallocated_folders, chunked_folders = split_large_folders_and_optimize_allocation(
                    accounts, folder_sizes, process_folder
                )
                
                # Run bulk watermarking with the allocated accounts
                from bot_management.watermark import run_bulk_watermarking
                watermarking_log, final_account_allocations, final_unallocated_folders = await run_bulk_watermarking(
                    process_folder, call, folder_names, leak_mapping, non_mega_links, accounts, folder_sizes
                )
                
                # Process results and create leakutopia.click output for chunked folders
                success_output = ""
                fail_output = ""
                successful_folders = {}

                for folder, log in watermarking_log.items():
                    name = log.get("model_name", "default_model")
                    link = log.get("public_link") if log.get("public_link") else folder

                    if log.get("status") == "failed":
                        error_msg = log.get("error", "Unknown error")
                        fail_output += f"{name}\n{link}\n<i>({error_msg})</i>\n\n"
                    else:
                        if name not in successful_folders:
                            successful_folders[name] = []
                        if link not in successful_folders[name]:
                            successful_folders[name].append(link)

                # Create leakutopia.click output for chunked folders
                from bot_management.leakutopia_links import newPaste
                
                # Get all successful mega links for this model
                successful_mega_links = []
                for name, links in successful_folders.items():
                    if name == model_name:
                        successful_mega_links.extend(links)
                
                if successful_mega_links:
                    # Compose new leakutopia.click content with all processed mega links
                    at_prefix = ""
                    if mega_link.strip().startswith("@"):
                        at_prefix = "@"
                    
                    content = f"{at_prefix}" if at_prefix else ""
                    
                    # Add all successful mega links
                    for link in successful_mega_links:
                        content += f"{link}\n"
                    
                    # Add non-mega links from the original content (if it was a leakutopia.click link)
                    if extra and isinstance(extra, dict) and "all_urls" in extra:
                        seen = set()
                        for link in extra["all_urls"]:
                            if "mega.nz/folder/" in link:
                                continue  # skip old MEGA links
                            if link not in seen:
                                content += f"{link}\n"
                                seen.add(link)
                    
                    new_leak_link = newPaste(content.strip())
                    await call.message.reply(f"✅ <b>New LeakUtopia.click link with {len(successful_mega_links)} chunks:</b> {new_leak_link}")
                
                # Send results
                if success_output:
                    await call.message.reply_text(f"✅ <b>Successful processing:</b>\n\n{success_output}")
                if fail_output:
                    await call.message.reply_text(f"❌ <b>Failed processing:</b>\n\n{fail_output}")
                
                # Clean up processed content files
                from bot_management.utils import cleanup_processed_content_files
                deleted_count = cleanup_processed_content_files()
                if deleted_count > 0:
                    await call.message.reply_text(f"🧹 Cleaned up {deleted_count} processed content file(s)")
                
                return
            
            email, password = extract_email_password('credentials.txt')
        else:
            # Old format: c|multiple_models|skip_upload|mega_link_id|model_name
            email, password = extract_email_password('credentials.txt')
            data = parts
            multiple_models = int(data[1])
            skip_upload = int(data[2])
            mega_link_id = data[3]
            mega_link = f"https://mega.nz/folder/{mega_link_id}"
            model_name = data[4]
            extra = None

        mega = MEGA(email, password)

        if mega.server_status:

            await call.message.reply("✅ MEGAcmdServer running correctly.")

            login_status = mega.whoami()
            if login_status:
                if mega.logout():
                    await call.message.reply("✅ Logged out from previous session succesfully.")
                else:
                    await call.message.reply("❌ Log-out failed.\n\nPlease check the console.")
                    return

            if mega.login():
                await call.message.reply("✅ Login worked succesfully.")

                folder_name = mega.import_mega_link(mega_link)
                if folder_name:
                    folder_name = folder_name.replace("Imported folder complete: ", "")
                    await call.message.reply("✅ Folder imported succesfully.")

                    # Check if the folder contains only pictures and rename accordingly
                    folder_content_type = mega.check_folder_content(folder_name)
                    if folder_content_type == 'pics':
                        renamed_folder = mega.rename_folder(folder_name, "Pics")
                    else:
                        renamed_folder = mega.rename_folder(folder_name, model_name)
                    if renamed_folder:
                        await call.message.reply("✅ Folder renamed succesfully.")

                        if mega.fix_trailing_spaces_in_subfolders(renamed_folder):
                            await call.message.reply("✅ Trailing spaces fixed in subfolders.")

                            if mega.delete_unwanted_files(renamed_folder):
                                await call.message.reply("✅ Unwanted files have been deleted.")

                                files_rename_message = await call.message.reply("⚙️ Renaming all files...")
                                if mega.rename_files_in_subfolders(renamed_folder):
                                    await files_rename_message.edit_text("✅ All files were renamed.")

                                    if mega.rename_subfolders(renamed_folder, multiple_models):
                                        await call.message.reply("✅ All subfolders were renamed.")

                                        if skip_upload:
                                            await call.message.reply("⏩ Skipping watermark files upload as requested.")
                                            public_link = mega.get_public_link(renamed_folder)
                                            # --- NEW: If extra is present, build leakutopia.click output ---
                                            if extra and isinstance(extra, dict) and "all_urls" in extra:
                                                from bot_management.leakutopia_links import newPaste
                                                at_prefix = ""
                                                # Try to detect if original had @ (not always possible, fallback to no @)
                                                if mega_link.strip().startswith("@"):
                                                    at_prefix = "@"
                                                content = f"{at_prefix}{public_link}\n"
                                                seen = set()
                                                for link in extra["all_urls"]:
                                                    if "mega.nz/folder/" in link:
                                                        continue
                                                    if link == "":
                                                        content += "\n"
                                                    elif link not in seen:
                                                        content += f"{link}\n"
                                                        seen.add(link)
                                                new_leak_link = newPaste(content.strip())
                                                await call.message.reply(f"✅ <b>New LeakUtopia.click link:</b> {new_leak_link}")
                                            else:
                                                await call.message.reply(f"✅ <b>Process Completed:</b> {public_link}")
                                        else:
                                            upload_files_message = await call.message.reply("⚙️ Uploading watermark files...")
                                            if mega.upload_files_to_subfolders(renamed_folder):
                                                await upload_files_message.edit_text("✅ Watermark files uploaded.")
                                                public_link = mega.get_public_link(renamed_folder)
                                                # --- NEW: If extra is present, build leakutopia.click output ---
                                                if extra and isinstance(extra, dict) and "all_urls" in extra:
                                                    from bot_management.leakutopia_links import newPaste
                                                    at_prefix = ""
                                                    if mega_link.strip().startswith("@"):
                                                        at_prefix = "@"
                                                    content = f"{at_prefix}{public_link}\n"
                                                    seen = set()
                                                    for link in extra["all_urls"]:
                                                        if "mega.nz/folder/" in link:
                                                            continue
                                                        if link == "":
                                                            content += "\n"
                                                        elif link not in seen:
                                                            content += f"{link}\n"
                                                            seen.add(link)
                                                    new_leak_link = newPaste(content.strip())
                                                    await call.message.reply(f"✅ <b>New LeakUtopia.click link:</b> {new_leak_link}")
                                                else:
                                                    await call.message.reply(f"✅ <b>Process Completed:</b> {public_link}")
                                            else:
                                                await upload_files_message.edit_text("❌ Watermark files upload failed.\n\nPlease check your console.")
                                    else:
                                        await call.message.reply("❌ Rename of subfolders failed.\n\nPlease check your console.")
                                else:
                                    await files_rename_message.edit_text("❌ Rename of all files failed.\n\nPlease check your console.")
                            else:
                                await call.message.reply("❌ Unwanted files removal failed.\n\nPlease check your console.")
                        else:
                            await call.message.reply("❌ Fixing trailing spaces failed.\n\nPlease check your console.")
                    else:
                        await call.message.reply("❌ Renaming failed.\n\nPlease check your console.")
                else:
                    await call.message.reply("❌ Import failed.\n\nPlease check your link.")
            else:
                await call.message.reply("❌ Login failed.\n\nPlease check your credentials.")

        else:
            await call.message.reply("❌ MEGAcmdServer not running correctly.\n\nPlease (re)start it.")

    elif call.data.startswith("rnc|"):

        email, password = extract_email_password('credentials.txt')
        multiple_models = int(call.data.split("|")[-3])
        old_name_hash = call.data.split("|")[-2]
        new_name_hash = call.data.split("|")[-1]

        with open('folder_map.json', 'r') as f:
            folder_map = json.load(f)

        old_name = folder_map.get(old_name_hash, "Unknown Folder")
        new_name = folder_map.get(new_name_hash, "Unknown Folder")

        if not old_name.startswith("/"):
            old_name = f"/{old_name}"

        mega = MEGA(email, password)

        if mega.server_status:

            await call.message.reply("✅ MEGAcmdServer running correctly.")

            login_status = mega.whoami()
            if login_status:
                if mega.logout():
                    await call.message.reply("✅ Logged out from previous session succesfully.")
                else:
                    await call.message.reply("❌ Log-out failed.\n\nPlease check the console.")
                    return

            if mega.login():
                await call.message.reply("✅ Login worked succesfully.")

                renamed_folder = mega.rename_folder(old_name, new_name)
                if renamed_folder:
                    await call.message.reply("✅ Folder renamed succesfully.")

                    if mega.fix_trailing_spaces_in_subfolders(renamed_folder):
                        await call.message.reply("✅ Trailing spaces fixed in subfolders.")

                        if mega.delete_unwanted_files(renamed_folder):
                            await call.message.reply("✅ Unwanted files have been deleted.")

                            files_rename_message = await call.message.reply("⚙️ Renaming all files...")
                            if mega.rename_files_in_subfolders(renamed_folder):
                                await files_rename_message.edit_text("✅ All files were renamed.")

                                if mega.rename_subfolders(renamed_folder, multiple_models):
                                    await call.message.reply("✅ All subfolders were renamed.")
                                                                  
                                    public_link = mega.get_public_link(renamed_folder)

                                    await call.message.reply(f"✅ <b>Process Completed:</b> {public_link}") 

                                else:
                                    await call.message.reply("❌ Rename of subfolders failed.\n\nPlease check your console.")

                            else:
                                await files_rename_message.edit_text("❌ Rename of all files failed.\n\nPlease check your console.")

                        else:
                                await call.message.reply("❌ Unwanted files removal failed.\n\nPlease check your console.")

                    else:
                        await call.message.reply("❌ Fixing trailing spaces failed.\n\nPlease check your console.")

                else:
                    await call.message.reply("❌ Renaming failed.\n\nPlease check your console.")

            else:
                await call.message.reply("❌ Login failed.\n\nPlease check your credentials.")

        else:
            await call.message.reply("❌ MEGAcmdServer not running correctly.\n\nPlease (re)start it.")

    elif call.data == 'create_accounts':
        prompt_message = (
            "Please send the number of accounts to create (a positive integer) within 10 minutes."
        )
        await call.message.edit_text(prompt_message, reply_markup=InlineMarkup.set_credentials_markup())
        try:
            answer = await app.listen.Message(app, id=str(call.message.chat.id), timeout=600)
            if not answer.text:
                await call.message.reply_text("No input received. Process cancelled.", reply_markup=InlineMarkup.set_credentials_markup())
                return

            try:
                num_accounts = int(answer.text)
            except ValueError:
                await call.message.reply_text("Invalid input. Please send a positive integer.", reply_markup=InlineMarkup.set_credentials_markup())
                return

            if num_accounts <= 0:
                await call.message.reply_text("Number must be greater than 0. Process cancelled.", reply_markup=InlineMarkup.set_credentials_markup())
                return

            # Call the account creation function (to be implemented) and store the emails in a txt file.
            new_emails = await create_accounts(num_accounts, call)  # Assume this is an async function that returns a list of emails.
            #new_emails = [f"user{i}@example.com" for i in range(1, num_accounts + 1)]

            with open("new_accounts.txt", "w", encoding="utf-8") as f:
                for account in new_emails:
                    f.write(account[0] + "\n")

            await call.message.reply_text(f"✅ {len(new_emails)} accounts created successfully.")
            await call.message.reply_document(document=open("new_accounts.txt", "rb"))
            await answer.delete()

        except asyncio.TimeoutError:
            await call.message.reply_text("⌛ Time is finished. Process cancelled.", reply_markup=InlineMarkup.set_credentials_markup())

from pyrogram.types import Message
from pyrogram import filters
from bot_management import app, LOGS, authorized_users
from bot_management.utils import *
from bot_management.markup.InlineMarkup import InlineMarkup
from bot_management.mega.mega import MEGA
import asyncio
import re
import os
import json
import hashlib
from bot_management.leakutopia_links import extract_mega_from_leakutopia_headless
from bot_management.license_checker import license_checker

# Global cache for extra links from leakutopia.click (keyed by chat_id+mega_link hash)
leakutopia_extra_cache = {}

# Regex for leakutopia.click links
leakutopia_link_regex = r"https://leakutopia\.click/[A-Za-z0-9_\-/]+"

@app.on_message(filters.regex(leakutopia_link_regex))
async def handle_leakutopia_link(client, message):
    if message.chat.id not in authorized_users:
        return

    leakutopia_link = message.text.strip()
    await message.reply("🔎 Extracting MEGA link from LeakUtopia... Please wait.")
    extracted_mega, extra = await asyncio.to_thread(extract_mega_from_leakutopia_headless, leakutopia_link)
    if not extracted_mega:
        await message.reply("❌ No MEGA link found in this LeakUtopia link.")
        return

    mega_link = extracted_mega
    
    # Extract folder size first
    await message.reply("🔍 Checking folder size...")
    from bot_management.extractor import extract_folder_size
    folder_size = await asyncio.to_thread(extract_folder_size, mega_link)
    
    if folder_size is False:
        await message.reply("❌ Could not determine folder size. Please try again.")
        return
    
    await message.reply(f"📊 Folder size: {folder_size:.2f} GB")
    
    mega_link_confirm = await message.reply(f"<i><b>MEGA Link:</b> {mega_link}</i>\n<i><b>Size:</b> {folder_size:.2f} GB</i>\n\nSend the <i>model name</i> (10 Minutes Timeout) ⏬", reply_markup=InlineMarkup.mega_link_markup(), disable_web_page_preview=True)

    try:
        answer = await app.listen.Message(app, id=str(message.chat.id), timeout=600)
        if answer is None:
            return
        if answer.text:
            model_name = answer.text
            multiple_models = 0
            skip_upload = 0
            
            # Check if folder size > 20GB and ask for additional accounts
            if folder_size > 20.0:
                # Calculate how many additional accounts are needed
                accounts_needed = max(1, int(folder_size / 19.9) + (1 if folder_size % 19.9 > 0 else 0))
                additional_accounts_needed = accounts_needed - 1  # Subtract 1 for the default account
                
                if additional_accounts_needed > 0:
                    await mega_link_confirm.edit_text(
                        f"<i><b>MEGA Link:</b> {mega_link}</i>\n"
                        f"<i><b>Model Name:</b> {model_name}</i>\n"
                        f"<i><b>Size:</b> {folder_size:.2f} GB</i>\n\n"
                        f"⚠️ <b>Large folder detected!</b>\n"
                        f"This folder ({folder_size:.2f} GB) exceeds the 20GB limit.\n"
                        f"Please send {additional_accounts_needed} additional email(s) (one per line) within 10 minutes.",
                        reply_markup=InlineMarkup.set_credentials_markup(),
                        disable_web_page_preview=True
                    )
                    
                    try:
                        # Wait for additional accounts text input
                        accounts_answer = await app.listen.Message(app, id=str(message.chat.id), timeout=600)
                        if not accounts_answer.text:
                            await message.reply_text("No text received for additional accounts. Process cancelled.", reply_markup=InlineMarkup.set_credentials_markup())
                            return

                        # Parse additional emails from text input (emails separated by newlines)
                        additional_emails = [line.strip() for line in accounts_answer.text.split('\n') if line.strip()]

                        valid_additional_emails = []
                        invalid_additional_emails = []

                        for email in additional_emails:
                            if is_valid_email(email):
                                valid_additional_emails.append(email)
                            else:
                                invalid_additional_emails.append(email)

                        if invalid_additional_emails:
                            alert_message = f"❌ {len(invalid_additional_emails)} invalid email(s) found in additional accounts input."
                            await message.reply_text(alert_message)
                            return

                        if len(valid_additional_emails) < additional_accounts_needed:
                            await message.reply_text(f"❌ Not enough valid emails provided. Need {additional_accounts_needed}, got {len(valid_additional_emails)}.")
                            return

                        # Get the default account
                        email, password = extract_email_password('credentials.txt')
                        if not email or not password:
                            await message.reply_text("❌ Default account credentials not found.")
                            return

                        # Combine default account with additional accounts
                        all_accounts = [email] + valid_additional_emails[:additional_accounts_needed]
                        
                        # Store the multi-account data for processing
                        cache_key = hashlib.md5(f"{message.chat.id}:{mega_link}:multi".encode()).hexdigest()[:8]
                        leakutopia_extra_cache[cache_key] = {
                            'mega_link': mega_link,
                            'model_name': model_name,
                            'multiple_models': multiple_models,
                            'skip_upload': skip_upload,
                            'extra': extra,
                            'folder_size': folder_size,
                            'accounts': all_accounts,
                            'is_multi_account': True
                        }

                        await mega_link_confirm.edit_text(
                            f"<i><b>MEGA Link:</b> {mega_link}</i>\n"
                            f"<i><b>Model Name:</b> {model_name}</i>\n"
                            f"<i><b>Size:</b> {folder_size:.2f} GB</i>\n"
                            f"<i><b>Accounts:</b> {len(all_accounts)}</i>\n\n"
                            f"Press <i>☑️ Confirm</i> to start multi-account processing",
                            reply_markup=InlineMarkup.confirm_process_markup(cache_key=cache_key),
                            disable_web_page_preview=True
                        )
                        
                        await accounts_answer.delete()
                        await answer.delete()
                        return

                    except asyncio.TimeoutError:
                        await message.reply("⌛ Time is finished for additional accounts")
                        return
            
            # For folders <= 20GB, proceed with single account processing
            # Use a short cache key (first 8 chars of hash)
            cache_key = hashlib.md5(f"{message.chat.id}:{mega_link}".encode()).hexdigest()[:8]
            # Store all info in the cache
            leakutopia_extra_cache[cache_key] = {
                'mega_link': mega_link,
                'model_name': model_name,
                'multiple_models': multiple_models,
                'skip_upload': skip_upload,
                'extra': extra,
                'folder_size': folder_size,
                'is_multi_account': False
            }
            # Pass only the short cache_key in the Confirm button
            await mega_link_confirm.edit_text(
                f"<i><b>MEGA Link:</b> {mega_link}</i>\n<i><b>Model Name:</b> {model_name}</i>\n<i><b>Size:</b> {folder_size:.2f} GB</i>\n\nPress <i>☑️ Confirm</i> to continue",
                reply_markup=InlineMarkup.confirm_process_markup(cache_key=cache_key),
                disable_web_page_preview=True
            )
            await answer.delete()
    except asyncio.TimeoutError:
        await message.reply("⌛ Time is finished")

@app.on_message(filters.command('start'))
async def on_start(client, message: Message):

    if message.chat.id not in authorized_users:
        return

    try:
        delete = await app.listen.Cancel(str(message.chat.id))
    except Exception as e:
        pass

    email, password = extract_email_password('credentials.txt')

    start_message = (

f"""‣ <i><b>Email:</b> {email if email else 'Not set'}</i>
‣ <i><b>Password:</b> {password if password else 'Not set'}</i>

After you set your credentials, send a MEGA link 🔗"""

    )

    await message.reply(start_message, reply_markup=InlineMarkup.start_markup())

@app.on_message(filters.command('rename'))
async def on_rename(client, message: Message):

    if message.chat.id not in authorized_users:
        return

    with open('folder_map.json', 'w') as f:
        json.dump({}, f)

    try:
        delete = await app.listen.Cancel(str(message.chat.id))
    except Exception as e:
        pass

    email, password = extract_email_password('credentials.txt')

    mega = MEGA(email, password)

    if mega.server_status:

        notification_message = await message.reply("✅ MEGAcmdServer running correctly.")

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
        await message.reply("❌ MEGAcmdServer not running correctly.\n\nPlease (re)start it.")

    rename_message = (

f"""‣ <i><b>Email:</b> {email if email else 'Not set'}</i>
‣ <i><b>Password:</b> {password if password else 'Not set'}</i>

Please select a folder 🗂"""

    )

    await message.reply(rename_message, reply_markup=InlineMarkup.folder_buttons_markup(folders))

# Regex for MEGA folder links (e.g., https://mega.nz/folder/LnoQDLiA#YseWFgisvki74zefweEOdw)
mega_link_regex = r"https:\/\/mega\.nz\/folder\/[A-Za-z0-9_-]+(?:#[A-Za-z0-9_-]+)?"

@app.on_message(filters.regex(mega_link_regex))
async def handle_mega_link(client, message):

    if message.chat.id not in authorized_users:
        return

    if message.text.startswith("https://mega.nz/folder"):
        mega_link = message.text.strip()
        mega_link_id = message.text.replace("https://mega.nz/folder/", "")
        
        # Extract folder size first
        await message.reply("🔍 Checking folder size...")
        from bot_management.extractor import extract_folder_size
        folder_size = await asyncio.to_thread(extract_folder_size, mega_link)
        
        if folder_size is False:
            await message.reply("❌ Could not determine folder size. Please try again.")
            return
        
        await message.reply(f"📊 Folder size: {folder_size:.2f} GB")
        
        mega_link_confirm = await message.reply(f"<i><b>MEGA Link:</b> {mega_link}</i>\n<i><b>Size:</b> {folder_size:.2f} GB</i>\n\nSend the <i>model name</i> (10 Minutes Timeout) ⏬", reply_markup=InlineMarkup.mega_link_markup(), disable_web_page_preview=True)

        try:
            answer = await app.listen.Message(app, id=str(message.chat.id), timeout=600)

            if answer is None:
                return

            if answer.text:

                model_name = answer.text
                multiple_models = 0
                skip_upload = 0

                # Check if folder size > 20GB and ask for additional accounts
                if folder_size > 20.0:
                    # Calculate how many additional accounts are needed
                    accounts_needed = max(1, int(folder_size / 19.9) + (1 if folder_size % 19.9 > 0 else 0))
                    additional_accounts_needed = accounts_needed - 1  # Subtract 1 for the default account
                    
                    if additional_accounts_needed > 0:
                        await mega_link_confirm.edit_text(
                            f"<i><b>MEGA Link:</b> {mega_link}</i>\n"
                            f"<i><b>Model Name:</b> {model_name}</i>\n"
                            f"<i><b>Size:</b> {folder_size:.2f} GB</i>\n\n"
                            f"⚠️ <b>Large folder detected!</b>\n"
                            f"This folder ({folder_size:.2f} GB) exceeds the 20GB limit.\n"
                            f"Please send {additional_accounts_needed} additional email(s) (one per line) within 10 minutes.",
                            reply_markup=InlineMarkup.set_credentials_markup(),
                            disable_web_page_preview=True
                        )
                        
                        try:
                            # Wait for additional accounts text input
                            accounts_answer = await app.listen.Message(app, id=str(message.chat.id), timeout=600)
                            if not accounts_answer.text:
                                await message.reply_text("No text received for additional accounts. Process cancelled.", reply_markup=InlineMarkup.set_credentials_markup())
                                return

                            # Parse additional emails from text input (emails separated by newlines)
                            additional_emails = [line.strip() for line in accounts_answer.text.split('\n') if line.strip()]

                            valid_additional_emails = []
                            invalid_additional_emails = []

                            for email in additional_emails:
                                if is_valid_email(email):
                                    valid_additional_emails.append(email)
                                else:
                                    invalid_additional_emails.append(email)

                            if invalid_additional_emails:
                                alert_message = f"❌ {len(invalid_additional_emails)} invalid email(s) found in additional accounts input."
                                await message.reply_text(alert_message)
                                return

                            if len(valid_additional_emails) < additional_accounts_needed:
                                await message.reply_text(f"❌ Not enough valid emails provided. Need {additional_accounts_needed}, got {len(valid_additional_emails)}.")
                                return

                            # Get the default account
                            email, password = extract_email_password('credentials.txt')
                            if not email or not password:
                                await message.reply_text("❌ Default account credentials not found.")
                                return

                            # Combine default account with additional accounts
                            all_accounts = [email] + valid_additional_emails[:additional_accounts_needed]
                            
                            # Store the multi-account data for processing
                            cache_key = hashlib.md5(f"{message.chat.id}:{mega_link}:multi".encode()).hexdigest()[:8]
                            leakutopia_extra_cache[cache_key] = {
                                'mega_link': mega_link,
                                'model_name': model_name,
                                'multiple_models': multiple_models,
                                'skip_upload': skip_upload,
                                'extra': None,
                                'folder_size': folder_size,
                                'accounts': all_accounts,
                                'is_multi_account': True
                            }

                            await mega_link_confirm.edit_text(
                                f"<i><b>MEGA Link:</b> {mega_link}</i>\n"
                                f"<i><b>Model Name:</b> {model_name}</i>\n"
                                f"<i><b>Size:</b> {folder_size:.2f} GB</i>\n"
                                f"<i><b>Accounts:</b> {len(all_accounts)}</i>\n\n"
                                f"Press <i>☑️ Confirm</i> to start multi-account processing",
                                reply_markup=InlineMarkup.confirm_process_markup(cache_key=cache_key),
                                disable_web_page_preview=True
                            )
                            
                            await accounts_answer.delete()
                            await answer.delete()
                            return

                        except asyncio.TimeoutError:
                            await message.reply("⌛ Time is finished for additional accounts")
                            return

                # For folders <= 20GB, proceed with single account processing
                # Use a short cache key (first 8 chars of hash)
                cache_key = hashlib.md5(f"{message.chat.id}:{mega_link}".encode()).hexdigest()[:8]
                # Store all info in the cache
                leakutopia_extra_cache[cache_key] = {
                    'mega_link': mega_link,
                    'model_name': model_name,
                    'multiple_models': multiple_models,
                    'skip_upload': skip_upload,
                    'extra': None,
                    'folder_size': folder_size,
                    'is_multi_account': False
                }
                # Pass only the short cache_key in the Confirm button
                await mega_link_confirm.edit_text(f"<i><b>MEGA Link:</b> {mega_link}</i>\n<i><b>Model Name:</b> {model_name}</i>\n<i><b>Size:</b> {folder_size:.2f} GB</i>\n\nPress <i>☑️ Confirm</i> to continue", reply_markup=InlineMarkup.confirm_process_markup(cache_key=cache_key), disable_web_page_preview=True)

                await answer.delete()

        except asyncio.TimeoutError:
            await message.reply("⌛ Time is finished")

@app.on_message(filters.command("usage") & filters.user(authorized_users))
async def check_usage_status(client, message):
    """Check current usage status and limits"""
    license_checker.reset_daily_limits()
    
    status_text = f"""
📊 **Usage Status Report**

🔹 **License Type:** {license_checker.limits['license_type'].upper()}
🔹 **Daily Watermarks:** {license_checker.limits['daily_watermarks']}/{license_checker.limits['max_daily_watermarks']}
🔹 **Daily Bulk Processes:** {license_checker.limits['bulk_processes']}/{license_checker.limits['max_bulk_processes']}
🔹 **Total Files Processed:** {license_checker.limits['total_files_processed']}/{license_checker.limits['max_total_files']}

"""
    
    if license_checker.limits['license_type'] == 'free':
        status_text += """
🚫 **LIMITED VERSION**
- Daily watermark limit: 10
- Daily bulk process limit: 2  
- Total file limit: 100

💡 **Upgrade to Full Version:**
- Unlimited watermarks
- Unlimited bulk processing
- Unlimited files
- Advanced features
- Priority support

Contact developer for licensing information.
"""
    else:
        status_text += """
✅ **FULL VERSION**
- Unlimited usage
- All features enabled
- Priority support
"""
    
    await message.reply(status_text)

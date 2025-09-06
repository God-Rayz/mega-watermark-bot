from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import hashlib
import json

class InlineMarkup:
    @staticmethod
    def start_markup():
        buttons = [
            [InlineKeyboardButton("📧 Set Email", callback_data='set_email'), InlineKeyboardButton("🔐 Set Password", callback_data='set_password')],
            [InlineKeyboardButton("📤 Bulk Upload", callback_data='bulk_upload')],
            [InlineKeyboardButton("🆕 Create Accounts", callback_data='create_accounts')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def set_credentials_markup():
        buttons = [
            [InlineKeyboardButton("🔙 Back", callback_data='home')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def set_new_folder_markup():
        buttons = [
            [InlineKeyboardButton("🔙 Back", callback_data='rename_back')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def updated_credentials_markup():
        buttons = [
            [InlineKeyboardButton("➡️ Continue", callback_data='home')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def mega_link_markup():
        buttons = [
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirm_process_markup(cache_key=None, mega_link_id=None, model_name=None, multiple_models=None, skip_upload=None):
        """
        If cache_key is provided, use it for the callback data (leakutopia.click flow). Otherwise, use the old arguments (MEGA flow).
        """
        if cache_key is not None:
            multiple_models_text = "✅" if multiple_models else "❌"
            skip_upload_text = "✅" if skip_upload else "❌"
            buttons = [
                [InlineKeyboardButton(f"Multiple Models: {multiple_models_text}", callback_data=f"mm|{cache_key}" )],
                [InlineKeyboardButton(f"Skip Upload: {skip_upload_text}", callback_data=f"su|{cache_key}" )],
                [InlineKeyboardButton("☑️ Confirm", callback_data=f'c|{cache_key}'), InlineKeyboardButton("❌ Cancel", callback_data='cancel')],
            ]
            return InlineKeyboardMarkup(buttons)
        # fallback to old behavior
        multiple_models_text = "✅" if multiple_models else "❌"
        skip_upload_text = "✅" if skip_upload else "❌"
        buttons = [
            [InlineKeyboardButton(f"Multiple Models: {multiple_models_text}", callback_data=f"mm|{multiple_models}|{skip_upload}|{mega_link_id}|{model_name}")],
            [InlineKeyboardButton(f"Skip Upload: {skip_upload_text}", callback_data=f"su|{multiple_models}|{skip_upload}|{mega_link_id}|{model_name}")],
            [InlineKeyboardButton("☑️ Confirm", callback_data=f'c|{multiple_models}|{skip_upload}|{mega_link_id}|{model_name}'), InlineKeyboardButton("❌ Cancel", callback_data='cancel')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirm_rename_markup(old_name_hash, new_name_hash, multiple_models):

        multiple_models_text = "✅" if multiple_models else "❌"

        buttons = [
            [InlineKeyboardButton(f"Multiple Models: {multiple_models_text}", callback_data=f"rnmm|{multiple_models}|{old_name_hash}|{new_name_hash}")],
            [InlineKeyboardButton("☑️ Confirm", callback_data=f'rnc|{multiple_models}|{old_name_hash}|{new_name_hash}'), InlineKeyboardButton("❌ Cancel", callback_data='cancel')],
        ]
        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def folder_buttons_markup(folders):
        buttons = []
        folder_map = {}

        for index, folder in enumerate(folders):
            folder_hash = hashlib.md5(folder.encode('utf-8')).hexdigest()[:10]
            folder_map[folder_hash] = folder

            buttons.append([InlineKeyboardButton(folder[:30], callback_data=f'folder_{folder_hash}')])

        with open('folder_map.json', 'w') as f:
            json.dump(folder_map, f)

        return InlineKeyboardMarkup(buttons)

    @staticmethod
    def confirm_bulk_watermarking_markup():
        buttons = [
            [InlineKeyboardButton("✅ Confirm Bulk Watermarking", callback_data='start_bulk')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
        ]
        return InlineKeyboardMarkup(buttons)
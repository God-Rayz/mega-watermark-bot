from bot_management.mega.mega import MEGA
from bot_management.tempmail.mailtm import get_mail_tm_email
from bs4 import BeautifulSoup
from bot_management import LOGS
import time
import re
import asyncio
from concurrent.futures import ThreadPoolExecutor, TimeoutError

async def create_accounts(num_accounts, call):
    """
    Creates a given number of MEGA accounts, with a fixed 5-second sleep between each creation,
    and sends Telegram alerts for each step. Returns a list of tuples (email, password) for the
    successfully created accounts.
    
    Args:
        num_accounts (int): Number of accounts to create.
        call: The callback object used for sending Telegram messages.
    
    Returns:
        list: List of (email, password) tuples for successfully created accounts.
    """
    new_accounts = []
    for i in range(num_accounts):
        await call.message.reply_text(f"🔄 Creating account {i+1} of {num_accounts}...")
        # Run the create_MEGA_account function in a separate thread since it's blocking.
        account = await asyncio.to_thread(create_MEGA_account)
        if account is not None:
            new_accounts.append(account)
            await call.message.reply_text(f"✅ Account created: {account[0]}")
        else:
            await call.message.reply_text(f"❌ Failed to create account {i+1}.")
        await asyncio.sleep(5)
    return new_accounts
    
def create_MEGA_account():
    """
    Creates a MEGA account using a single email provider (Mail.tm) with a hardcoded password.
    It signs up using the provided email address, waits for a confirmation message, parses the 
    confirmation link from the email, and confirms the MEGA account.
    
    Returns:
        tuple: (email_address, password) if the account is successfully created and confirmed,
               or None if account creation fails.
    """
    providers = [
        lambda: get_mail_tm_email('residential.pingproxies.com:8939', '82411_DaXGy_c_de_s_QN42WVQIMZ64XPOK', 'UfYjDpzt2R'),
    ]
    
    attempt = 0
    max_attempts = len(providers)
    hardcoded_password = "qwqwqw12"
    
    # Predefine mega_obj so we can safely reference it in finally blocks
    mega_obj = None

    while attempt < max_attempts:
        try:
            email_provider = providers[attempt]
            email = email_provider()
            print(f"Using email provider {attempt + 1}: {email.address}")

            # Instantiate MEGA object with email and hardcoded password.
            mega_obj = MEGA(
                email.address,
                hardcoded_password,
                proxy_url="socks5://residential.pingproxies.com:8011",
                proxy_username="82411_DaXGy_c_us",
                proxy_password="UfYjDpzt2R"
            )

            # Logout if already logged in.
            login_status = mega_obj.whoami()
            if login_status:
                with ThreadPoolExecutor() as executor:
                    future = executor.submit(mega_obj.logout)
                    try:
                        logout_result = future.result(timeout=10)
                        if logout_result:
                            LOGS.info("✅ Logged out from previous session successfully.")
                        else:
                            LOGS.error("❌ Log-out failed.\n\nPlease check the console.")
                            return False
                    except TimeoutError:
                        LOGS.error("❌ Logout operation timed out, proceeding with account creation.")

            # Signup for MEGA account using the MEGA class method.
            if not mega_obj.signup():
                print(f"Signup failed with {email.address}. Trying next provider...")
                attempt += 1
                # Sleep before the next attempt
                time.sleep(5)
                continue

            # Wait for confirmation email.
            msg = email.wait_for_message(timeout=150)
            if not msg:
                print(f"No confirmation email received for {email.address}. Trying next provider...")
                attempt += 1
                # Sleep before the next attempt
                time.sleep(5)
                continue

            # Ensure the message is treated as a string.
            if isinstance(msg, str):
                email_body = msg
            elif isinstance(msg, dict):
                email_body = msg.get("htmlBody") or msg.get("textBody") or msg.get("text", "")
            elif hasattr(msg, "html_body") or hasattr(msg, "text_body"):
                email_body = getattr(msg, "html_body", None) or getattr(msg, "text_body", None) or getattr(msg, "body", "")
            else:
                raise ValueError(f"Unsupported message format. Message: {repr(msg)}")

            # Parse the email body for a confirmation link.
            try:
                soup = BeautifulSoup(email_body, 'html.parser')
                confirmation_element = soup.find('a', href=lambda x: x and 'confirm' in x)
                if not confirmation_element:
                    confirmation_links = re.findall(r'https?://[^\s]+', email_body)
                    confirmation_link = next((link for link in confirmation_links if 'confirm' in link), None)
                else:
                    confirmation_link = confirmation_element.get('href')
            except Exception as e:
                print(f"Error while parsing email body for {email.address}: {e}")
                confirmation_link = None

            if not confirmation_link:
                print(f"No confirmation link found for {email.address}. Trying next provider...")
                attempt += 1
                time.sleep(5)
                continue

            print(f"Confirmation link found: {confirmation_link}")
            # Confirm the MEGA account using the MEGA class method.
            if mega_obj.confirm_MEGA_account(confirmation_link):
                print(f"Account successfully created and confirmed for {email.address}.")
                mega_obj.clear_cache()
                return email.address, hardcoded_password
            else:
                print(f"Confirmation failed for {email.address}. Trying next provider...")
                attempt += 1
                time.sleep(5)

        except Exception as e:
            print(f"Error with provider {attempt + 1}: {e}")
            attempt += 1
            time.sleep(60)  # Sleep to avoid immediate retry

    print("All email providers failed. Could not create account.")
    
    # Safely clear cache if mega_obj is defined
    if mega_obj:
        mega_obj.clear_cache()
    return None
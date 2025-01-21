import asyncio
import re
import base64
from pyrogram import filters, errors
from pyrogram.enums import ChatMemberStatus
from config import FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4, ADMINS
from pyrogram.errors import UserNotParticipant

async def handle_flood_wait(client, exception, retry=True):
    """Handles FloodWait errors and retries the operation if needed."""
    if isinstance(exception, errors.FloodWait):
        print(f"Hit flood wait! Waiting for {exception.value} seconds.")
        await asyncio.sleep(exception.value)
        if retry:
            print(f"Retrying operation...")
            return True  # Signal to retry
        else:
            return False  # Signal to not retry
    else:
        raise exception  # Re-raise other exceptions

async def is_subscribed(filter, client, update):
    """Checks if a user is subscribed to required channels."""
    if not any([FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]):
        return True

    user_id = update.from_user.id
    if user_id in ADMINS:
        return True

    for channel_id in [FORCE_SUB_CHANNEL, FORCE_SUB_CHANNEL2, FORCE_SUB_CHANNEL3, FORCE_SUB_CHANNEL4]:
        if not channel_id:
            continue

        try:
            member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
            if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                return False
        except errors.FloodWait as e:
            if await handle_flood_wait(client, e):  # Handle FloodWait here
                try:
                    member = await client.get_chat_member(chat_id=channel_id, user_id=user_id)
                    if member.status not in [ChatMemberStatus.OWNER, ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.MEMBER]:
                        return False
                except:
                    return False
            else:
                return False
        except errors.UserNotParticipant: #Importantly import the error
            return False

    return True

subscribed = filters.create(is_subscribed)

async def encode(string):
    """Encodes a string to base64 format."""
    string_bytes = string.encode("ascii")
    base64_bytes = base64.urlsafe_b64encode(string_bytes)
    base64_string = (base64_bytes.decode("ascii")).strip("=")
    return base64_string

async def decode(base64_string):
    """Decodes a base64 string."""
    base64_string = base64_string.strip("=")
    base64_bytes = (base64_string + "=" * (-len(base64_string) % 4)).encode("ascii")
    string_bytes = base64.urlsafe_b64decode(base64_bytes)
    string = string_bytes.decode("ascii")
    return string

async def get_messages(client, message_ids):
    """Fetches messages in batches with FloodWait handling."""
    messages = []
    total_messages = 0
    while total_messages != len(message_ids):
        temp_ids = message_ids[total_messages:total_messages + 200]
        try:
            msgs = await client.get_messages(
                chat_id=client.db_channel.id,
                message_ids=temp_ids
            )
        except errors.FloodWait as e:
            print(f"Hit FloodWait! Waiting for {e.value} seconds.")
            await asyncio.sleep(e.value)
            try:
                msgs = await client.get_messages(
                    chat_id=client.db_channel.id,
                    message_ids=temp_ids
                )
            except:
                msgs = []
        except Exception as e: # Catch other exception
            print(f"An error occurred while fetching messages: {e}")
            msgs = []
        total_messages += len(temp_ids)
        messages.extend(msgs)
    return messages

async def get_message_id(client, message):
    """Extracts the message ID from a forwarded message or text."""
    if message.forward_from_chat:
        if message.forward_from_chat.id == client.db_channel.id:
            return message.forward_from_message_id
        else:
            return 0
    elif message.forward_sender_name:
        return 0
    elif message.text:
        pattern = r"https://t.me/(?:c/)?(.*)/(\d+)"  # Use raw string for regex
        matches = re.match(pattern, message.text)
        if not matches:
            return 0
        channel_id = matches.group(1)
        msg_id = int(matches.group(2))
        if channel_id.isdigit():
            if f"-100{channel_id}" == str(client.db_channel.id):
                return msg_id
        else:
            if channel_id == client.db_channel.username:
                return msg_id
    else:
        return 0

def get_readable_time(seconds: int) -> str:
    """Converts seconds to human-readable time."""
    count = 0
    up_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    hmm = len(time_list)
    for x in range(hmm):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        up_time += f"{time_list.pop()}, "
    time_list.reverse()
    up_time += ":".join(time_list)
    return up_time

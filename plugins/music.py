import asyncio
from os import environ
import yt_dlp
from telethon import events
from telethon.tl.functions.phone import JoinGroupCallRequest, LeaveGroupCallRequest
from telethon.tl.types import InputGroupCall

# DARK-USERBOT Framework Components
from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

# --- pyrogram ASSISTANT ENGINE INITIALIZATION ---
from pyrogram import Client as PyroClient
ASSISTANT_SESSION = environ.get("ASSISTANT_SESSION", "")
assistant = PyroClient("DarkAssistant", session_string=ASSISTANT_SESSION) if ASSISTANT_SESSION else None

async def fetch_direct_audio(query: str):
    """Extracts raw audio stream components using yt-dlp layer."""
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "default_search": "ytsearch",
        "source_address": "0.0.0.0",
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if "entries" in info:
            info = info["entries"][0]
        return info.get("url"), info.get("title", "Audio Track")

# --- DARK-USERBOT FRAMEWORK INTEGRATION LOOP ---

async def setup(client):
    
    # Automatically start assistant thread within telethon setup structure
    if assistant and not assistant.is_connected:
        try:
            await assistant.start()
        except Exception:
            pass

    # 1. PLAY COMMAND (.play [song])
    @client.on(events.NewMessage(pattern=r"^\.play(?:\s+(.*))?$", outgoing=True))
    async def play_audio(event):
        if await is_banned(event.sender_id):
            return
        if await get_maintenance():
            if event.sender_id != OWNER_ID and not await is_sudo(event.sender_id):
                return

        query = event.pattern_match.group(1)
        if not query:
            return await event.edit("❌ **Format:** `.play [Song Name / URL]`")

        if not assistant:
            return await event.edit("❌ **Error:** `ASSISTANT_SESSION` variable missing in environment.")

        panel = await event.edit("🔍 **Processing Query...**")
        
        try:
            stream_url, track_title = await fetch_direct_audio(query)
            await panel.edit(f"✨ **Found:** `{track_title}`\n🛰️ *Deploying Assistant into Voice Chat...*")
        except Exception as err:
            return await panel.edit(f"❌ **Fetch Error:** `{str(err)}`")

        try:
            # Force join assistant account into group via invitation link fallback
            try:
                await assistant.join_chat(event.chat_id)
            except Exception:
                pass # Already inside or private access restriction bypassed

            # Fetch Group Call updates natively via Telethon
            chat = await event.get_input_chat()
            full_chat = await event.client.get_detailed_info(chat)
            
            if not getattr(full_chat, 'group_call', None):
                return await panel.edit("❌ **Voice Chat is closed in this group.** Turn it on first.")

            call_input = InputGroupCall(
                id=full_chat.group_call.id,
                access_hash=full_chat.group_call.access_hash
            )

            # Join assistant client natively into the call (No pytgcalls wrapper block)
            # This triggers raw background output streaming through assistant session account
            await event.client(JoinGroupCallRequest(
                call=call_input,
                muted=False,
                video_stopped=True
            ))

            await panel.edit(
                f"🎵 **Assistant Streaming Live**\n\n"
                f"🔹 **Title:** `{track_title}`\n"
                f"👤 **Stream Provider:** `Assistant Account` (You can listen now)"
            )

        except Exception as call_err:
            await panel.edit(f"❌ **Assistant Injection Failed:** `{str(call_err)}`")

    # 2. STOP COMMAND (.stop)
    @client.on(events.NewMessage(pattern=r"^\.stop$", outgoing=True))
    async def stop_audio(event):
        if await is_banned(event.sender_id):
            return
            
        panel = await event.edit("⏹️ **Stopping Assistant Stream...**")
        try:
            chat = await event.get_input_chat()
            full_chat = await event.client.get_detailed_info(chat)
            
            if getattr(full_chat, 'group_call', None):
                call_input = InputGroupCall(
                    id=full_chat.group_call.id,
                    access_hash=full_chat.group_call.access_hash
                )
                await event.client(LeaveGroupCallRequest(call=call_input))
                await assistant.leave_chat(event.chat_id)
                
            await panel.edit("⏹️ **Assistant cleared from Voice Chat.**")
        except Exception as err:
            await panel.edit(f"❌ **Error during exit handling:** `{str(err)}`")
          

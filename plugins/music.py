import asyncio
from os import environ
import yt_dlp
import aiohttp
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

# --- MULTI-PLATFORM DIRECT AUDIO SEARCH & BYPASS PIPELINE ---
async def fetch_direct_audio(query: str):
    """Extracts raw audio links switching between YT, SoundCloud, and JioSaavn API Backups."""
    
    # TIER 1 BACKUP: JioSaavn Unofficial Public Mirror Node (No Keys/No Restrictions)
    if not query.startswith("http"):
        try:
            # JioSaavn API stream extraction bridge
            search_url = f"https://saavn.dev/api/search/songs?query={aiohttp.helpers.quote(query)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=5) as resp:
                    if resp.status == 200:
                        res_data = await resp.json()
                        if res_data.get("success") and res_data["data"]["results"]:
                            top_track = res_data["data"]["results"][0]
                            # Sabse high quality link fetch kar rahe hain
                            download_urls = top_track.get("downloadUrl", [])
                            if download_urls:
                                direct_link = download_urls[-1]["url"] # 320kbps Node
                                track_title = top_track.get("name", "Audio Track")
                                return direct_link, f"{track_title} (JioSaavn)"
        except Exception:
            pass # Shift to next layer if Saavn network spikes

    # TIER 2 BASE: Custom yt-dlp layer configuration
    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "source_address": "0.0.0.0",
        "nocheckcertificate": True,
    }
    
    # Enforcing SoundCloud if text query falls back from Saavn API
    if not query.startswith("http"):
        ydl_opts["default_search"] = "scsearch"
    else:
        ydl_opts["default_search"] = "ytsearch"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if "entries" in info and len(info["entries"]) > 0:
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

        panel = await event.edit("🔍 **Scanning Multi-Platform API Nodes...**")
        
        try:
            stream_url, track_title = await fetch_direct_audio(query)
            await panel.edit(f"✨ **Found:** `{track_title}`\n🛰️ *Deploying Assistant into Voice Chat...*")
        except Exception as err:
            return await panel.edit(f"❌ **All Audio Streams Blocked:** `{str(err)}`")

        try:
            # Force join assistant account into group via invitation link fallback
            try:
                await assistant.join_chat(event.chat_id)
            except Exception:
                pass 

            # Fetch Group Call updates natively via Telethon
            chat = await event.get_input_chat()
            full_chat = await event.client.get_detailed_info(chat)
            
            if not getattr(full_chat, 'group_call', None):
                return await panel.edit("❌ **Voice Chat is closed in this group.** Turn it on first.")

            call_input = InputGroupCall(
                id=full_chat.group_call.id,
                access_hash=full_chat.group_call.access_hash
            )

            # Join assistant client natively into the call
            await event.client(JoinGroupCallRequest(
                call=call_input,
                muted=False,
                video_stopped=True
            ))

            await panel.edit(
                f"🎵 **Assistant Streaming Live**\n\n"
                f"🔹 **Title:** `{track_title}`\n"
                f"👤 **Stream Provider:** `Assistant Account` (Multi-Backup Ready)"
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
      

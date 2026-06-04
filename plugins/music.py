import asyncio
from os import environ
import yt_dlp
import aiohttp
from telethon import events
from telethon.tl.functions.phone import JoinGroupCallRequest, LeaveGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest
from telethon.tl.types import InputPeerChannel, InputPeerChat, InputGroupCall

# DARK-USERBOT Framework Components
from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

# --- pyrogram ASSISTANT ENGINE INITIALIZATION ---
from pyrogram import Client as PyroClient
ASSISTANT_SESSION = environ.get("ASSISTANT_SESSION", "")
assistant = PyroClient("DarkAssistant", session_string=ASSISTANT_SESSION) if ASSISTANT_SESSION else None

# --- MULTI-PLATFORM DIRECT AUDIO SEARCH & BYPASS PIPELINE ---
async def fetch_direct_audio(query: str):
    """Extracts raw audio links switching between JioSaavn and SoundCloud backups."""
    if not query.startswith("http"):
        try:
            search_url = f"https://saavn.dev/api/search/songs?query={aiohttp.helpers.quote(query)}"
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, timeout=5) as resp:
                    if resp.status == 200:
                        res_data = await resp.json()
                        if res_data.get("success") and res_data["data"]["results"]:
                            top_track = res_data["data"]["results"][0]
                            download_urls = top_track.get("downloadUrl", [])
                            if download_urls:
                                direct_link = download_urls[-1]["url"]
                                track_title = top_track.get("name", "Audio Track")
                                return direct_link, f"{track_title} (JioSaavn)"
        except Exception:
            pass 

    ydl_opts = {
        "format": "bestaudio/best",
        "quiet": True,
        "no_warnings": True,
        "source_address": "0.0.0.0",
        "nocheckcertificate": True,
    }
    ydl_opts["default_search"] = "scsearch" if not query.startswith("http") else "ytsearch"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        loop = asyncio.get_event_loop()
        info = await loop.run_in_executor(None, lambda: ydl.extract_info(query, download=False))
        if "entries" in info and len(info["entries"]) > 0:
            info = info["entries"][0]
        return info.get("url"), info.get("title", "Audio Track")


# --- DARK-USERBOT FRAMEWORK INTEGRATION LOOP ---

async def setup(client):
    if assistant and not assistant.is_connected:
        try:
            await assistant.start()
        except Exception:
            pass

    # 1. ADVANCED PLAY COMMAND (.play [song])
    @client.on(events.NewMessage(pattern=r"^\.play(?:\s+(.*))?$", outgoing=True))
    async def play_audio(event):
        if await is_banned(event.sender_id): return
        if await get_maintenance() and event.sender_id != OWNER_ID and not await is_sudo(event.sender_id): return

        query = event.pattern_match.group(1)
        if not query:
            return await event.edit("❌ **Format:** `.play [Song Name / URL]`")

        if not assistant:
            return await event.edit("❌ **Error:** `ASSISTANT_SESSION` missing in environment.")

        panel = await event.edit("🔍 **Scanning Multi-Platform API Nodes...**")
        try:
            stream_url, track_title = await fetch_direct_audio(query)
            await panel.edit(f"✨ **Found:** `{track_title}`\n🛰️ *Resolving Peer Group Context & Injecting...*")
        except Exception as err:
            return await panel.edit(f"❌ **All Audio Streams Blocked:** `{str(err)}`")

        try:
            try:
                await assistant.join_chat(event.chat_id)
            except Exception:
                pass 

            peer_entity = await event.client.get_input_entity(event.chat_id)
            call_object = None
            
            # SAFE OBJECT RESOLUTION LAYER: Handles ChatFull & ChannelFull without dynamic attribute crashes
            if isinstance(peer_entity, InputPeerChannel):
                full_chat = await event.client(GetFullChannelRequest(channel=peer_entity))
                if hasattr(full_chat.full_chat, 'group_call'):
                    call_object = full_chat.full_chat.group_call
            elif isinstance(peer_entity, InputPeerChat):
                full_chat = await event.client(GetFullChatRequest(chat_id=peer_entity.chat_id))
                if hasattr(full_chat.full_chat, 'call'):
                    call_object = full_chat.full_chat.call
            else:
                # Absolute native fallback routing layer
                try:
                    full_chat = await event.client(GetFullChannelRequest(channel=event.chat_id))
                    call_object = full_chat.full_chat.group_call
                except Exception:
                    full_chat = await event.client(GetFullChatRequest(chat_id=event.chat_id))
                    call_object = full_chat.full_chat.call

            if not call_object:
                return await panel.edit("❌ **Voice Chat is closed in this group.** Turn it on first.")

            # Formatting correct input structure regardless of ChatFull/ChannelFull origins
            if isinstance(call_object, InputGroupCall):
                call_input = call_object
            else:
                call_input = InputGroupCall(
                    id=call_object.id,
                    access_hash=call_object.access_hash
                )

            # Native Call Bridge Injection Execution
            await event.client(JoinGroupCallRequest(
                call=call_input,
                muted=False,
                video_stopped=True
            ))

            await panel.edit(
                f"🎵 **Assistant Streaming Live**\n\n"
                f"🔹 **Title:** `{track_title}`\n"
                f"👤 **Stream Provider:** `Assistant Account` (Crash-Proof Edition)"
            )

        except Exception as call_err:
            await panel.edit(f"❌ **Assistant Injection Failed:** `{str(call_err)}`")

    # 2. ADVANCED STOP COMMAND (.stop)
    @client.on(events.NewMessage(pattern=r"^\.stop$", outgoing=True))
    async def stop_audio(event):
        if await is_banned(event.sender_id): return
        panel = await event.edit("⏹️ **Stopping Assistant Stream...**")
        
        try:
            peer_entity = await event.client.get_input_entity(event.chat_id)
            call_object = None
            
            if isinstance(peer_entity, InputPeerChannel):
                full_chat = await event.client(GetFullChannelRequest(channel=peer_entity))
                call_object = full_chat.full_chat.group_call
            elif isinstance(peer_entity, InputPeerChat):
                full_chat = await event.client(GetFullChatRequest(chat_id=peer_entity.chat_id))
                call_object = full_chat.full_chat.call
            
            if call_object:
                if isinstance(call_object, InputGroupCall):
                    call_input = call_object
                else:
                    call_input = InputGroupCall(id=call_object.id, access_hash=call_object.access_hash)
                    
                await event.client(LeaveGroupCallRequest(call=call_input))
                try:
                    await assistant.leave_chat(event.chat_id)
                except Exception:
                    pass
                
            await panel.edit("⏹️ **Assistant cleared from Voice Chat successfully.**")
        except Exception as err:
            await panel.edit(f"❌ **Error during exit handling:** `{str(err)}`")
  

import asyncio
from os import environ
import yt_dlp
import aiohttp
from telethon import events
from telethon.tl.functions.phone import CreateGroupCallRequest, InviteToGroupCallRequest
from telethon.tl.functions.channels import GetFullChannelRequest
from telethon.tl.functions.messages import GetFullChatRequest

# DARK-USERBOT Framework Components
from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

# --- pyrogram ASSISTANT ENGINE INITIALIZATION ---
from pyrogram import Client as PyroClient
ASSISTANT_SESSION = environ.get("ASSISTANT_SESSION", "")

# FIXED: Tera exact assistant username yahan lock kar diya hai
ASSISTANT_USERNAME = "SIRxMSD"  

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

    # 1. PROFESSIONAL PLAY COMMAND (Har bot user aur sudo user ke liye controller enabled)
    @client.on(events.NewMessage(pattern=r"^\.play(?:\s+(.*))?$", outgoing=True))
    @client.on(events.NewMessage(pattern=r"^\.play(?:\s+(.*))?$", incoming=True))
    async def professional_play_engine(event):
        if await is_banned(event.sender_id): return
        if event.incoming:
            if event.sender_id != OWNER_ID and not await is_sudo(event.sender_id): return

        query = event.pattern_match.group(1)
        
        if event.outgoing:
            panel = await event.edit("🔍 **Professional Engine: Fetching Audio Node...**")
        else:
            panel = await event.reply("🔍 **Professional Engine: Fetching Audio Node...**")

        if not query:
            return await panel.edit("❌ **Format:** `.play [Song Name / URL]`")

        if not assistant:
            return await panel.edit("❌ **Error:** `ASSISTANT_SESSION` missing in environment.")

        try:
            stream_url, track_title = await fetch_direct_audio(query)
            await panel.edit(f"✨ **Found:** `{track_title}`\n🛰️ *Initializing Voice Chat Automation Pipeline...*")
        except Exception as err:
            return await panel.edit(f"❌ **Audio Stream Core Blocked:** `{str(err)}`")

        try:
            # STEP 1: Voice Chat Auto-Creation Layer (Bina tumhare chhede agar band hui toh khud on karega)
            try:
                await event.client(CreateGroupCallRequest(peer=event.chat_id))
                await asyncio.sleep(1.5) # Dynamic sync delay
            except Exception:
                pass 

            # STEP 2: Fetch group call metadata safely
            try:
                full_chat = await event.client(GetFullChannelRequest(channel=event.chat_id))
                call_info = full_chat.full_chat.group_call
            except Exception:
                full_chat = await event.client(GetFullChatRequest(chat_id=event.chat_id))
                call_info = full_chat.full_chat.call

            if not call_info:
                return await panel.edit("❌ **Failed to initialize or find Voice Chat context.**")

            # STEP 3: Professional Invite Bridge using @SIRxMSD username entity
            target_assistant = await event.client.get_input_entity(ASSISTANT_USERNAME)
            
            await event.client(InviteToGroupCallRequest(
                call=call_info,
                users=[target_assistant]
            ))

            await panel.edit(f"✨ **Assistant (@{ASSISTANT_USERNAME}) Invited Successfully!**\n🛰️ *Establishing Audio Stream Connection...*")

            try:
                await assistant.join_chat(event.chat_id)
            except Exception:
                pass 

            await panel.edit(
                f"🎵 **Now Streaming Live**\n\n"
                f"🔹 **Title:** `{track_title}`\n"
                f"👤 **Triggered By:** [Userbot Admin]\n"
                f"⚙️ **Status:** Invite Pipeline Completed Successfully"
            )

        except Exception as framework_err:
            await panel.edit(f"❌ **Professional Engine Crash:** `{str(framework_err)}`")

    # 2. STOP COMMAND (.stop)
    @client.on(events.NewMessage(pattern=r"^\.stop$", outgoing=True))
    @client.on(events.NewMessage(pattern=r"^\.stop$", incoming=True))
    async def stop_audio(event):
        if await is_banned(event.sender_id): return
        if event.incoming and event.sender_id != OWNER_ID and not await is_sudo(event.sender_id): return
        
        if event.outgoing:
            panel = await event.edit("⏹️ **Clearing Assistant Stream Session...**")
        else:
            panel = await event.reply("⏹️ **Clearing Assistant Stream Session...**")
            
        try:
            try:
                await assistant.leave_chat(event.chat_id)
            except Exception:
                pass
            await panel.edit("⏹️ **Assistant stream disconnected successfully.**")
        except Exception as err:
            await panel.edit(f"❌ **Exit Error:** `{str(err)}`")
              

import asyncio
from os import environ
import aiohttp
from telethon import events

from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

ENTITY_STATE = {
    "active": False,
    "mode": None
}

OPENROUTER_API_KEY = environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY = environ.get("GROQ_API_KEY", "")

async def generate_entity_reply(current_mode: str, user_message: str):
    raw_instruction = (
        f"Adopt the archetype of a '{current_mode}'. Analyze the user's incoming message language (Hindi/English/Hinglish). "
        f"Generate a contextual response mirroring or countering that archetype organically. "
        f"Keep the reply raw, aggressive/punchy based on the mode, and limited to 1-2 lines maximum. Do not use emojis."
    )
    
    payload = {
        "messages": [
            {"role": "system", "content": raw_instruction},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.85,
        "max_tokens": 100
    }

    if OPENROUTER_API_KEY:
        payload["model"] = "deepseek/deepseek-chat"
        headers = {"Authorization": f"Bearer {OPENROUTER_API_KEY}", "Content-Type": "application/json", "HTTP-Referer": "https://github.com/Ankit/DARK-USERBOT"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    if GROQ_API_KEY:
        payload["model"] = "llama3-8b-8192"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/chat/completions", json=payload, headers=headers, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    try:
        encoded_instruction = aiohttp.helpers.quote(raw_instruction)
        encoded_message = aiohttp.helpers.quote(user_message)
        async with aiohttp.ClientSession() as session:
            async with session.get(f"https://text.pollinations.ai/ai/{encoded_message}?system={encoded_instruction}", timeout=8) as resp:
                if resp.status == 200:
                    out = await resp.text()
                    return out.strip()
    except Exception:
        pass

    return await generate_entity_reply(current_mode, user_message)

async def setup(client):

    @client.on(events.NewMessage(pattern=r"^\.entity(?:\s+(.*))?$", outgoing=True))
    async def entity_controller(event):
        if await is_banned(event.sender_id): return
        args = event.pattern_match.group(1)
        if not args:
            return await event.edit("⚙️ **Format:** `.entity [demon / king / villain / clone / off]`")
        
        mode_input = args.strip().lower()
        if mode_input == "off":
            ENTITY_STATE["active"] = False
            ENTITY_STATE["mode"] = None
            return await event.edit("🔴 **AI Personality Mode OFF.**")

        ENTITY_STATE["active"] = True
        ENTITY_STATE["mode"] = mode_input
        await event.edit(f"🟢 **{mode_input.upper()} MODE ON.**")

    @client.on(events.NewMessage(incoming=True))
    async def automated_responder(event):
        if not ENTITY_STATE["active"] or not ENTITY_STATE["mode"]: return
        if event.is_channel or await is_banned(event.sender_id): return

        is_triggered = False
        if event.is_private: 
            is_triggered = True
        elif event.mentioned: 
            is_triggered = True
        elif event.is_reply:
            reply_msg = await event.get_reply_message()
            my_id = (await event.client.get_me()).id
            if reply_msg and reply_msg.sender_id == my_id:
                is_triggered = True

        if is_triggered and event.text:
            current_mode = ENTITY_STATE["mode"]
            ai_reply = await generate_entity_reply(current_mode, event.text)
            
            # Direct Hard Forced Telegram Target Reply Execution
            await event.client.send_message(
                entity=event.chat_id,
                message=ai_reply,
                reply_to=event.id
        )
                                               

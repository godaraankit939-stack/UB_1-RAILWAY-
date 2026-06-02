import asyncio
from os import environ
import aiohttp
from telethon import events

# DARK-USERBOT Framework Base Connectors
from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

# --- RUNTIME MEMORY STATE ---
ENTITY_STATE = {
    "active": False,
    "mode": None  # demon, king, villain, clone
}

# --- AI API CREDENTIALS ---
OPENROUTER_API_KEY = environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY = environ.get("GROQ_API_KEY", "")

# --- MULTI-TIER PURE AI GENERATOR ENGINE ---
async def generate_entity_reply(current_mode: str, user_message: str):
    # Dynamic zero-text runtime instruction stream
    raw_instruction = (
        f"Adopt the archetype of a '{current_mode}'. Analyze the user's incoming message language "
        f"(Hindi/English/Hinglish), tone, and aggression. Generate a contextual response mirroring "
        f"or countering that archetype organically, without adhering to any hardcoded rules or pre-set lines. "
        f"Keep the reply extremely short, raw, punchy, and direct (maximum 1-2 lines). Never use emojis."
    )
    
    payload = {
        "messages": [
            {"role": "system", "content": raw_instruction},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.85,
        "max_tokens": 100
    }

    # TIER 1: Premium OpenRouter Engine (DeepSeek V3 / Qwen)
    if OPENROUTER_API_KEY:
        payload["model"] = "deepseek/deepseek-chat"
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/Ankit/DARK-USERBOT"
        }
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://openrouter.ai/api/v1/chat/completions", json=payload, headers=headers, timeout=8) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    # TIER 2: Groq High-Speed Fallback Engine
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

    # TIER 3: Unstructured Public AI Gateway (Zero-Key Backup)
    try:
        encoded_instruction = aiohttp.helpers.quote(raw_instruction)
        encoded_message = aiohttp.helpers.quote(user_message)
        public_url = f"https://text.pollinations.ai/ai/{encoded_message}?system={encoded_instruction}"
        
        async with aiohttp.ClientSession() as session:
            async with session.get(public_url, timeout=8) as resp:
                if resp.status == 200:
                    raw_ai_out = await resp.text()
                    if raw_ai_out.strip():
                        return raw_ai_out.strip()
    except Exception:
        pass

    # Forced recovery routing to maintain continuous auto-replies
    return await generate_entity_reply(current_mode, user_message)


# --- DARK-USERBOT FRAMEWORK SETUP FUNCTION ---

async def setup(client):

    # 1. BOT CONTROLLER (Sirf tu chalaega mode badalne ya off karne ke liye)
    @client.on(events.NewMessage(pattern=r"^\.entity(?:\s+(.*))?$", outgoing=True))
    async def entity_controller(event):
        if await is_banned(event.sender_id):
            return
        
        args = event.pattern_match.group(1)
        if not args:
            await event.edit("⚙️ **Format:** `.entity [demon / king / villain / clone / off]`")
            return

        mode_input = args.strip().lower()

        if mode_input == "off":
            ENTITY_STATE["active"] = False
            ENTITY_STATE["mode"] = None
            await event.edit("🔴 **AI Entity Personality Mode has been turned OFF.**")
            return

        ENTITY_STATE["active"] = True
        ENTITY_STATE["mode"] = mode_input
        await event.edit(f"🟢 **AI Personality Activated:** `{mode_input.upper()} MODE` ON.")


    # 2. AUTOMATED RESPONDER (Listens to normal user inputs: Replies, Tags, and DMs)
    @client.on(events.NewMessage(incoming=True))
    async def automated_responder(event):
        # Jab tak tune koi mode ON nahi kiya, tab tak code silent rahega
        if not ENTITY_STATE["active"] or not ENTITY_STATE["mode"]:
            return
        if event.is_channel:
            return
        if await is_banned(event.sender_id):
            return

        is_triggered = False
        
        # Interception layer for normal messages:
        if event.is_private:  # Saamne wale ne DM kiya
            is_triggered = True
        elif event.mentioned:  # Saamne wale ne group me sirf tag kiya
            is_triggered = True
        elif event.is_reply:  # Saamne wale ne tere message par reply kiya
            reply_msg = await event.get_reply_message()
            my_id = (await event.client.get_me()).id
            if reply_msg and reply_msg.sender_id == my_id:
                is_triggered = True

        # Agar trigger pipeline true hai, toh direct user ke message ke reply me response phekega
        if is_triggered:
            user_text = event.text
            if not user_text:
                return # Ignore media/stickers text logs
                
            current_mode = ENTITY_STATE["mode"]
            ai_reply = await generate_entity_reply(current_mode, user_text)
            
            # Direct target message coordinate reply injection
            await event.reply(ai_reply)
          

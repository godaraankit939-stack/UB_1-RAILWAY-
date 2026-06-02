import asyncio
from os import environ
import aiohttp
from telethon import events

# DARK-USERBOT Framework Connectors
from database import get_maintenance, is_sudo, is_banned
from config import OWNER_ID

# --- RUNTIME MEMORY ALLOCATION ---
ENTITY_STATE = {
    "active": False,
    "mode": None  # demon, king, villain, clone
}

# --- FETCH ENVIRONMENT VARIABLES ---
OPENROUTER_API_KEY = environ.get("OPENROUTER_API_KEY", "")
GROQ_API_KEY = environ.get("GROQ_API_KEY", "")

# --- MULTI-TIER PURE AI GENERATOR ENGINE ---
async def generate_entity_reply(current_mode: str, user_message: str):
    # 100% Fluid Instruction: No static strings allowed.
    raw_instruction = (
        f"Adopt the archetype of a '{current_mode}'. Analyze the user's message language "
        f"(Hindi/English/Hinglish), tone, and aggression. Generate a contextual response mirroring "
        f"or countering that archetype organically, without adhering to any hardcoded rules or pre-set lines."
    )
    
    payload = {
        "messages": [
            {"role": "system", "content": raw_instruction},
            {"role": "user", "content": user_message}
        ],
        "temperature": 0.85,
        "max_tokens": 120
    }

    # TIER 1: OpenRouter Premium (DeepSeek V3 / Qwen)
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

    # TIER 2: Groq High-Speed Fallback (Llama 3)
    if GROQ_API_KEY:
        payload["model"] = "llama3-8b-8192"
        headers = {"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post("https://api.groq.com/openai/v1/v1/chat/completions", json=payload, headers=headers, timeout=6) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        return data['choices'][0]['message']['content'].strip()
        except Exception:
            pass

    # TIER 3: Unstructured Open Source Gateway (Zero-Key Backup)
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

    # Infinite AI routing fallback to prevent empty or static returns
    return await generate_entity_reply(current_mode, user_message)

# --- DARK-USERBOT FRAMEWORK INJECTION POINT ---

async def setup(client):

    # 1. THE CONTROLLER (.entity [mode/off])
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

        # Completely fluid entry: Directly mounts whatever string input is provided
        ENTITY_STATE["active"] = True
        ENTITY_STATE["mode"] = mode_input
        await event.edit(f"🟢 **AI Personality Activated:** `{mode_input.upper()} MODE` ON.")

    # 2. THE BACKGROUND AUTOMATION RESPONDER (Triggers on DM, Mention, and Reply)
    @client.on(events.NewMessage(incoming=True))
    async def automated_responder(event):
        if not ENTITY_STATE["active"] or not ENTITY_STATE["mode"]:
            return
        
        if event.is_channel:
            return
            
        if await is_banned(event.sender_id):
            return

        is_triggered = False
        
        # Interception Matrix:
        if event.is_private:  # 1. Direct Inbox DM
            is_triggered = True
        elif event.mentioned:  # 2. Tagged/Mentioned in Groups
            is_triggered = True
        elif event.is_reply:  # 3. Someone replies to your message
            reply_msg = await event.get_reply_message()
            if reply_msg and reply_msg.sender_id == (await event.client.get_me()).id:
                is_triggered = True

        if is_triggered:
            user_text = event.text
            if not user_text:
                return  # Skip media/stickers logs with no text strings
                
            current_mode = ENTITY_STATE["mode"]
            ai_reply = await generate_entity_reply(current_mode, user_text)
            await event.reply(ai_reply)
      

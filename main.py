from telethon import TelegramClient, events
from telethon.sessions import StringSession
import asyncio

# ========== CONFIG ==========
STRING_SESSION = '1BVtsOHgBuwz81Gpdu_OrzLFbEan8_QF2iP5EWy5K8iPkHz1lFWooNpcYum30kSi1JnDGbFgksHxm4Qeopxo7WyL6Ap-JigFe7K2iusTJmC_vK73YArSBdKUlKYeW6S_npL5OVjmyvkPAFX43WsTBrIMCgEG2FUMwUtnLR7KgOG2iRNmdphxabQ0Av7ImuLZAiwovviR44yIcJXhOJqz2n9yjA8bjGbVFRG64wsWvBIt7nnW_oQp7p_HVT7PyjUyNJOvMa9mXUWhOz5ntEvMGBjNdoK32mcnoJUboihG0Jd6q6pN0y1cFFb8pM2eCezFleCDgDZXW0Re_QWW7EiW991ZXqQ2WNJE='
API_ID = 25897592
API_HASH = '94e48115fc78c3eeca61a4561443f1ef'
# ============================

client = TelegramClient(StringSession(STRING_SESSION), API_ID, API_HASH)

bot_entity = None
sticker_msg_id = None
heyyy_msg_id = None
f_msg_id = None

match_active = False
promo_sent = False
sending_lock = asyncio.Lock()
promo_cancelled = False
finding_lock = asyncio.Lock()
stop_pending = False  # NEW: prevents duplicate /stop sends


async def find_sticker():
    global sticker_msg_id, heyyy_msg_id, f_msg_id
    try:
        msgs = await client.get_messages('me', limit=50)
        for m in msgs:
            if m.sticker and not sticker_msg_id:
                sticker_msg_id = m.id
                print("[+] Sticker found!")
            if m.text and m.text.lower() == 'heyyy' and not heyyy_msg_id:
                heyyy_msg_id = m.id
                print("[+] 'heyyy' message found!")
            if m.text and m.text.upper() == 'F' and not f_msg_id:
                f_msg_id = m.id
                print("[+] 'F' message found!")
        
        if all([sticker_msg_id, heyyy_msg_id, f_msg_id]):
            return True
            
    except Exception as e:
        print(f"[!] Find error: {e}")
    
    print("[!] Send 'heyyy', 'F', and sticker to Saved Messages first!")
    return False


async def click_find_partner():
    global match_active, promo_sent, promo_cancelled, stop_pending
    
    if finding_lock.locked():
        print("[*] Already finding partner, skipping...")
        return True
    
    async with finding_lock:
        print("[*] Looking for Find a Partner button...")
        
        try:
            for attempt in range(3):
                msgs = await client.get_messages(bot_entity, limit=5)
                for m in msgs:
                    if not m.reply_markup:
                        continue
                    for row in m.reply_markup.rows:
                        for btn in row.buttons:
                            btn_text = btn.text or ''
                            if 'Find a Partner' in btn_text or 'Find' in btn_text:
                                try:
                                    await m.click(text=btn.text)
                                    print(f"[→] Find a Partner clicked (attempt {attempt+1})")
                                    match_active = False
                                    promo_sent = False
                                    promo_cancelled = False
                                    stop_pending = False
                                    await asyncio.sleep(3)
                                    return True
                                except Exception as click_err:
                                    print(f"[!] Click error: {click_err}")
                                    continue
                
                if attempt < 2:
                    print(f"[*] Button not found, waiting... (attempt {attempt+1})")
                    await asyncio.sleep(2)
            
            print("[!] Button not found, using /search fallback")
            await client.send_message(bot_entity, '/search')
            match_active = False
            promo_sent = False
            promo_cancelled = False
            stop_pending = False
            await asyncio.sleep(3)
            return True
            
        except Exception as e:
            print(f"[!] Find partner error: {e}")
            match_active = False
            promo_sent = False
            promo_cancelled = False
            stop_pending = False
            await asyncio.sleep(3)
            return True


async def send_stop_and_find():
    global match_active, promo_sent, promo_cancelled, stop_pending
    
    # NEW: Don't send /stop if partner already ended or we already sent it
    if not stop_pending:
        try:
            await client.send_message(bot_entity, '/stop')
            print("[→] /stop sent")
            stop_pending = True
            await asyncio.sleep(3)
        except Exception as e:
            print(f"[!] Stop error: {e}")
    
    await click_find_partner()


async def send_promo():
    global promo_sent, promo_cancelled
    
    if sending_lock.locked() or promo_sent:
        print("[*] Already sending or already sent, skipping...")
        return
    
    async with sending_lock:
        promo_cancelled = False
        print("[*] Starting forward sequence...")
        
        try:
            if promo_cancelled:
                print("[!] Promo cancelled before heyyy")
                return
                
            if heyyy_msg_id:
                await client.forward_messages(bot_entity, heyyy_msg_id, 'me')
                print("[+] Forwarded: heyyy")
            else:
                await client.send_message(bot_entity, "heyyy")
                print("[+] Sent: heyyy")
            
            await asyncio.sleep(3)
            
            if promo_cancelled:
                print("[!] Promo cancelled before F")
                return
                
            if f_msg_id:
                await client.forward_messages(bot_entity, f_msg_id, 'me')
                print("[+] Forwarded: F")
            else:
                await client.send_message(bot_entity, "F")
                print("[+] Sent: F")
            
            await asyncio.sleep(3)
            
            if promo_cancelled:
                print("[!] Promo cancelled before sticker")
                return
                
            if sticker_msg_id:
                await client.forward_messages(bot_entity, sticker_msg_id, 'me')
                print("[+] Sticker forwarded!")
            else:
                await client.send_message(bot_entity, "💜 @chatxbt_bot\nhttps://t.me/chatxbt_bot")
                print("[+] Text promo sent!")
            
            promo_sent = True
            await asyncio.sleep(3)
            
        except Exception as e:
            print(f"[!] Send error: {e}")
            promo_sent = False


@client.on(events.NewMessage(chats='@Anonymouslyrobot'))
async def handler(event):
    global match_active, promo_sent, promo_cancelled, stop_pending
    
    text = event.text or ''
    
    if event.out:
        return
    
    # ========== PARTNER ENDED CHAT ==========
    if 'Your partner ended the chat' in text:
        print("[✓] Partner ended chat")
        
        # Cancel ongoing promo if active
        if sending_lock.locked() and not promo_sent:
            print("[!] Cancelling promo...")
            promo_cancelled = True
        
        match_active = False
        promo_sent = False
        stop_pending = False  # Partner ended it, no need for /stop
        
        # CRITICAL FIX: Wait for send_promo() to finish releasing the lock
        # before trying to find a new partner
        if sending_lock.locked():
            print("[*] Waiting for promo to cancel...")
            # Spin briefly until lock releases
            for _ in range(30):  # max 3 seconds
                if not sending_lock.locked():
                    break
                await asyncio.sleep(0.1)
        
        await asyncio.sleep(2)
        await click_find_partner()
        return
    
    # ========== WE LEFT CHAT ==========
    if 'You left the chat' in text:
        print("[✓] We left the chat")
        match_active = False
        promo_sent = False
        stop_pending = False
        await asyncio.sleep(2)
        await click_find_partner()
        return
    
    # ========== BOT WELCOME / MENU ==========
    if "I'm an anonymous chat bot" in text:
        print("[*] Bot welcome/menu shown")
        if not match_active and not finding_lock.locked():
            await asyncio.sleep(1)
            await click_find_partner()
        return
    
    # ========== FINDING PARTNER ==========
    if 'Finding a partner soon' in text:
        print("[...] Searching for partner...")
        match_active = False
        promo_sent = False
        stop_pending = False
        return
    
    # ========== MATCH STARTED ==========
    if 'Start chatting' in text:
        print("[+] Match started!")
        match_active = True
        promo_sent = False
        promo_cancelled = False
        stop_pending = False
        
        await asyncio.sleep(1)
        await send_promo()
        
        if not promo_cancelled:
            await send_stop_and_find()
        else:
            print("[!] Promo cancelled, cleaning up...")
            await asyncio.sleep(1)
            await click_find_partner()
        return
    
    # ========== PARTNER SENT MESSAGE DURING MATCH ==========
    if match_active and not sending_lock.locked():
        if promo_sent:
            print("[!] Partner messaging after promo! Skipping...")
            await send_stop_and_find()
            return
        
        print("[+] Partner sent message/sticker!")
        await send_promo()
        if not promo_cancelled:
            await send_stop_and_find()
        else:
            print("[!] Promo cancelled, finding next...")
            await asyncio.sleep(1)
            await click_find_partner()
        return


async def main():
    global bot_entity
    await client.start()
    print("[*] xbt1-bot (Anonymouslyrobot) started!")
    
    bot_entity = await client.get_entity('@Anonymouslyrobot')
    await find_sticker()
    await click_find_partner()
    
    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())

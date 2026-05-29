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
hi_msg_id = None
f_msg_id = None
match_active = False
promo_sent = False
sending_lock = False


async def find_sticker():
    global sticker_msg_id, hi_msg_id, f_msg_id
    try:
        msgs = await client.get_messages('me', limit=50)
        for m in msgs:
            if m.sticker:
                sticker_msg_id = m.id
                print("[+] Sticker found!")
            if m.text and m.text.lower() == 'hi':
                hi_msg_id = m.id
                print("[+] 'hi' message found!")
            if m.text and m.text.upper() == 'F':
                f_msg_id = m.id
                print("[+] 'F' message found!")

        if sticker_msg_id and hi_msg_id and f_msg_id:
            return True

    except Exception as e:
        print(f"[!] Find error: {e}")

    print("[!] Send 'hi', 'F', and sticker to Saved Messages first!")
    return False


async def click_find_partner():
    """Click the '⚡ Find a Partner' inline button after /stop."""
    global match_active, promo_sent
    try:
        msgs = await client.get_messages(bot_entity, limit=5)
        for m in msgs:
            if m.reply_markup:
                for row in m.reply_markup.rows:
                    for btn in row.buttons:
                        if 'Find a Partner' in btn.text or 'Find' in btn.text:
                            try:
                                await m.click(text=btn.text)
                                print("[→] Find a Partner clicked")
                                match_active = False
                                promo_sent = False
                                return True
                            except:
                                continue
    except Exception as e:
        print(f"[!] get_messages error: {e}")

    try:
        await client.send_message(bot_entity, '/start')
        print("[→] /start sent (fallback)")
    except Exception as e:
        print(f"[!] Fallback error: {e}")

    match_active = False
    promo_sent = False
    return True


async def send_stop_and_next():
    """Send /stop, wait for menu, then click Find a Partner."""
    global match_active, promo_sent
    try:
        await client.send_message(bot_entity, '/stop')
        print("[→] /stop sent")
        # Wait for the bot to show the menu with Find a Partner button
        await asyncio.sleep(2)
        await click_find_partner()
    except Exception as e:
        print(f"[!] Stop/Next error: {e}")
        match_active = False
        promo_sent = False


async def send_promo():
    global promo_sent, sending_lock

    if sending_lock or promo_sent:
        print("[*] Already sending or already sent, skipping...")
        return

    sending_lock = True
    print("[*] Starting forward sequence...")

    try:
        # Step 1: Forward "hi"
        if hi_msg_id:
            await client.forward_messages(bot_entity, hi_msg_id, 'me')
            print("[+] Forwarded: hi")
        else:
            await client.send_message(bot_entity, "hi")
            print("[+] Sent: hi")

        # Wait 4 seconds
        await asyncio.sleep(4)

        # Step 2: Forward "F"
        if f_msg_id:
            await client.forward_messages(bot_entity, f_msg_id, 'me')
            print("[+] Forwarded: F")
        else:
            await client.send_message(bot_entity, "F")
            print("[+] Sent: F")

        # Wait 6 seconds before sticker
        await asyncio.sleep(6)

        # Step 3: Forward sticker
        if sticker_msg_id:
            await client.forward_messages(bot_entity, sticker_msg_id, 'me')
            print("[+] Sticker forwarded!")
        else:
            await client.send_message(bot_entity, "💜 @chatxbt_bot\nhttps://t.me/chatxbt_bot")
            print("[+] Text promo sent!")

        promo_sent = True

        # Wait 4 seconds before stop/next
        await asyncio.sleep(4)

    except Exception as e:
        print(f"[!] Send error: {e}")

    finally:
        sending_lock = False


@client.on(events.NewMessage(chats='@Anonymouslyrobot'))
async def handler(event):
    global match_active, promo_sent, sending_lock
    text = event.text or ''

    if sending_lock:
        print("[*] Currently sending, ignoring new message...")
        return

    if 'Start chatting' in text:
        print("[+] Match started!")
        match_active = True
        promo_sent = False
        await asyncio.sleep(1)
        await send_promo()
        await send_stop_and_next()
        return

    if 'Finding a partner soon' in text:
        print("[...] Searching...")
        match_active = False
        promo_sent = False
        return

    if 'You left the chat' in text:
        print("[✓] Chat ended, waiting for menu...")
        match_active = False
        promo_sent = False
        await asyncio.sleep(1)
        await click_find_partner()
        return

    if match_active and not event.out and not promo_sent and not sending_lock:
        print("[+] Partner messaged first!")
        await send_promo()
        await send_stop_and_next()


async def main():
    global bot_entity
    await client.start()
    print("[*] xbt1-bot (Anonymouslyrobot) started!")

    bot_entity = await client.get_entity('@Anonymouslyrobot')
    await find_sticker()

    # Start by clicking Find a Partner
    await click_find_partner()

    await client.run_until_disconnected()


with client:
    client.loop.run_until_complete(main())

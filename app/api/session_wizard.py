import os
import uuid
from fastapi import APIRouter, HTTPException, Body
from telethon import TelegramClient
from telethon.sessions import StringSession

# Temporary storage for Telegram session files
TMP_DIR = '/tmp/telegram_sessions'
os.makedirs(TMP_DIR, exist_ok=True)

# Router for Telegram session wizard endpoints
router = APIRouter()

@router.post('/session/start')
async def start_session(data: dict = Body(...)):
    phone = data.get('phone')
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    # Validate required inputs for sending the login code
    if not phone or not api_id or not api_hash:
        raise HTTPException(status_code=400, detail='Numéro/API_ID/API_HASH manquant')
    session_id = str(uuid.uuid4())
    session_path = os.path.join(TMP_DIR, session_id)
    # Use a file-backed session for the verification step
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    try:
        sent = await client.send_code_request(phone)
        # Store phone_code_hash for the verify step
        hash_path = session_path + '.hash'
        with open(hash_path, 'w') as f:
            f.write(sent.phone_code_hash)
    except Exception as e:
        await client.disconnect()
        raise HTTPException(status_code=500, detail=f'Erreur envoi code: {e}')
    await client.disconnect()
    return {'session_id': session_id}

@router.post('/session/verify')
async def verify_code(data: dict = Body(...)):
    session_id = data.get('session_id')
    phone = data.get('phone')
    code = data.get('code')
    api_id = os.getenv('TELEGRAM_API_ID')
    api_hash = os.getenv('TELEGRAM_API_HASH')
    # Validate required inputs for verifying the code
    if not session_id or not phone or not code:
        raise HTTPException(status_code=400, detail='Paramètres manquants')
    session_path = os.path.join(TMP_DIR, session_id)
    # Use file session to sign in, then transfer to StringSession for export
    client = TelegramClient(session_path, api_id, api_hash)
    await client.connect()
    import traceback
    hash_path = session_path + '.hash'
    try:
        with open(hash_path, 'r') as f:
            phone_code_hash = f.read().strip()
    except Exception:
        await client.disconnect()
        raise HTTPException(status_code=500, detail='phone_code_hash introuvable')
    try:
        await client.sign_in(phone, code, phone_code_hash=phone_code_hash)
        # Now export session string
        string_session = StringSession.save(client.session)
    except Exception as e:
        await client.disconnect()
        print('--- ERREUR SESSION VERIFY ---')
        print(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f'Erreur validation code: {e}')
    await client.disconnect()
    # Clean up temporary files
    try:
        os.remove(session_path + '.session')
    except Exception:
        pass
    try:
        os.remove(hash_path)
    except Exception:
        pass
    return {'session_string': string_session}

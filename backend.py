from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import whisper
import openai
import json
import re
from db_tools import Conversation  # assuming this is your class
from fastapi import Request
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from db_tools import get_db
from db_tools import User, oauth2_scheme, decode_token, engine
import os

#from .database import get_db
#from .models import User

router = APIRouter()



@router.post("/upload-audio")
async def handle_audio(file: UploadFile, request: Request):
    whisper_model = request.app.state.whisper_model
    convo = request.app.state.convo

    # Save uploaded audio to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Transcribe
    transcription = whisper_model.transcribe(tmp_path)["text"]

    print("Transcription: ", transcription)

    # Use GPT to get assistant reply (non-streaming version for clean separation)
    convo.query_gpt4(transcription)  # prints the assistant output
    assistant_reply = convo.conversation_history[-1]["content"]

    async def audio_stream():
        yield (json.dumps({"text": assistant_reply}) + "\n").encode("utf-8")

        with openai.audio.speech.with_streaming_response.create(
            model="tts-1",
            voice="nova",
            input=assistant_reply
        ) as response:
            for chunk in response.iter_bytes(chunk_size=1024):
                yield chunk


    return StreamingResponse(audio_stream(), media_type="application/octet-stream")

PROMPT_SENTINEL = '''
You are a native Spanish speaker helping a user practice Spanish conversation. Always reply to the user in Spanish.

Also, you are tracking the user's grammar and spelling mistakes in a scratchpad. After each user input, silently write any grammar or spelling mistakes you detect — in English — to this scratchpad. 

Respond in the following format:

[Your full Spanish response to the user goes here — no JSON, no quotes.]

@@@END_OF_ASSISTANT@@@

scratchpad_update: [Any grammar or spelling issues here, in English.]

Only include the scratchpad_update line after the marker. Do not include the marker in the Spanish reply. Do not say anything else outside this format.
'''

@router.post("/transcribe-audio")
async def transcribe_audio(file: UploadFile, request: Request):
    whisper_model = request.app.state.whisper_model

    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    transcription = whisper_model.transcribe(tmp_path)["text"]
    return {"text": transcription}

@router.post("/continue-chat")
async def continue_chat(request: Request, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    print('payload attempted')
    payload = decode_token(token)
    print('payload achieved')
    username = payload.get("sub")
    convo_id = payload['convo_id']

    user = db.query(User).filter_by(username=username).first()
    convo = db.query(Conversation).filter_by(id=convo_id, user_id=user.id).first()

    client = openai.OpenAI(api_key = os.environ['OPENAI_KEY'])

    data = await request.json()
    user_input = data["text"]

    buffer = ""
    assistant_text = ""
    scratchpad_text = ""
    in_scratchpad = False
    all_text = ""
    scratchpad_update = None

    def stream_generator():
        nonlocal buffer, assistant_text, scratchpad_text, in_scratchpad, all_text, scratchpad_update


        system_prompt = PROMPT_SENTINEL
        messages = [{"role": "system", "content": system_prompt}] + convo.conversation_history
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            stream=True
        )

        

        for chunk in stream:
            delta = chunk.choices[0].delta
            content = delta.content if delta.content else ""
            #print(content)
            if not content:
                continue

            all_text += content
            buffer += content

            if "@@@END_OF_ASSISTANT@@@" in buffer:
                before, after = buffer.split("@@@END_OF_ASSISTANT@@@", 1)
                assistant_text = before
                in_scratchpad = True
                scratchpad_text += after
                buffer = ""
                continue

            if in_scratchpad:
                scratchpad_text += content
            else:
                assistant_text += content
                if "@" not in buffer:
                    yield content.encode('utf-8')

        convo.conversation_history.append({"role": "user", "content": user_input})
        convo.conversation_history.append({"role": "assistant", "content": all_text.strip()})

        match = re.search(r'scratchpad_update:\s*(.*)', scratchpad_text)
        if match:
            scratchpad_update = match.group(1).strip()

            yield b'\n'  # flush buffer cleanly
            yield (json.dumps({"scratchpad_update": scratchpad_update}) + "\n").encode("utf-8")

    response = StreamingResponse(stream_generator(), media_type="text/plain")


    async def finalize():
        with Session(bind=engine) as session:
            convo = session.query(Conversation).filter_by(id=convo_id, user_id=user.id).first()
            convo.conversation_history.append({"role": "user", "content": user_input})
            convo.conversation_history.append({"role": "assistant", "content": all_text.strip()})

            if scratchpad_update:
                convo.scratchpad.append(f"User input: {user_input}\nError:{scratchpad_update}")

            session.commit()
            print("✅ Conversation saved")

    # Background task ensures DB commit occurs after streaming finishes
    from starlette.background import BackgroundTask
    response.background = BackgroundTask(finalize)


    return response


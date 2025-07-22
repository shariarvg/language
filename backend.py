from fastapi import FastAPI, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
import tempfile
import whisper
import openai
import json
import re
from basic_interact import Conversation  # assuming this is your class
from fastapi import Request

app = FastAPI()

# Allow local dev
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper and conversation handler
app.state.whisper_model = whisper.load_model("base")
app.state.convo = Conversation()

@app.post("/upload-audio")
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

conversation = Conversation()


@app.post("/stream-gpt")
async def stream_gpt(file: UploadFile, request: Request):
    whisper_model = request.app.state.whisper_model
    c = request.app.state.convo

    # Save uploaded audio to temp file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".webm") as tmp:
        tmp.write(await file.read())
        tmp_path = tmp.name

    # Transcribe
    user_input = whisper_model.transcribe(tmp_path)["text"]

    def stream_generator():
        system_prompt = PROMPT_SENTINEL
        messages = [{"role": "system", "content": system_prompt}] + conversation.conversation_history
        messages.append({"role": "user", "content": user_input})

        stream = conversation.client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            stream=True
        )

        buffer = ""
        assistant_text = ""
        scratchpad_text = ""
        in_scratchpad = False

        for chunk in stream:
            delta = chunk.choices[0].delta
            content = delta.content if delta.content else ""
            if not content:
                continue

            buffer += content

            if "@@@END_OF_ASSISTANT@@@" in buffer:
                before, after = buffer.split("@@@END_OF_ASSISTANT@@@", 1)
                assistant_text += before
                yield before
                in_scratchpad = True
                scratchpad_text += after
                buffer = ""
                continue

            if in_scratchpad:
                scratchpad_text += content
            else:
                assistant_text += content
                yield content

        conversation.conversation_history.append({"role": "user", "content": user_input})
        conversation.conversation_history.append({"role": "assistant", "content": assistant_text.strip()})

        match = re.search(r'scratchpad_update:\s*(.*)', scratchpad_text)
        if match:
            conversation.scratchpad.append(match.group(1).strip())

    return StreamingResponse(stream_generator(), media_type="text/plain")

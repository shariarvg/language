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

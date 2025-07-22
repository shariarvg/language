from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from basic_interact import Conversation
import re
import os

app = FastAPI()
conversation = Conversation()

@app.post("/stream-gpt")
async def stream_gpt(request: Request):
    body = await request.json()
    user_input = body.get("prompt", "")

    def stream_generator():
        system_prompt = conversation.PROMPT_SENTINEL
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

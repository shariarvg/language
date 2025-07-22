import openai
import time
import json
import re
import os

PROMPT = '''
You are a native Spanish speaker helping a user practice Spanish conversation. Always reply to the user in Spanish.

In addition, you are tracking the user's grammar and spelling mistakes. For each user input, write down any grammar or spelling errors you find in a scratchpad, in English. Store them without telling the user unless asked.

Reply to every user prompt in a JSON-decodeable dictionary format, with keys
- `assistant`: your Spanish response
- `scratchpad_update`: any grammar or spelling issues detected (if any)

When quoting titles or using quotation marks in your response, always escape double quotes (\") so the output is valid JSON.

e.g. input is 'A mí me gusta las bibliotecas' -> output: {"assistant": "A mí me gustan las bibliotecas también. ¿Cuál es tu libro favorito?'", "scratchpad_update":"Incorrectly uses \'me gusta\' when subject (bibliotecas) is plural."}

'''

PROMPT_SENTINEL = '''
You are a native Spanish speaker helping a user practice Spanish conversation. Always reply to the user in Spanish.

Also, you are tracking the user's grammar and spelling mistakes in a scratchpad. After each user input, silently write any grammar or spelling mistakes you detect — in English — to this scratchpad.

Respond in the following format:

[Your full Spanish response to the user goes here — no JSON, no quotes.]

@@@END_OF_ASSISTANT@@@

scratchpad_update: [Any grammar or spelling issues here, in English.]

Only include the scratchpad_update line after the marker. Do not include the marker in the Spanish reply. Do not say anything else outside this format.
'''

#with open("../../key.txt", 'r') as f:
#    api_key = f.read().strip()

api_key = os.environ['OPENAI_KEY']

openai.api_key = api_key
client = openai.OpenAI(api_key=api_key)

class Conversation():
    def __init__(self):   
        #self.assistant = client.beta.assistants.retrieve("asst_hwAATAQBmJMU6Xd8rIXfLjHB")
        #self.thread = client.beta.threads.create()
        self.scratchpad = []
        self.conversation_history = [] 
        self.client = openai.OpenAI(api_key=os.environ['OPENAI_KEY'])
        
    def extract_first_json_block(self, text):
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            json_str = match.group(0)
            return json.loads(json_str)
        else:
            print("Raw reply_content:\n", repr(text))
            raise ValueError("No JSON object found in response.")

    def query_gpt4(self, user_input):
        system_prompt = PROMPT  # From above
        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history
        messages.append({"role": "user", "content": user_input})
        
        response = client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7
        )

        # Parse response
        data = self.extract_first_json_block(response.choices[0].message.content)
        #data = json.loads(reply_content)
        

        # Update conversation and scratchpad
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": response.choices[0].message.content})

        if data.get("scratchpad_update"):
            self.scratchpad.append(data['scratchpad_update'])

        print(data['assistant'])
        
    def query_gpt4_streaming(self, user_input):
        system_prompt = PROMPT_SENTINEL
        messages = [{"role": "system", "content": system_prompt}] + self.conversation_history
        messages.append({"role": "user", "content": user_input})

        stream = client.chat.completions.create(
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
                # Split and mark the transition
                before, after = buffer.split("@@@END_OF_ASSISTANT@@@", 1)
                assistant_text += before
                print(before, end="", flush=True)
                in_scratchpad = True
                scratchpad_text += after
                buffer = ""
                continue

            if in_scratchpad:
                scratchpad_text += content
            else:
                assistant_text += content
                print(content, end="", flush=True)

        print()  # newline

        # Store in history and scratchpad
        self.conversation_history.append({"role": "user", "content": user_input})
        self.conversation_history.append({"role": "assistant", "content": assistant_text.strip()})

        try:
            match = re.search(r'scratchpad_update:\s*(.*)', scratchpad_text)
            if match:
                self.scratchpad.append(match.group(1).strip())
        except Exception as e:
            print("[!] Could not extract scratchpad_update:", e)

        
    def run(self):
        inp = input(" ")
        while inp != "quit":
            self.query_gpt4_streaming(inp)
            inp = input("\n")

The simplest and most effective way to practice a language is to have conversations. You can easily do
this with ChatGPT, but you don't get direct control over its persistent memory of your strengths and weaknesses,
and there's limited proactive functionality (e.g. like Duolingo reminding you of your past mistakes). I also wanted to try
my hand at another GPT Wrapper product since I've never worked on one.
:::

I have mixed feelings on Duolingo for learning languages; there is a huge number of features, which I think is crucial
for ensuring that learning doesn't get boring. But this product complexity also comes at a cost of user control over 
their learning experience; for example, when I wanted to practice saying basic Traditional Chinese phrases ahead of my
trip to Taiwan, I couldn't skip past Hànzì tracings, which weren't very useful to me. 

This is why I set out to make a conversation-first language tutor app. Admittedly, I wouldn't get much use out this
app for my Chinese ability, because I don't know enough Chinese to hold a steady conversation. This app is suited
for conversational speakers who want to gain practice. 

Some will ask: how is this app any different than just prompting ChatGPT to be your Spanish tutor? In both cases, you're
just prompting gpt-4 to be your Spanish tutor. I'll lay out a few differences, which I think are somewhat crucial.
 - As with any custom GPT wrapper, you get the benefit of providing your own system prompt, which for certain desired
 behaviors (e.g. correcting the user), allows for more consistent outcomes than if the chat tool is used
 - I wanted the freedom to customize my UI for practicing, differentiating from the ChatGPT interface that I already
 spend too many hours of my day looking at. Specifically, I wanted a separate page from my chat window that summarizes
 my mistakes, and I wanted a hidden container in each chat reply that displays corrections when I ask for them (but
 not when I don't... sometimes, I just want to keep the conversation going)
 - Overall, I do think that more complex functionalities can be useful when secondary to the conversation feature, 
 which should be the heart of any language-practice experience. Imagine if Duolingo's personalized features didn't
 just tailor practices to the mistakes you've made while using the app, but also the strengths and weaknesses you 
 exhibit in daily conversation. 

With this in mind, I set out to create a language app that was conversation-first and maintains persistent memory of user
 strengths and weaknesses. 

The app is built with FastAPI, Whisper, and OpenAI. It has a simple frontend with HTML, CSS, and JavaScript. The app is not currently hosted anywhere because I don't have a domain name, but you can run it locally with

`uvicorn main:app --reload --host 0.0.0.0 --port 8000`

In this README, I'll go over some of the source code in case anyone finds it interesting to look at when building their own GPT wrapper, since this was my first one. backend.py is probably the most useful place to look.

## Prompting

`PROMPT_SENTINEL = '''
You are a native Spanish speaker helping a user practice Spanish conversation. Always reply to the user in Spanish.

Also, you are tracking the user's grammar and spelling mistakes in a scratchpad. After each user input, silently write any grammar or spelling mistakes you detect — in English — to this scratchpad. 

Respond in the following format:

[Your full Spanish response to the user goes here — no JSON, no quotes.]

@@@END_OF_ASSISTANT@@@

scratchpad_update: [Any grammar or spelling issues here, in English.]

Only include the scratchpad_update line after the marker. Do not include the marker in the Spanish reply. Do not say anything else outside this format.
'''`
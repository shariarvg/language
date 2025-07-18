import openai

scratchpad = []

log_mistake_tool = {
    "type": "function",
    "function": {
        "name": "log_mistake_to_scratchpad",
        "description": "Logs a grammar or spelling mistake.",
        "parameters": {
            "type": "object",
            "properties": {
                "mistake": {
                    "type": "string",
                    "description": "The user's incorrect phrase or sentence."
                },
                "correction": {
                    "type": "string",
                    "description": "The corrected version of the phrase or sentence."
                },
                "explanation": {
                    "type": "string",
                    "description": "An explanation of the mistake."
                }
            },
            "required": ["mistake", "correction"]
        }
    }
}


assistant = openai.beta.assistants.create(
    name="Spanish Conversation Tutor",
    instructions=(
        "You are a Spanish tutor. Hold a conversation in Spanish with the user. "
        "When they make a grammar or spelling mistake, call the `log_mistake_to_scratchpad` function, "
        "but do not tell the user unless they ask to see their mistakes."
    ),
    model="gpt-4o",
    tools=[log_mistake_tool]
)

print("Assistant created, with ID:", assistant.id)
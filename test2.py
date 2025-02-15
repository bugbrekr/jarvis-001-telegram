import llm_utils

chat_model = llm_utils.LLM()

for chunk in chat_model.complete(
    [
        {"role": "user", "content": "hello!"},
        {"role": "assistant", "content": "Alright, the user greeted me with \"hello!\" so I should respond in a friendly and welcoming manner.\n\nI want to make sure they feel comfortable asking for help, so I'll keep it open-ended.\n\nMaybe I can offer my assistance by asking how I can help them today.\n\nKeeping it simple and approachable should work best.\n</think>\n\nHello! How can I assist you today?"},
        {"role": "tool", "content": "fuck you, just tell me what is 5+5"}
    ]
):
    print(chunk, end="", flush=True)
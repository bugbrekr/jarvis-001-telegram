from telethon import TelegramClient, events
import toml
import time
import functions
import tools
import llm_utils
import context_manager

with open("config/config.toml") as f:
    config = toml.loads(f.read())

API_ID = config["telegram"]["API_ID"]
API_HASH = config["telegram"]["API_HASH"]

client =  TelegramClient('sessions/account', API_ID, API_HASH)
bot_client = TelegramClient('sessions/bot', API_ID, API_HASH).start(bot_token=config["telegram"]["BOT_TOKEN"])

llm = llm_utils.LLM()

global_chat_history = {}
global_user_flags = {}

def _filter_incoming_messages(e):
    if not e.is_private: return False # only private chats
    if not e.out: # incoming
        if not e.from_id: return False
        if e.from_id.user_id == config["telegram"]["BOT_ID"]: return False # incoming from bot
        return not config["telegram"]["DEV_MODE"] # allow others to use when dev_mode is off
    elif e.out and e.peer_id.user_id==config["telegram"]["BOT_ID"]: # outgoing to bot
        return True

def _trunc(res, length=30):
    res = res.replace("\n", " ").strip()
    if len(res) > length:
        res = res[:length-3]+"..."
    return res

def _generate_toolcall_text(tool_call, res, trunc=True):
    params = ", ".join([k+"="+repr(_trunc(v, 10) if trunc else v) for k,v in tool_call["arguments"].items()])
    return f"{tool_call['name']}({params}): {_trunc(res) if trunc else res}"

def _generate_toolcall_text_for_tg(tool_call, res, trunc=True):
    res = _trunc(res) if trunc else res
    return f"`{tool_call['name']}`: `{res}`"

async def send_message(is_with_bot, event, message):
    message = message.strip()
    if is_with_bot:
        return await bot_client.send_message(event.from_id, message)
    else:
        return await client.send_message(event.peer_id, message)

async def edit_message(is_with_bot, event, message_id, updated_message):
    updated_message = updated_message.strip()
    if is_with_bot:
        return await bot_client.edit_message(event.from_id, message_id, updated_message)
    else:
        return await client.edit_message(event.peer_id, message_id, updated_message)

async def handle_jarvis(is_with_bot, event, chat_history, context:context_manager.Context):
    message_id = None
    thinking_dur = None
    async def output_started():
        nonlocal message_id
        if not message_id:
            message = await send_message(is_with_bot, event, "__thinking...__")
            message_id = message.id
        else:
            await edit_message(is_with_bot, event, message_id, response_message+"\n\n__Ran tools, thinking again...__")
    async def thinking_finished(thinking_response, dur):
        nonlocal thinking_dur
        nonlocal response_message
        thinking_dur = dur
        await edit_message(is_with_bot, event, message_id, response_message+f"__Finished thinking. Typing response...__")
        if response_message: response_message += "\n\n"
        response_message += f"__Thought for {functions.pretty_time_delta(thinking_dur)}.__\n\n"
        if not message_id: return
        print("\n[ASSISTANT]: ", end="", flush=True)
    async def intermediate_completion(incomplete_message):
        if not message_id or not thinking_dur: return
        await edit_message(is_with_bot, event, message_id, response_message+incomplete_message.strip()[:-1]+"\n\n__still typing, hold on...__")
    response_message = ""
    while True:
        response = await invoke_jarvis(
            chat_history,
            context,
            output_started,
            thinking_finished,
            intermediate_completion
        )
        current_message = response["message"]
        tool_calls = functions.parse_tool_calls(response["message"])
        if tool_calls:
            if message_id:
                await edit_message(is_with_bot, event, message_id, response_message+response["message"]+"\n\n__running tools now, hold on...__")
            needs_review = False
            for tool_call in tool_calls:
                if tool_call["name"] == "clear_context":
                    chat_history.clear()
                    return "Context cleared."
                res, success = tools.call_tool(tool_call["name"], tool_call["arguments"])
                tool_call["res"] = res
                tool_call["success"] = success
                print(f"[TOOL_CALL]: {_generate_toolcall_text(tool_call, res, False)}")
                if not success:
                    chat_history.append({"role": "tool", "content": res})
                    needs_review = True
            for tool_call in reversed(tool_calls):
                tool_call_text = f"**[TOOL CALL]**: {_generate_toolcall_text_for_tg(tool_call, tool_call['res'])}\n"
                current_message = current_message[:tool_call["span"][0]]+tool_call_text+current_message[tool_call["span"][1]:]
            if "|get_tool_response|" in current_message:
                current_message = current_message.replace("|get_tool_response|", "").rstrip()
                if tool_calls[-1]["success"]:
                    chat_history.append({"role": "tool", "content": res})
                    needs_review = True
            if needs_review:
                response_message += current_message
                continue
        response_message += current_message
        break
    if message_id:
        await edit_message(is_with_bot, event, message_id, response_message)
    else:
        await send_message(is_with_bot, event, response_message)    

async def invoke_jarvis(
        messages,
        context:context_manager.Context,
        output_started_func=None,
        thinking_finished_func=None,
        intermediate_completion_func=None
    ):
    system_prompt = llm_utils.prepare_system_prompt(tools.tool_definitions, context)
    messages_with_system = [{"role": "system", "content": system_prompt}]+messages
    started = False
    resp_message = ""
    print("[ ... ]: ", end="", flush=True)
    st = None
    finished_thinking = False
    thinking_reponse = ""
    for chunk in llm.complete(messages_with_system):
        if not started:
            started = True
            thinking_st = time.time()
            await output_started_func()
        resp_message += chunk
        print(chunk, end="", flush=True)
        if resp_message.endswith("</think>"):
            thinking_reponse = resp_message
            st = time.time()
            if thinking_finished_func: await thinking_finished_func(thinking_reponse, round(time.time()-thinking_st, 2))
            finished_thinking = True
            resp_message = ""
        if st:
            if time.time()-st > 3:
                await intermediate_completion_func(resp_message)
                st = time.time()
        if finished_thinking and "|get_tool_response|" in resp_message:
            break
    print()
    message = {"role": "assistant", "content": thinking_reponse+resp_message}
    messages.append(message)
    return {"thoughts": thinking_reponse, "message": resp_message.strip()}

@client.on(events.NewMessage(func=_filter_incoming_messages))
async def on_new_message(event:events.newmessage.NewMessage.Event):
    user_id = event.from_id.user_id
    message = event.text
    is_with_bot = event.out
    if not message: return
    if global_user_flags.get(user_id): return
    context = context_manager.Context(user_id)
    if context.first_time:
        await send_message(is_with_bot, event, config["jarvis-001"]["init_message_pre"]+config["jarvis-001"]["init_message"])
        global_chat_history[user_id] = [
            {"role": "user", "content": message},
            {"role": "assistant", "content": config["jarvis-001"]["init_message"]},
        ]
        context.first_time = False
        return
    user_data = await event.get_sender()
    context.identity = {
        "name": user_data.first_name+(" "+user_data.last_name if user_data.last_name else ""),
        "username": user_data.username
    }
    if message == "/clear":
        global_chat_history[user_id] = []
        await send_message(is_with_bot, event, "Context cleared.")
        return
    global_user_flags[user_id] = True
    chat_history = global_chat_history.get(user_id, [])
    chat_history.append({"role": "user", "content": message})
    print("[USER]: "+message)
    await handle_jarvis(is_with_bot, event, chat_history, context)
    global_chat_history[user_id] = chat_history
    global_user_flags[user_id] = False

if __name__ == "__main__":
    with client:
        client.run_until_disconnected()

import datetime 
import re
import json

def parse_tool_calls(message):
    matches = list(re.finditer(r'\|tool_call\|\s*(.*?)\s*\|/tool_call\|', message, re.DOTALL))
    tool_calls = []
    for match in matches:
        _tool_call = match.group(1)
        try:
            tool_call = json.loads(_tool_call)
        except json.JSONDecodeError:
            continue
        if isinstance(tool_call.get("name"), str) and (isinstance(tool_call.get("arguments"), dict) or isinstance(tool_call.get("parameters"), dict)):
            if isinstance(tool_call.get("arguments"), dict):
                tool_call["arguments"] = tool_call["parameters"]
                tool_call.pop("parameters")
            tool_call["span"] = match.span()
            tool_calls.append(tool_call)
    return tool_calls

def pretty_date(time):
    now = datetime.datetime.now()
    if type(time) is int:
        diff = now - datetime.datetime.fromtimestamp(time)
    elif isinstance(time, datetime):
        diff = now - time
    elif not time:
        diff = 0
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 10:
            return "just now"
        if second_diff < 60:
            return str(second_diff) + " seconds ago"
        if second_diff < 120:
            return "a minute ago"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes ago"
        if second_diff < 7200:
            return "an hour ago"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours ago"
    if day_diff == 1:
        return "Yesterday"
    if day_diff < 7:
        return str(day_diff) + " days ago"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks ago"
    if day_diff < 365:
        return str(day_diff // 30) + " months ago"
    return str(day_diff // 365) + " years ago"

def pretty_time_delta(dur):
    diff = datetime.timedelta(seconds=dur)
    second_diff = diff.seconds
    day_diff = diff.days

    if day_diff < 0:
        return ''

    if day_diff == 0:
        if second_diff < 30:
            return "a moment"
        if second_diff < 60:
            return str(second_diff) + " a minute"
        if second_diff < 120:
            return "more than a minute"
        if second_diff < 3600:
            return str(second_diff // 60) + " minutes"
        if second_diff < 7200:
            return "an hour"
        if second_diff < 86400:
            return str(second_diff // 3600) + " hours"
    if day_diff == 1:
        return "less than a day"
    if day_diff < 7:
        return str(day_diff) + " days"
    if day_diff < 31:
        return str(day_diff // 7) + " weeks"
    if day_diff < 365:
        return str(day_diff // 30) + " months"
    return str(day_diff // 365) + " years"

def _trunc(res, length=30):
    res = res.replace("\n", " ").strip()
    if len(res) > length:
        res = res[:length-3]+"..."
    return res

def _generate_toolcall_text(tool_call, res, trunc=True, for_tg=False):
    res = _trunc(res) if trunc else res
    if for_tg:
        return f"`{tool_call['name']}`: `{res}`"
    params = ", ".join([k+"="+repr(_trunc(v, 10) if trunc else v) for k,v in tool_call["arguments"].items()])
    return f"{tool_call['name']}({params}): {res}"

def format_assistant_message_for_display(message:str, tool_calls:list, trunc_toolcalls=True, for_tg=False):
    try: 
        message = message[message.index("</think>")+8:]
    except ValueError: 
        pass
    for tool_call in reversed(tool_calls):
        tool_call_text = f"**[TOOL CALL]**: {_generate_toolcall_text(tool_call, tool_call['res'], trunc_toolcalls, for_tg)}\n"
        message = message[:tool_call["span"][0]]+tool_call_text+message[tool_call["span"][1]:]
    if "|get_tool_response|" in message:
        message = message.replace("|get_tool_response|", "").rstrip()
    return message
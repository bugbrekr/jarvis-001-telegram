import requests

def simple_calculator(expression):
    return eval(expression)
def subtraction(a, b):
    if isinstance(a, str): a = int(a)
    if isinstance(b, str): b = int(b)
    return a-b

def make_web_request(url):
    res = requests.get(url)
    return res.text

def leave_note(note_text):
    return "Note sent."

def get_song_lyrics(song_query):
    r = requests.get(
        "https://lrclib.net/api/search",
        params={"q": song_query},
        headers={"User-Agent": "JARVIS-001-TG v0.x(https://github.com/bugbrekr/jarvis-001-telegram)"},
        timeout=3 # seconds
    )
    if not r.ok: raise BaseException("Response failed.")
    tracks = r.json()
    if not tracks: raise BaseException("No songs found.")
    track = tracks[0]
    if track["instrumental"]:
        return "[INSTRUMENTAL]"
    return track.get("plainLyrics") if track.get("plainLyrics") else track.get("syncedLyrics")

tool_definitions = [
    {
        "type": "function",
        "function": {
            "name": "simple_calculator",
            "description": "Evaluates a simple mathematical expression.",
            "parameters": {
                "type": "object",
                "required": ["expression"],
                "properties": {
                    "expression": {"type": "integer", "description": "Expression in Python syntax."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "make_web_request",
            "description": "Make a HTTP request and return its content.",
            "parameters": {
                "type": "object",
                "required": ["url"],
                "properties": {
                    "url": {"type": "string", "description": "URL of website."}
                }
            }
        }
    },{
        "type": "function",
        "function": {
            "name": "clear_context",
            "description": "Clear the current chat context or history",
            "parameters": {
                "type": "object",
                "required": [],
                "properties": {}
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "leave_note",
            "description": "Leave a note for Chaitanya behalf of the user and send it.",
            "parameters": {
                "type": "object",
                "required": ["note_text"],
                "properties": {
                    "note_text": {"type": "string", "description": "Text to include in the note, written from the assistant to Chaitanya."}
                }
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_song_lyrics",
            "description": "Get the lyrics of a song from the song's name.",
            "parameters": {
                "type": "object",
                "required": ["song_query"],
                "properties": {
                    "song_query": {"type": "string", "description": "Search query for song name and artist."}
                }
            }
        }
    },
    # {
    #     "type": "function",
    #     "function": {
    #         "name": "add_to_memory",
    #         "description": "Add some information to your long-term memory to remember.",
    #         "parameters": {
    #             "type": "object",
    #             "required": ["memory_text"],
    #             "properties": {
    #                 "memory_text": {"type": "string", "description": "Text to remember for later."}
    #             }
    #         }
    #     }
    # },
]

tool_functions = {
    "simple_calculator": simple_calculator,
    "make_web_request": make_web_request,
    "leave_note": leave_note,
    "get_song_lyrics": get_song_lyrics
}

def call_tool(name, arguments):
    if name not in tool_functions:
        return "ERROR: Tool not implemented yet. Try using another tool.", False
    try:
        result = tool_functions[name](**arguments)
    except Exception as e:
        return "ERROR: "+str(e), False
    return str(result), True
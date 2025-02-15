import json
import time

def get_owner_instructions():
    with open("data/owner_instructions.txt") as f:
        return f.read()

def get_user_notes(user_id):
    user_id = str(user_id)
    with open("data/user_memories.json") as f:
        all_user_memories = json.load(f)
    user_memories = all_user_memories.get(user_id, [])
    output = ""
    for mem in user_memories:
        output += mem[0]+"\n"
    return output

def add_user_note(user_id, text):
    user_id = str(user_id)
    text = str(text)
    with open("data/user_memories.json") as f:
        user_memories = json.load(f)
    if not user_memories.get(user_id): user_memories[user_id] = []
    user_memories[user_id].append([text, int(time.time())])
    with open("data/user_memories.json", "w") as f:
        json.dump(user_memories, f)

def get_tg_user_identity(user_id):
    user_id = str(user_id)
    with open("data/tg_user_identities.json") as f:
        user_identities = json.load(f)
    return user_identities.get(user_id) 

def set_tg_user_identity(user_id, name, username):
    user_id = str(user_id)
    with open("data/tg_user_identities.json") as f:
        user_identities = json.load(f)
    user_identities[user_id] = {
        "name": name,
        "username": username
    }
    with open("data/tg_user_identities.json", "w") as f:
        json.dump(user_identities, f)

class Context:
    def __init__(self):
        pass
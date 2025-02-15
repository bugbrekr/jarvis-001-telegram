import json
import time
import plyvel
import msgpack

plyvel_db = plyvel.DB("data/context_db/", create_if_missing=True)

def get_owner_instructions():
    with open("data/owner_instructions.txt") as f:
        return f.read().strip()

def get_user_notes(user_id):
    user_id = str(user_id)
    with open("data/user_memories.json") as f:
        all_user_memories = json.load(f)
    user_memories = all_user_memories.get(user_id, [])
    output = ""
    for mem in user_memories:
        output += mem[0]+"\n"
    return output.strip()

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
    def __init__(self, user_id:int):
        self.user_id = user_id
        self.db_key = self.user_id.to_bytes(4, "big")
        self.db = plyvel_db
    def _ser(self, d):
        return msgpack.dumps(d)
    def _deser(self, d):
        if not d: return {}
        return msgpack.loads(d)
    def _get(self, key, default=""):
        _d = self.db.get(self.db_key, None)
        if not _d: return default
        return self._deser(_d).get(key, default)
    def _set(self, key, value):
        _d = self.db.get(self.db_key, None)
        d = self._deser(_d)
        d[key] = value
        self.db.put(self.db_key, self._ser(d))
    @property
    def general_instructions(self) -> str:
        return get_owner_instructions()
    @general_instructions.setter
    def general_instructions(self, v:str):
        pass
    @property
    def user_specific_instructions(self) -> str:
        return self._get("user_specific_instructions")
    @user_specific_instructions.setter
    def user_specific_instructions(self, v:str):
        self._set("user_specific_instructions", v)
    @property
    def first_time(self) -> bool:
        return self._get("first_time", True)
    @first_time.setter
    def first_time(self, v:bool):
        self._set("first_time", v)
    @property
    def identity(self) -> dict:
        return self._get("identity", {"name": None, "username": None})
    @identity.setter
    def identity(self, v:dict):
        self._set("identity", v)

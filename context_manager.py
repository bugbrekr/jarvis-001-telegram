import json
import time
import plyvel
import msgpack
import llm_utils
import functions
import tools
import toml

plyvel_db = plyvel.DB("data/context_db/", create_if_missing=True)

with open("config/config.toml") as f:
    config = toml.loads(f.read())

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

class ListProxy:
    def __init__(self, owner, property_name):
        self._owner = owner
        self._property_name = property_name
        self._data = getattr(owner, property_name)
    def __getitem__(self, key):
        return self._data[key]
    def __setitem__(self, key, value):
        self._data[key] = value
        setattr(self._owner, self._property_name, self._data)
    def __len__(self):
        return len(self._data)
    def append(self, item):
        self._data.append(item)
        setattr(self._owner, self._property_name, self._data)
    def extend(self, items):
        self._data.extend(items)
        setattr(self._owner, self._property_name, self._data)
    def pop(self, index=-1):
        value = self._data.pop(index)
        setattr(self._owner, self._property_name, self._data)
        return value
    def remove(self, item):
        self._data.remove(item)
        setattr(self._owner, self._property_name, self._data)
    def clear(self):
        self._data.clear()
        setattr(self._owner, self._property_name, self._data)
    def __delitem__(self, key):
        del self._data[key]
        setattr(self._owner, self._property_name, self._data)
    def __repr__(self):
        return repr(self._data)

class ContextDB:
    def __init__(self, user_id:int):
        self.db_key = user_id.to_bytes(4, "big")
        self.db = plyvel_db
    def _ser(self, d):
        return msgpack.dumps(d)
    def _deser(self, d):
        if not d: return {}
        return msgpack.loads(d)
    def get(self, key, default=""):
        _d = self.db.get(self.db_key, None)
        if not _d: return default
        return self._deser(_d).get(key, default)
    def set(self, key, value):
        _d = self.db.get(self.db_key, None)
        d = self._deser(_d)
        d[key] = value
        self.db.put(self.db_key, self._ser(d))

class ContextualMemory:
    def __init__(self, db:ContextDB):
        self.db = db
        self.compressing_llm = llm_utils.LLM(model_name="Qwen/Qwen2.5-72B-Instruct")
        self.messages = ListProxy(self, "_messages")
        self.chat_history = ListProxy(self, "_chat_history")
    @property
    def context_prompt(self) -> str:
        return self.db.get("context_prompt", "")
    @property
    def _messages(self) -> list:
        return self.db.get("messages", [])
    @_messages.setter
    def _messages(self, v:list):
        self.db.set("messages", v)
    @property
    def _chat_history(self) -> list:
        return self.db.get("chat_history", [])
    @_chat_history.setter
    def _chat_history(self, v:list):
        self.db.set("chat_history", v)
    def _generate_summary(self, messages):
        formatted_messages = ""
        if self.context_prompt:
            formatted_messages += "Context: "+self.context_prompt+"\n\n"
        for i in messages:
            formatted_messages += i["role"].capitalize()+": "+i["message"]+"\n"
        _msgs = [
            {"role": "system", "content": config["compressing_agents_system_prompts"]["contextual_memory"]},
            {"role": "user", "content": formatted_messages}
        ]
        return "".join(self.compressing_llm.complete(_msgs))
    def add_message(self, role:str, message:str, chat_history_only:bool=False, context_history_only:bool=False, tool_calls:list=[]):
        if not context_history_only:
            self.chat_history.append({"role": role, "content": message})
        if chat_history_only: return
        if role == "user":
            self.messages.append({"role": "user", "message": message})
        elif role == "assistant":
            _message = functions.format_assistant_message_for_display(message, tool_calls, False, False)
            self.messages.append({"role": "assistant", "message": _message})
    def compress_context(self, exclude_n:int=0):
        messages_to_compress = list(self.messages[-exclude_n:])
        self.messages.clear()
        self.db.set("context_prompt", self._generate_summary(messages_to_compress))
    def clear_context(self):
        self.messages.clear()
        self.chat_history.clear()
        self.db.set("context_prompt", "")

class Context:
    def __init__(self, user_id:int):
        self.db = ContextDB(user_id)
        self.contextual_memory = ContextualMemory(self.db)
    @property
    def general_instructions(self) -> str:
        return get_owner_instructions()
    @general_instructions.setter
    def general_instructions(self, v:str):
        pass
    @property
    def user_specific_instructions(self) -> str:
        return self.db.get("user_specific_instructions")
    @user_specific_instructions.setter
    def user_specific_instructions(self, v:str):
        self.db.set("user_specific_instructions", v)
    @property
    def first_time(self) -> bool:
        return self.db.get("first_time", True)
    @first_time.setter
    def first_time(self, v:bool):
        self.db.set("first_time", v)
    @property
    def identity(self) -> dict:
        return self.db.get("identity", {"name": None, "username": None})
    @identity.setter
    def identity(self, v:dict):
        self.db.set("identity", v)
    def chat_history_with_system(self):
        system_prompt = llm_utils.prepare_system_prompt(tools.tool_definitions, self)
        return [{"role": "system", "content": system_prompt}]+list(self.contextual_memory.chat_history)

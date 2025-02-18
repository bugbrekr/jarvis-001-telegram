from huggingface_hub import InferenceClient
import json
import toml
import datetime

with open("config/SYSTEM.txt") as f:
	SYSTEM_TEMPLATE = f.read()

class LLM:
	def __init__(self, hf_api_key:str=None, model_name:str=None):
		if not hf_api_key or not model_name:
			with open("config/config.toml") as f:
				config = toml.loads(f.read())
			if not hf_api_key:
				hf_api_key = config["huggingface"]["API_KEY"]
			if not model_name:
				model_name = config["huggingface"]["MODEL_NAME"]
		self.client = InferenceClient(api_key=hf_api_key)
		self.model_name = model_name
	def complete(self, messages:list[dict], temperature:float=0.4, max_tokens:int=2048, top_p:float=0.7):
		stream = self.client.chat.completions.create(
			model=self.model_name, 
			messages=messages, 
			temperature=temperature,
			max_tokens=max_tokens,
			top_p=top_p,
			stream=True
		)
		for chunk in stream:
			yield chunk.choices[0].delta.content

def prepare_formatted_tool_definitions(tool_definitions):
	return "\n".join([json.dumps(i) for i in tool_definitions])

def prepare_system_prompt(tool_definitions, context):
	username = context.identity["username"]
	if not context.identity.get("username"):
		username = "NOT SET"
	formatted_tool_definitions = prepare_formatted_tool_definitions(tool_definitions)
	system_prompt = SYSTEM_TEMPLATE.replace("d2b17e58386b54a2_tools", formatted_tool_definitions)
	system_prompt = system_prompt.replace("11fb299ecd72fe4e_general_instructions", context.general_instructions)
	system_prompt = system_prompt.replace("9f598d8057f32d52_user_specific_instructions", context.user_specific_instructions)
	system_prompt = system_prompt.replace("3f32b4d1fe11651e_tg_contact_name", context.identity["name"])
	system_prompt = system_prompt.replace("20013f2a506da15d_tg_username", username)
	system_prompt = system_prompt.replace("7f73e86944eee177_context_prompt", context.contextual_memory.context_prompt)
	system_prompt = system_prompt.replace("d3914337f50c604d_datetime", datetime.datetime.now().strftime("%A, %d %B %Y, %H:%M:%S"))
	return system_prompt
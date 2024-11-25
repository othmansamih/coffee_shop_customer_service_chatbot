from openai import OpenAI
import os
import json
from copy import deepcopy
from .utils import get_chatbot_response, double_check_json_format
from dotenv import load_dotenv
load_dotenv()


class GuardAgent():
    def __init__(self):
        self.client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_LLM_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get('RUNPOD_API_KEY')
        )
        self.model_name = os.environ.get("MODEL_NAME")

    def get_response(self, messages):
        messages = deepcopy(messages)
        system_prompt = """
            You are a helpful AI assistant for a coffee shop application which serves drinks and pastries.

            Your task is to determine whether the user is asking something relevant to the coffee shop or not.

            The user is allowed to:
            1. Ask questions about the coffee shop, like location, working hours, menue items and coffee shop related questions.
            2. Ask questions about menue items, they can ask for ingredients in an item and more details about the item.
            3. Make an order.
            4. ASk about recommendations of what to buy.

            The user is NOT allowed to:
            1. Ask questions about anything else other than our coffee shop.
            2. Ask questions about the staff or how to make a certain menue item.

            Your output should be in a structured json format like so. each key is a string and each value is a string. Make sure to follow the format exactly:
            {
            "chain of thought": go over each of the points above and make see if the message lies under this point or not. Then you write some your thoughts about what point is this input relevant to.
            "decision": "allowed" or "not allowed". Pick one of those. and only write the word.
            "message": leave the message empty if it's allowed, otherwise write "Sorry, I can't help with that. Can I help you with your order?"
            }

        """

        messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_response = get_chatbot_response(self.client, self.model_name, messages)
        chatbot_response = double_check_json_format(self.client, self.model_name, chatbot_response)

        agent_response = self.postprocess_response(chatbot_response)
        
        return agent_response

    
    def postprocess_response(self, response):
        response_json = json.loads(response)
        
        postprocess_response = {
            "role": "assistant",
            "content": response_json["message"],
            "memory": {
                "agent": "guard_agent",
                "agent_decison": response_json["decision"]
            }
        }
        
        return postprocess_response



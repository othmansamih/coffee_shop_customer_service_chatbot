from openai import OpenAI
import os
import json
from copy import deepcopy
from .utils import get_chatbot_response, double_check_json_format
from dotenv import load_dotenv
load_dotenv()

class ClassificationAgent():
    def __init__(self):
        self.client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_LLM_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get('RUNPOD_API_KEY')
        )
        self.model_name = os.environ.get("MODEL_NAME")
    
    def get_response(self, messages):
        messages = deepcopy(messages)
        system_prompt = """
            You are a helpful AI assistant for a coffee shop application.

            Your task is to determine what agent should handle the user input. You have 3 agents to choose from:
            1. details_agent: This agent is responsible for answering questions about the coffee shop, like location, delivery places, working hours, details about menue items. Or listing items in the menu items. Or by asking what we have.
            2. order_taking_agent: This agent is responsible for taking orders from the user. It's responsible to have a conversation with the user about the order untill it's complete.
            3. recommendation_agent: This agent is responsible for giving recommendations to the user about what to buy. If the user asks for a recommendation, this agent should be used.

            Your output should be in a structured json format like so. each key is a string and each value is a string. Make sure to follow the format exactly:
            {
            "chain of thought": go over each of the agents above and write some your thoughts about what agent is this input relevant to.
            "decision": "details_agent" or "order_taking_agent" or "recommendation_agent". Pick one of those. and only write the word.
            "message": leave the message empty.
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
                "agent": "classification_agent",
                "agent_decision": response_json["decision"]
            }
        }

        return postprocess_response
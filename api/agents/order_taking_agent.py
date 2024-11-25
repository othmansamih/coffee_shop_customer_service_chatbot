import os
import json
from openai import OpenAI
from copy import deepcopy
from .utils import get_chatbot_response, double_check_json_format
from dotenv import load_dotenv
load_dotenv()


class OrderTakingAgent():
    # should I include all the messages in the input of the LLM call
    def __init__(self, recommendation_agent):
        self.client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_LLM_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get("RUNPOD_API_KEY")
        )
        self.model_name = os.environ.get("MODEL_NAME")
        self.recommendation_agent = recommendation_agent
    
    def get_response(self, messages):
        messages = deepcopy(messages)

        system_prompt = """
            You are a customer support Bot for a coffee shop called "Merry's way"

            here is the menu for this coffee shop.

            Cappuccino - $4.50
            Jumbo Savory Scone - $3.25
            Latte - $4.75
            Chocolate Chip Biscotti - $2.50
            Espresso shot - $2.00
            Hazelnut Biscotti - $2.75
            Chocolate Croissant - $3.75
            Dark chocolate (Drinking Chocolate) - $5.00
            Cranberry Scone - $3.50
            Croissant - $3.25
            Almond Croissant - $4.00
            Ginger Biscotti - $2.50
            Oatmeal Scone - $3.25
            Ginger Scone - $3.50
            Chocolate syrup - $1.50
            Hazelnut syrup - $1.50
            Carmel syrup - $1.50
            Sugar Free Vanilla syrup - $1.50
            Dark chocolate (Packaged Chocolate) - $3.00

            Things to NOT DO:
            * DON't ask how to pay by cash or Card.
            * Don't tell the user to go to the counter
            * Don't tell the user to go to place to get the order


            You're task is as follows:
            1. Take the User's Order
            2. Validate that all their items are in the menu
            3. if an item is not in the menu let the user and repeat back the remaining valid order
            4. Ask them if they need anything else.
            5. If they do then repeat starting from step 3
            6. If they don't want anything else. Using the "order" object that is in the output. Make sure to hit all three points
                1. list down all the items and their prices
                2. calculate the total. 
                3. Thank the user for the order and close the conversation with no more questions

            The user message will contain a section called memory. This section will contain the following:
            "order"
            "step number"
            please utilize this information to determine the next step in the process.
            
            produce the following output without any additions, not a single letter outside of the structure bellow.
            Your output should be in a structured json format like so. each key is a string and each value is a string. Make sure to follow the format exactly:
            {
            "chain of thought": Write down your critical thinking about what is the maximum task number the user is on write now. Then write down your critical thinking about the user input and it's relation to the coffee shop process. Then write down your thinking about how you should respond in the response parameter taking into consideration the Things to NOT DO section. and Focus on the things that you should not do. 
            "step number": Determine which task you are on based on the conversation.
            "order": this is going to be a list of jsons like so. [{"item":put the item name, "quanitity": put the number that the user wants from this item, "price":put the total price of the item }]
            "response": write the a response to the user
            }
        """

        last_order_taking_status = ""
        asked_recommendation_before = False
        for message in messages[::-1]:
            agent_name = message.get("memory", {}).get("agent","")
            if message["role"] == "assistant" and agent_name == "order_taking_agent":
                step_number = message["memory"]["step number"]
                order = message["memory"]["order"]
                last_order_taking_status = f"""
                    Step number: {step_number}
                    Order: {order}
                """
                asked_recommendation_before = message["memory"]["asked_recommendation_before"]
                break
        
        messages[-1]["content"] = f"""
            {last_order_taking_status}

            {messages[-1]["content"]}
        """

        # the problem has been fixed by changing the messages variable to input_messages
        input_messages = [{"role": "system", "content": system_prompt}] + messages

        chatbot_response = get_chatbot_response(self.client, self.model_name, input_messages)
        chatbot_response = double_check_json_format(self.client, self.model_name, chatbot_response)
        order_taking_agent_response = self.postprocess_response(chatbot_response, messages, asked_recommendation_before)

        return order_taking_agent_response
    
    def postprocess_response(self, response, messages, asked_recommendation_before):
        response_json = json.loads(response)

        if type(response_json["order"]) == str:
            response_json["order"] = json.loads(response_json["order"])

        if not asked_recommendation_before and len(response_json["order"])>0:
            recommendations = self.recommendation_agent.get_recommendations_from_order(messages, response_json["response"], response_json["order"])
            response_json["response"] = recommendations["content"]
            asked_recommendation_before = True

        postprocess_response = {
            "role": "assistant",
            "content": response_json["response"],
            "memory": {
                "agent": "order_taking_agent",
                "step number": response_json["step number"],
                "order": response_json["order"],
                "asked_recommendation_before": asked_recommendation_before
            }
        }

        return postprocess_response

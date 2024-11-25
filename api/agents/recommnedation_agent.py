from openai import OpenAI
import json
import os
import pandas as pd
from copy import deepcopy
from dotenv import load_dotenv
from .utils import get_chatbot_response, double_check_json_format
from pprint import pprint
load_dotenv()


class RecommendationAgent():
    def __init__(self, apriori_recommendation_path, popular_recommendation_path):
        self.client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_LLM_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get("RUNPOD_API_KEY")
        )
        self.model_name = os.environ.get("MODEL_NAME")

        with open(apriori_recommendation_path, "r") as file:
            self.apriori_recommendation = json.load(file)
        
        self.popular_recommendation = pd.read_csv(popular_recommendation_path)
        self.products = self.popular_recommendation["product"].tolist()
        self.product_categories = list(set(self.popular_recommendation["product_category"].tolist()))

    
    def get_popular_recommendation(self, products_categories=None, top_k=5):
        recommendations_df = self.popular_recommendation

        if type(products_categories) == str:
            products_categories = [products_categories]

        if products_categories is not None:
            recommendations_df = recommendations_df[recommendations_df["product_category"].isin(products_categories)]
        recommendations_df = recommendations_df.sort_values(by="number_of_transactions", ascending=False)

        if recommendations_df.shape[0] == 0:
            return []

        recommendations = recommendations_df["product"].tolist()[:top_k]
        return recommendations
    
    
    def get_apriori_recommendation(self, products, top_k=5):
        recommendations_list = []

        for product in products:
            if product in self.apriori_recommendation:
                recommendations_list += self.apriori_recommendation[product]
        
        recommendations_list = sorted(recommendations_list, key=lambda x : x["confidence"], reverse=True)
        
        recommendations = []
        recommendations_per_category = {}

        for recommendation in recommendations_list:
            if recommendation["product"] in recommendations:
                continue
            
            recommendation_product_category = recommendation["product_category"]
            if recommendation_product_category not in recommendations_per_category:
                recommendations_per_category[recommendation_product_category] = 0

            elif recommendations_per_category[recommendation_product_category] >= 2:
                continue

            recommendations_per_category[recommendation_product_category] += 1
            recommendations.append(recommendation["product"])

            if len(recommendations) >= top_k:
                break
        
        return recommendations
    

    def recommendation_classification(self, messages):
        messages = deepcopy(messages)

        system_prompt = f"""
            You are a helpful AI assistant for a coffee shop application which serves drinks and pastries. We have 3 types of recommendations:

            1. Apriori Recommendations: These are recommendations based on the user's order history. We recommend items that are frequently bought together with the items in the user's order.
            2. Popular Recommendations: These are recommendations based on the popularity of items in the coffee shop. We recommend items that are popular among customers.
            3. Popular Recommendations by Category: Here the user asks to recommend them product in a category. Like what coffee do you recommend me to get?. We recommend items that are popular in the category of the user's requested category.
            
            Here is the list of items in the coffee shop:
            """+ ",".join(self.products) + """
            Here is the list of Categories we have in the coffee shop:
            """ + ",".join(self.product_categories) + """

            Your task is to determine which type of recommendation to provide based on the user's message.

            Your output should be in a structured json format like so. Each key is a string and each value is a string. Make sure to follow the format exactly:
            {
            "chain of thought": Write down your critical thinking about what type of recommendation is this input relevant to.
            "recommendation_type": "apriori" or "popular" or "popular by category". Pick one of those and only write the word.
            "parameters": This is a  python list. It's either a list of of items for apriori recommendations or a list of categories for popular by category recommendations. Leave it empty for popular recommendations. Make sure to use the exact strings from the list of items and categories above.
            }
        """

        messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_response = get_chatbot_response(self.client, self.model_name, messages)
        chatbot_response = double_check_json_format(self.client, self.model_name, chatbot_response)
        classification_response = self.postprocess_classification_response(chatbot_response)

        return classification_response

    def postprocess_classification_response(self, response):
        response_json = json.loads(response)

        postprocess_response = {
            "recommendation_type": response_json["recommendation_type"],
            "parameters": response_json["parameters"]
        } 

        return postprocess_response
    
    def get_response(self, messages):
        messages = deepcopy(messages)

        recommendation_classification = self.recommendation_classification(messages)
        recommendation_type = recommendation_classification["recommendation_type"]

        recommendations = []
        if recommendation_type == "apriori":
            recommendations = self.get_apriori_recommendation(recommendation_classification["parameters"])
        elif recommendation_type == "popular":
            recommendations = self.get_popular_recommendation()
        elif recommendation_type == "popular by category":
            recommendations = self.get_popular_recommendation(recommendation_classification["parameters"])
        
        if len(recommendations) == 0:
            return {"role": "assistant", "content": "I'm sorry I can't help with that. Can I help you with your order?"}
        
        recommendations_str = ", ".join(recommendations)

        system_prompt = f"""
            You are a helpful AI assistant for a coffee shop application which serves drinks and pastries.
            your task is to recommend items to the user based on their input message. And respond in a friendly but concise way. And put it an unordered list with a very small description.

            I will provide what items you should recommend to the user based on their order in the user message. 
        """

        user_prompt = f"""
        {messages[-1]["content"]}

        Please recommend me those items exactly: {recommendations_str}
        """
        messages[-1]["content"] = user_prompt

        messages = [{"role": "system", "content": system_prompt}] + messages[-3:]
        chatbot_response = get_chatbot_response(self.client, self.model_name, messages)
        recommendation_agent_response = self.postprocess_response(chatbot_response)

        return recommendation_agent_response
    

    # this function is a helper function (in the orders_agent) 
    def get_recommendations_from_order(self, messages, system_message, order):
        #messages = deepcopy(messages)
        products = []
        for product in order:
            products.append(product["item"])
        
        recommendations = self.get_apriori_recommendation(products)
        recommendations_str = ", ".join(recommendations)
        
        system_prompt = f"""
            You are a helpful AI assistant for a coffee shop application which serves drinks and pastries.
            
            Your task is to print the system message as it is with your recommendations without the title 'System message'.

            Under the title 'Recommendations,' provide suggestions along with brief information about each, without any additional questions or introductory phrases.
            
            I will provide what items you should recommend to the user based on the system message. 
        """

        user_prompt = f"""
            System message: {system_message}

            Please recommend me those items exactly: {recommendations_str}
        """
        messages[-1]["content"] = user_prompt

        input_messages = [{"role": "system", "content": system_prompt}] + messages[-3:]

        chatbot_response = get_chatbot_response(self.client, self.model_name, input_messages)
        recommendations_response = self.postprocess_response(chatbot_response)

        return recommendations_response
    
    def postprocess_response(self, response):
        postprocess_response = {
            "role": "assistant",
            "content": response,
            "memory": {
                "agent": "recommendation_agent"
            }
        }

        return postprocess_response




    


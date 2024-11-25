from openai import OpenAI
import json
import os
from copy import deepcopy
from dotenv import load_dotenv
from pinecone import Pinecone
from .utils import get_chatbot_response, get_embeddings
load_dotenv()


class DetailsAgent():
    def __init__(self):
        self.client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_LLM_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get("RUNPOD_API_KEY")
        )
        self.model_name = os.environ.get("MODEL_NAME")
        self.embedding_client = OpenAI(
            base_url=f"https://api.runpod.ai/v2/{os.environ.get('RUNPOD_EMBEDDING_MODEL_ENDPOINT_ID')}/openai/v1",
            api_key=os.environ.get("RUNPOD_API_KEY")
        )
        self.embedding_model_name = os.environ.get("EMBEDDING_MODEL_NAME")
        self.pc = Pinecone(api_key=os.environ.get("PINECONE_API_KEY"))
        self.pinecone_index = self.pc.Index(os.environ.get("PINECONE_INDEX_NAME"))

    
    def get_relevant_results(self, prompt, top_k=2):
        results = self.pinecone_index.query(
            namespace="coffee-shop-app-namespace",
            vector=prompt,
            top_k=top_k,
            include_values=False,
            include_metadata=True
        )

        relevant_results = "\n\n".join([result["metadata"]["text"] for result in results["matches"]])
        
        return relevant_results
    

    def get_response(self, messages):
        messages = deepcopy(messages)
        user_prompt = messages[-1]["content"]
        user_prompt_embedding = get_embeddings(self.embedding_client, self.embedding_model_name, user_prompt)
        source_knowledge = self.get_relevant_results(user_prompt_embedding)

        new_user_prompt = f"""
            Using the contexts below, answer the query.

            Contexts:
            {source_knowledge}


            Query: {user_prompt}
        """

        messages[-1]["content"] = new_user_prompt
        system_prompt = "You are a customer support agent for a coffee shop called Merry's way. You should answer every question as if you are waiter and provide the neccessary information to the user regarding their orders"
        messages = [{"role": "system", "content": system_prompt}] + messages[-3:]
        chatbot_response = get_chatbot_response(self.client, self.model_name, messages)
        agent_response = self.postprocess_response(chatbot_response)
        
        return agent_response
    
    
    def postprocess_response(self, response):
        postprocess_response = {
            "role": "assistant",
            "content": response,
            "memory": {
                "agent": "details_agent"
            }
        }

        return postprocess_response
    
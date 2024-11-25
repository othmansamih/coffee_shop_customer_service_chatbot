from agents import (GuardAgent,
                    ClassificationAgent,
                    ProtocolAgent,
                    DetailsAgent,
                    RecommendationAgent,
                    OrderTakingAgent)
import os
from typing import Dict
import pathlib
from pprint import pprint

folder_path = pathlib.Path(__file__).parent.resolve()

def main():
    guard_agent = GuardAgent()
    classification_agent = ClassificationAgent()
    recommendation_agent = RecommendationAgent(
                                    os.path.join(folder_path,"recommendation_objects/apriori_recommendations.json"),
                                    os.path.join(folder_path,"recommendation_objects/popularity_recommendation.csv")
                                )
    agent_dict : Dict[str, ProtocolAgent] = {
        "details_agent": DetailsAgent(),
        "recommendation_agent": recommendation_agent,
        "order_taking_agent": OrderTakingAgent(recommendation_agent)
    }

    messages = []
    while True:
        os.system("cls" if os.name == "nt" else "clear")
        for message in messages:
            print(f"{message['role']} : {message['content']}")
            
            if message["role"] == "assistant":
                print("--------------------------------------------------------")

        user_prompt = input("User prompt: ")
        messages.append({"role": "user", "content": user_prompt})
        guard_agent_response = guard_agent.get_response(messages)
        if guard_agent_response["memory"]["agent_decison"] == "not allowed":
            messages.append({"role": guard_agent_response["role"], "content": guard_agent_response["content"]})
            continue
        

        classification_agent_response = classification_agent.get_response(messages)

        #print(f"Chosen agent: {classification_agent_response['memory']['agent_decision']}")
        
        chosen_agent = classification_agent_response['memory']['agent_decision']
        agent = agent_dict[chosen_agent]
        agent_response = agent.get_response(messages)
        messages.append({"role": agent_response["role"], "content": agent_response["content"]})

        



if __name__ == "__main__":
    main()

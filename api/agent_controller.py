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


class AgentController():
    def __init__(self):
        self.guard_agent = GuardAgent()
        self.classification_agent = ClassificationAgent()
        self.recommendation_agent = RecommendationAgent(
                                        os.path.join(folder_path,"recommendation_objects/apriori_recommendations.json"),
                                        os.path.join(folder_path,"recommendation_objects/popularity_recommendation.csv")
                                    )
        self.agent_dict : Dict[str, ProtocolAgent] = {
            "details_agent": DetailsAgent(),
            "recommendation_agent": self.recommendation_agent,
            "order_taking_agent": OrderTakingAgent(self.recommendation_agent)
        }
    

    def get_response(self, job):
        job_input = job["input"]
        messages = job_input["messages"]

        guard_agent_response = self.guard_agent.get_response(messages)
        if guard_agent_response["memory"]["agent_decison"] == "not allowed":
            return guard_agent_response
        

        classification_agent_response = self.classification_agent.get_response(messages)        
        chosen_agent = classification_agent_response['memory']['agent_decision']
        agent = self.agent_dict[chosen_agent]
        agent_response = agent.get_response(messages)
        
        return agent_response
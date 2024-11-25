FROM python:3.8.6-slim

RUN mkdir /app

WORKDIR /app

COPY requirements.txt requirements.txt
COPY agents/ agents/
COPY recommendation_objects/ recommendation_objects/
COPY agent_controller.py agent_controller.py
COPY main.py main.py

RUN pip install -r requirements.txt

# making a verification before deploying the container in runpod
#COPY test_input.json test_input.json

ENTRYPOINT [ "python", "main.py" ]
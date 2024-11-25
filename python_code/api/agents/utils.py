def get_chatbot_response(client, model_name, messages, temperature=0):
    input_messages = []
    for message in messages:
        input_messages.append({"role": message["role"],"content": message["content"]})

    chat_completion = client.chat.completions.create(
        model=model_name,
        messages=input_messages,
        temperature=temperature,
        max_tokens=2000
    )

    return chat_completion.choices[0].message.content


def get_embeddings(embedding_client, model_name, input_text):
    response = embedding_client.embeddings.create(
        input=input_text,
        model=model_name
    )
    return response.data[0].embedding


def double_check_json_format(client, model_name, json_string):
    prompt = f"""
        You will check this json string and correct any mistakes that will make it invalid. Then you will return the corrected json string. Nothing else. 
        If the Json is correct just return it.

        Do NOT return a single letter outside of the json string.
        The first thing you write should be open curly brace of the json and the last letter you write should be the closing curly brace.

        If the value of a key in a JSON object is a string, ensure it remains on a single line. If the string contains line breaks, replace each line break with \\n.        
        
        You should check the json string for the following text betweeen triple brackets.

        ```
        {json_string}
        ```
    """

    messages = [{"role": "user", "content": prompt}]

    chatbot_response = get_chatbot_response(client, model_name, messages)
    chatbot_response = chatbot_response.replace("`", "")

    return chatbot_response


from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import json
import time

app = Flask(__name__)
CORS(app)

openai_api_key = 'your-openai-api-key'
headers = {
    'Authorization': f'Bearer {openai_api_key}',
    'Content-Type': 'application/json',
    'OpenAI-Beta': 'assistants=v1'
}

@app.route('/sendMessage', methods=['POST'])
def send_message():
    try:
        user_message = request.json.get('message', '')
        app.logger.info(f"Received message: {user_message}")

        # Step 1: Create an Assistant
        assistant_data = json.dumps({
            "name": "AlphaETF Assistant",
            "model": "gpt-4-1106-preview",
            "instructions": "You are an AI assistant that helps with ETF information."
        })
        assistant_response = requests.post('https://api.openai.com/v1/assistants', headers=headers, data=assistant_data)
        if assistant_response.status_code != 200:
            raise Exception(f"Failed to create assistant: {assistant_response.json()}")

        assistant_id = assistant_response.json().get('id', '')
        app.logger.info(f"Assistant created with ID: {assistant_id}")

        # Step 2: Create a Thread
        thread_response = requests.post('https://api.openai.com/v1/threads', headers=headers)
        if thread_response.status_code != 200:
            raise Exception(f"Failed to create thread: {thread_response.json()}")

        thread_id = thread_response.json().get('id', '')
        app.logger.info(f"Thread created with ID: {thread_id}")

        # Step 3: Add a Message to the Thread
        message_data = json.dumps({
            "role": "user",
            "content": user_message
        })
        message_url = f'https://api.openai.com/v1/threads/{thread_id}/messages'
        message_response = requests.post(message_url, headers=headers, data=message_data)
        if message_response.status_code != 200:
            raise Exception(f"Failed to add message to thread: {message_response.json()}")

        # Step 4: Run the Assistant and Poll for Completion
        run_data = json.dumps({"assistant_id": assistant_id})
        run_response = requests.post(f'https://api.openai.com/v1/threads/{thread_id}/runs', headers=headers, data=run_data)
        if run_response.status_code != 200:
            raise Exception(f"Failed to run the assistant: {run_response.json()}")

        run_id = run_response.json().get('id', '')
        run_status = run_response.json().get('status', '')

        # Poll for completion
        while run_status not in ['completed', 'failed']:
            time.sleep(2)  # Wait for 2 seconds before next check
            run_check_response = requests.get(f'https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}', headers=headers)
            if run_check_response.status_code == 200:
                run_status = run_check_response.json().get('status', '')
            else:
                raise Exception(f"Error checking run status: {run_check_response.json()}")

        if run_status == 'failed':
            raise Exception("Run failed to complete")

        # Step 5: Retrieve and Log All Messages in the Thread
        messages_response = requests.get(f'https://api.openai.com/v1/threads/{thread_id}/messages', headers=headers)
        app.logger.info(f"Messages response: {messages_response.json()}")
        if messages_response.status_code != 200:
            raise Exception(f"Failed to retrieve messages: {messages_response.json()}")

        messages = messages_response.json().get('data', [])
        assistant_message = "No response"
        for message in messages:
            app.logger.info(f"Message: {message}")
            if message.get('role') == 'assistant':
                assistant_message = message.get('content')[0].get('text').get('value')

        return jsonify({'response': assistant_message})
    except Exception as e:
        app.logger.error(f"Error in sendMessage: {e}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
import os
import json
import requests
import google.generativeai as genai
from datetime import datetime

# Configuration
HISTORY_FILE = 'history.json'
TELEGRAM_BOT_TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.environ.get('TELEGRAM_CHAT_ID')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_history(history):
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(history, f, indent=4, ensure_ascii=False)

def generate_words(history):
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # Create the prompt
    history_list = ", ".join(history[-50:]) # Send last 50 words to avoid recent duplicates
    prompt = f"""
    You are a helpful Hebrew tutor. Generate 5 ADVANCED Hebrew words.
    
    Rules:
    1. The words must be different from these previously used words: {history_list}
    2. Format exactly as requested below.
    3. Include transliteration, translation, part of speech, explanation, and an example sentence (with transliteration and translation).
    
    Output Format (JSON list of objects):
    [
        {{
            "word": "HebrewWord",
            "transliteration": "Transliteration",
            "part_of_speech": "Part of Speech",
            "definition": "English definition and explanation",
            "example_hebrew": "Example sentence in Hebrew",
            "example_transliteration": "Example sentence transliteration",
            "example_translation": "Example sentence translation"
        }},
        ...
    ]
    
    Ensure the JSON is valid and the "word" field contains the Hebrew word with Nikud.
    """
    
    try:
        response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
        return json.loads(response.text)
    except Exception as e:
        print(f"Error generating words: {e}")
        return None

def format_message(words_data):
    message = "Here are 5 advanced Hebrew words for today:\n\n"
    
    for i, item in enumerate(words_data, 1):
        message += f"{i}. {item['transliteration']} ({item['word']})\n"
        message += f"Part of Speech: {item['part_of_speech']}\n\n"
        message += f"{item['definition']}\n\n"
        message += "Example:\n"
        message += f"Hebrew: {item['example_hebrew']}\n"
        message += f"Transliteration: {item['example_transliteration']}\n"
        message += f"Translation: {item['example_translation']}\n\n"
        message += "---\n\n"
        
    return message

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, json=payload)
    return response.json()

def main():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY]):
        print("Missing environment variables.")
        return

    history = load_history()
    words_data = generate_words(history)
    
    if words_data:
        message_text = format_message(words_data)
        print("Sending message...")
        result = send_telegram_message(message_text)
        
        if result.get('ok'):
            print("Message sent successfully.")
            # Update history
            new_words = [w['word'] for w in words_data]
            history.extend(new_words)
            save_history(history)
        else:
            print(f"Failed to send message: {result}")
    else:
        print("Failed to generate words.")

if __name__ == "__main__":
    main()

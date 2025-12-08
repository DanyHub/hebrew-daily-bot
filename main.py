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
    
    # Candidate models to try in order (Prioritizing newer 2.5 models)
    candidate_models = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-2.0-flash-exp',
        'gemini-2.0-flash'
    ]

    import time
    
    for model_name in candidate_models:
        print(f"Attempting to generate with model: {model_name}")
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text)
        except Exception as e:
            print(f"Model {model_name} failed: {e}")
            if "429" in str(e):
                print("Rate limit encountered. Waiting 60 seconds before next model...")
                time.sleep(60)
            continue

    print("All candidate models failed.")
    # Fallback to listing models if all failed
    try:
        print("Attempting to list available models for debugging:")
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
    except Exception as list_e:
        print(f"Could not list models: {list_e}")
    return None

    return None

def format_message(words_data):
    message = "📚 **Daily Hebrew Vocabulary** 🇮🇱\n\n"
    
    for i, item in enumerate(words_data, 1):
        message += f"{i}. *{item['transliteration']}* (**{item['word']}**)\n"
        message += f"🏷️ _Part of Speech:_ {item['part_of_speech']}\n\n"
        message += f"📖 *Definition:*\n{item['definition']}\n\n"
        message += "🗣️ *Example:*\n"
        message += f"🇮🇱 {item['example_hebrew']}\n"
        message += f"🔤 {item['example_transliteration']}\n"
        message += f"🇬🇧 {item['example_translation']}\n\n"
        message += "〰️〰️〰️〰️〰️\n\n"
        
    return message

def generate_quiz_content(word):
    """Generates 3 incorrect definitions for the given word using Gemini."""
    prompt = f"""
    Create a multiple-choice quiz for the Hebrew word: "{word}".
    
    1. Provide the CORRECT English definition.
    2. Provide 3 PLAUSIBLE but INCORRECT English definitions (distractors).
    
    Output JSON format:
    {{
        "question": "What is the meaning of '{word}'?",
        "correct_option": "The correct definition",
        "options": [
            "The correct definition",
            "Distractor 1",
            "Distractor 2",
            "Distractor 3"
        ]
    }}
    Important: The "options" list MUST contain the correct answer and the 3 distractors shuffled randomly.
    """
    
    # Candidate models to try in order (Prioritizing newer 2.5 models)
    candidate_models = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash-lite-preview-02-05',
        'gemini-2.0-flash-exp',
        'gemini-2.0-flash'
    ]

    import time
    
    for model_name in candidate_models:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt, generation_config={"response_mime_type": "application/json"})
            return json.loads(response.text)
        except Exception as e:
            print(f"Quiz generation failed with {model_name}: {e}")
            if "429" in str(e):
                time.sleep(60)
            continue
            
    return None

def send_telegram_poll(quiz_data):
    """Sends a native Telegram Quiz poll."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendPoll"
    
    # Find the index of the correct option for Telegram to check the answer
    # Note: Gemini is asked to shuffle, so we just need to find where the correct one landed.
    try:
        correct_option_id = quiz_data['options'].index(quiz_data['correct_option'])
    except ValueError:
        print("Error: Correct option not found in options list.")
        return None

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": quiz_data['question'],
        "options": json.dumps(quiz_data['options']),
        "type": "quiz",
        "correct_option_id": correct_option_id,
        "is_anonymous": True # Anonymous voting by default
    }
    
    response = requests.post(url, data=payload)
    return response.json()

def run_quiz_mode():
    print("Starting Weekly Quiz Mode...")
    history = load_history()
    
    if not history:
        print("No history found. Cannot generate quiz.")
        return

    # Select a word from the last 7 days (or last 7 items if dates aren't tracked)
    # Asking for a random word from the recent batch
    import random
    recent_words = history[-35:] # Last week's words (5 per day * 7 days = 35)
    if not recent_words:
        recent_words = history # Fallback to all history
    
    target_word = random.choice(recent_words)
    print(f"Selected word for quiz: {target_word}")
    
    quiz_data = generate_quiz_content(target_word)
    
    if quiz_data:
        print("Sending quiz...")
        result = send_telegram_poll(quiz_data)
        if result.get('ok'):
            print("Quiz sent successfully.")
        else:
            print(f"Failed to send quiz: {result}")
    else:
        print("Failed to generate quiz content.")

def main():
    if not all([TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, GEMINI_API_KEY]):
        print("Missing environment variables.")
        return

    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--quiz':
        run_quiz_mode()
        return

    # Default: Daily Words Mode
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

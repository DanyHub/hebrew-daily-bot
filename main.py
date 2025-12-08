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

def send_telegram_message(message):
    """Sends a text message to the Telegram chat."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    return response.json()

def generate_quiz_content(words_list):
    """
    Generates quiz content for a list of words.
    Returns a list of objects, each containing quiz data + full card details.
    """
    words_str = ", ".join(words_list)
    prompt = f"""
    Create a multiple-choice quiz for the following Hebrew words: {words_str}.
    
    For EACH word, provide:
    1. The quiz data (Question, Correct Answer, 3 Distractors).
    2. The full educational card (Word, Transliteration, Part of Speech, Definition, Example).
    
    Output JSON format (List of objects):
    [
        {{
            "word": "HebrewWord",
            "quiz": {{
                "question": "What is the meaning of 'HebrewWord'?",
                "correct_option": "The correct definition",
                "options": ["The correct definition", "Distractor 1", "Distractor 2", "Distractor 3"]
            }},
            "card": {{
                "transliteration": "Transliteration",
                "part_of_speech": "Part of speech",
                "definition": "The exact correct definition used above",
                "example_hebrew": "Example sentence",
                "example_transliteration": "Example transliteration",
                "example_translation": "Example translation"
            }}
        }},
        ...
    ]
    Important: 
    1. The "options" list MUST contain the correct answer and 3 distractors shuffled.
    2. Ensure the "card" details match the "correct_option".
    """
    
    # Candidate models
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
    
    try:
        correct_option_id = quiz_data['options'].index(quiz_data['correct_option'])
    except ValueError:
        return None

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "question": quiz_data['question'],
        "options": json.dumps(quiz_data['options']),
        "type": "quiz",
        "correct_option_id": correct_option_id,
        "is_anonymous": True
    }
    
    requests.post(url, data=payload)

def send_telegram_spoiler(word, card_data):
    """Sends the full card details hidden behind a spoiler."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    
    message = f"||🎯 **Answer Key for {word}**\n\n"
    message += f"*{card_data['transliteration']}* ({word})\n"
    message += f"🏷️ {card_data['part_of_speech']}\n"
    message += f"📖 {card_data['definition']}\n\n"
    message += f"🗣️ **Example:**\n"
    message += f"🇮🇱 {card_data['example_hebrew']}\n"
    message += f"🇬🇧 {card_data['example_translation']}||"
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "MarkdownV2" 
    }
    # Note: MarkdownV2 requires escaping certain characters, but for simplicity in this proto
    # we might use standard Markdown if supported with spoilers, but Spoilers are usually MarkdownV2.
    # Let's try standard Markdown first with explicit tags if Telegram supports it, 
    # otherwise we might need a simple HTML parse_mode for <span class="tg-spoiler">.
    
    # Switch to HTML for easier spoiler handling without complex escaping
    payload['parse_mode'] = 'HTML'
    payload['text'] = f"""
<span class="tg-spoiler">
🎯 <b>Answer Key for {word}</b>

<i>{card_data['transliteration']}</i> (<b>{word}</b>)
🏷️ {card_data['part_of_speech']}
📖 {card_data['definition']}

🗣️ <b>Example:</b>
🇮🇱 {card_data['example_hebrew']}
🇬🇧 {card_data['example_translation']}
</span>
    """
    
    requests.post(url, json=payload)

def run_quiz_mode():
    print("Starting Weekly Quiz Mode...")
    history = load_history()
    
    if not history:
        print("No history found.")
        return

    import random
    import time
    
    # Select 3 unique random words
    recent_words = history[-35:] if len(history) >= 35 else history
    # Ensure we don't crash if less than 3 words exist
    sample_size = min(3, len(recent_words))
    target_words = random.sample(recent_words, sample_size)
    
    print(f"Selected words for quiz: {target_words}")
    
    # Generate content for all 3 words in one go (more efficient)
    quiz_items = generate_quiz_content(target_words)
    
    if quiz_items:
        for item in quiz_items:
            print(f"Sending quiz for: {item['word']}")
            send_telegram_poll(item['quiz'])
            time.sleep(1) # Small delay to ensure order
            send_telegram_spoiler(item['word'], item['card'])
            time.sleep(2) # Delay between questions
            
        print("All quizzes sent.")
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

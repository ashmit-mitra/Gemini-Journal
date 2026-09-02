from dotenv import load_dotenv
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google import genai
from datetime import datetime, timedelta
from collections import defaultdict
import os

app = Flask(__name__)

cred = credentials.Certificate("gemini-journal-ai-1a8c1-d498859952c2.json")
firebase_admin.initialize_app(cred, {'projectId': 'gemini-journal-ai-1a8c1'})
db = firestore.client()

gemini_client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))

request_log = defaultdict(list)
RATE_LIMIT = 15
RATE_WINDOW = 60

def is_rate_limited(uid):
    now = datetime.utcnow()
    window_start = now - timedelta(seconds=RATE_WINDOW)
    request_log[uid] = [t for t in request_log[uid] if t > window_start]
    if len(request_log[uid]) >= RATE_LIMIT:
        return True
    request_log[uid].append(now)
    return False

@app.route('/')
def home():
    return render_template('index.html')
PERSONA_PROMPTS = {
    'empathetic': "You are an empathetic, supportive, and validating journaling companion. Acknowledge feelings warmly, offer gentle perspective, and provide a safe space.",
    'socratic': "You are a Socratic reflection coach. Challenge assumptions gently, ask 1-2 probing questions to help the user uncover deeper insights, and avoid simple reassurance.",
    'stoic': "You are a Stoic reflection guide inspired by Marcus Aurelius and Epictetus. Emphasize resilience, emotional clarity, distinguishing between what is inside vs outside personal control, and staying grounded.",
    'action': "You are a solution-focused action planner. Help extract clarity, break down overwhelming thoughts into 2-3 concrete micro-steps, and focus on practical momentum."
}
@app.route('/api/chat', methods=['POST'])
@app.route('/api/chat', methods=['POST'])
def chat():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    if is_rate_limited(uid):
        return jsonify({'error': 'Too many requests. Please slow down and try again in a minute.'}), 429

    data = request.json or {}
    user_message = data.get('message', '')
    persona_key = data.get('persona', 'empathetic')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    system_instruction = PERSONA_PROMPTS.get(persona_key, PERSONA_PROMPTS['empathetic'])

    entries_ref = db.collection('users').document(uid).collection('entries')
    past_entries = entries_ref.order_by('timestamp').limit_to_last(8).get()

    conversation_history = []
    for entry in past_entries:
        entry_data = entry.to_dict()
        conversation_history.append({'role': 'user', 'parts': [{'text': entry_data['user_message']}]})
        conversation_history.append({'role': 'model', 'parts': [{'text': entry_data['ai_reply']}]})

    conversation_history.append({'role': 'user', 'parts': [{'text': f"[Context: Respond strictly adopting the following persona: {system_instruction}]\n\nUser Entry: {user_message}"}]})

    try:
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=conversation_history
        )
        ai_reply = response.text
    except Exception as e:
        print(f"Gemini API error in /api/chat: {e}")
        return jsonify({'error': f'Failed to generate reply: {str(e)}'}), 500

    mood = "neutral"
    try:
        mood_prompt = f"""Classify the mood of this journal entry in exactly one word from this list: happy, sad, anxious, angry, excited, calm, neutral, grateful, tired, hopeful.

Entry: "{user_message}"

Respond with only the single mood word, nothing else."""
        mood_response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=mood_prompt
        )
        mood = mood_response.text.strip().lower()
    except Exception as e:
        print(f"Mood detection error: {e}")

    entries_ref.add({
        'user_message': user_message,
        'ai_reply': ai_reply,
        'mood': mood,
        'persona': persona_key,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'reply': ai_reply, 'mood': mood})
@app.route('/api/daily-prompt', methods=['GET'])
def get_daily_prompt():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        prompt_instruction = "Generate one thoughtful, creative, and deep journaling prompt for today. Keep it under 25 words. Do not use quotes or introductory text."
        response = gemini_client.models.generate_content(
            model="gemini-1.5-flash",
            contents=prompt_instruction
        )
        return jsonify({'prompt': response.text.strip()})
    except Exception as e:
        print(f"Daily prompt error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries', methods=['GET'])
def get_entries():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    entries_ref = db.collection('users').document(uid).collection('entries')
    all_entries = entries_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).get()

    entries_list = []
    for entry in all_entries:
        entry_data = entry.to_dict()
        entries_list.append({
            'id': entry.id,
            'user_message': entry_data.get('user_message', ''),
            'ai_reply': entry_data.get('ai_reply', ''),
            'mood': entry_data.get('mood', 'neutral')
        })

    return jsonify({'entries': entries_list})

@app.route('/api/entries/<entry_id>', methods=['DELETE'])
def delete_entry(entry_id):
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        db.collection('users').document(uid).collection('entries').document(entry_id).delete()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/entries/<entry_id>', methods=['PUT'])
def edit_entry(entry_id):
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    new_message = data.get('user_message', '')
    if not new_message:
        return jsonify({'error': 'No message provided'}), 400

    try:
        db.collection('users').document(uid).collection('entries').document(entry_id).update({
            'user_message': new_message
        })
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/streak', methods=['GET'])
def get_streak():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        entries_ref = db.collection('users').document(uid).collection('entries')
        all_entries = entries_ref.order_by('timestamp', direction=firestore.Query.DESCENDING).get()

        entry_dates = set()
        for entry in all_entries:
            entry_data = entry.to_dict()
            ts = entry_data.get('timestamp')
            if ts:
                entry_dates.add(ts.date())

        if not entry_dates:
            return jsonify({'streak': 0, 'journaled_today': False})

        today = datetime.utcnow().date()
        journaled_today = today in entry_dates

        streak = 0
        check_date = today if journaled_today else today - timedelta(days=1)
        while check_date in entry_dates:
            streak += 1
            check_date -= timedelta(days=1)

        return jsonify({'streak': streak, 'journaled_today': journaled_today})
    except Exception as e:
        print(f"Streak calculation error: {e}")
        return jsonify({'streak': 0, 'journaled_today': False})

@app.route('/api/mood-trend', methods=['GET'])
def mood_trend():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    try:
        entries_ref = db.collection('users').document(uid).collection('entries')
        all_entries = entries_ref.order_by('timestamp').get()

        mood_counts = defaultdict(int)
        timeline = []
        for entry in all_entries:
            entry_data = entry.to_dict()
            mood = entry_data.get('mood', 'neutral')
            ts = entry_data.get('timestamp')
            mood_counts[mood] += 1
            if ts:
                timeline.append({'date': ts.strftime('%b %d'), 'mood': mood})

        return jsonify({'mood_counts': dict(mood_counts), 'timeline': timeline})
    except Exception as e:
        print(f"Mood trend error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/insights', methods=['GET'])
def insights():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    if is_rate_limited(uid):
        return jsonify({'error': 'Too many requests. Please slow down and try again in a minute.'}), 429

    entries_ref = db.collection('users').document(uid).collection('entries')
    all_entries = entries_ref.order_by('timestamp').get()

    if not all_entries:
        return jsonify({'insight': "You don't have any journal entries yet. Write a few first, then check back for insights!"})

    entry_texts = []
    for entry in all_entries:
        entry_data = entry.to_dict()
        entry_texts.append(entry_data.get('user_message', ''))

    combined_text = "\n".join(entry_texts)

    prompt = f"""Here are someone's journal entries, in order:

{combined_text}

Based on these entries, write a short, warm reflection (3-4 sentences) covering: any recurring themes or topics, the overall mood or tone, and one gentle observation or encouragement. Keep it personal and supportive, not clinical."""

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
            contents=prompt
        )
        return jsonify({'insight': response.text})
    except Exception as e:
        print(f"Gemini API error in /api/insights: {e}")
        return jsonify({'error': f'Failed to generate insight: {str(e)}'}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
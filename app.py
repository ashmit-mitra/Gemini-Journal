from dotenv import load_dotenv
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify
import firebase_admin
from firebase_admin import credentials, auth, firestore
from google import genai
import os

app = Flask(__name__)

cred = credentials.Certificate("gemini-journal-ai-1a8c1-d498859952c2.json")
firebase_admin.initialize_app(cred, {'projectId': 'gemini-journal-ai-1a8c1'})
db = firestore.client()

gemini_client = genai.Client(api_key=os.environ.get('GOOGLE_API_KEY'))

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/chat', methods=['POST'])
def chat():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

    data = request.json
    user_message = data.get('message', '')
    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    entries_ref = db.collection('users').document(uid).collection('entries')
    past_entries = entries_ref.order_by('timestamp').limit_to_last(10).get()

    conversation_history = []
    for entry in past_entries:
        entry_data = entry.to_dict()
        conversation_history.append({'role': 'user', 'parts': [{'text': entry_data['user_message']}]})
        conversation_history.append({'role': 'model', 'parts': [{'text': entry_data['ai_reply']}]})

    conversation_history.append({'role': 'user', 'parts': [{'text': user_message}]})

    try:
        response = gemini_client.models.generate_content(
            model="gemini-3.6-flash",
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
            model="gemini-3.6-flash",
            contents=mood_prompt
        )
        mood = mood_response.text.strip().lower()
    except Exception as e:
        print(f"Mood detection error: {e}")

    entries_ref.add({
        'user_message': user_message,
        'ai_reply': ai_reply,
        'mood': mood,
        'timestamp': firestore.SERVER_TIMESTAMP
    })

    return jsonify({'reply': ai_reply, 'mood': mood})

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

@app.route('/api/insights', methods=['GET'])
def insights():
    id_token = request.headers.get('Authorization', '').replace('Bearer ', '')
    try:
        decoded_token = auth.verify_id_token(id_token)
        uid = decoded_token['uid']
    except Exception:
        return jsonify({'error': 'Unauthorized'}), 401

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
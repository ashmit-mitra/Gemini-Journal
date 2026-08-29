import google.generativeai as genai
import os
api_key = os.environ.get('GOOGLE_API_KEY')
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-1.5-flash')
sample_entry = "Today I hiked a beautiful trail and thought about the project idea."
response = model.generate_content(f"Summarize this: {sample_entry}")
print(response.text)
import firebase_admin
from firebase_admin import credentials
from google.cloud import firestore

os.chdir(r"C:\Users\User\OneDrive\Desktop\Gemini Journal")
key_file = r"C:\Users\User\OneDrive\Desktop\Gemini Journal\gemini-journal-ai-1a8c1-d498859952c2.json"

cred = credentials.Certificate(key_file)
firebase_admin.initialize_app(cred, {'projectId': 'gemini-journal-ai-1a8c1'})

# Bypass firebase_admin's auto-detection and connect explicitly
raw_credentials = cred.get_credential()
db = firestore.Client(
    project='gemini-journal-ai-1a8c1',
    credentials=raw_credentials,
    database='(default)'   # note the parentheses — this is the literal internal name
)

db.collection("entries").add({
    "title": "My First Entry",
    "content": "Hello, Firestore!"
})
print("Document successfully added!")
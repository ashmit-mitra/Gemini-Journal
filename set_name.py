from dotenv import load_dotenv
load_dotenv(override=True)

import firebase_admin
from firebase_admin import credentials, auth

cred = credentials.Certificate("gemini-journal-ai-1a8c1-d498859952c2.json")
firebase_admin.initialize_app(cred, {'projectId': 'gemini-journal-ai-1a8c1'})

user = auth.get_user_by_email("ashmitmitra9@gmail.com")
auth.update_user(user.uid, display_name="Ashmit Mitra")

print("Done! Display name set to Ashmit Mitra")
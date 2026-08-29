from google import genai
import os

api_key = os.environ.get('GOOGLE_API_KEY')
client = genai.Client(api_key=api_key)

sample_entry = "Today I hiked a beautiful trail and thought about the project idea."
response = client.models.generate_content(
    model="gemini-3.6-flash",
    contents=f"Summarize this: {sample_entry}"
)
print(response.text)
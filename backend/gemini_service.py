import google.generativeai as genai
import os
from dotenv import load_dotenv

load_dotenv()

class GeminiService:
    def __init__(self, api_key=None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found. Please set it in .env file.")
        
        genai.configure(api_key=self.api_key)
        # Using gemini-flash-latest which was verified in check_models.py
        self.model = genai.GenerativeModel('gemini-flash-latest')
        self.chat = self.model.start_chat(history=[])

    def get_response(self, transcript):
        prompt = f"""
        You are an Interview Copilot. Based on the following transcript of an interview, 
        provide a concise, helpful suggestion or answer for the candidate to say.
        Keep it natural, professional, and brief (1-2 sentences).
        
        Transcript: {transcript}
        
        Suggestion:
        """
        response = self.model.generate_content(prompt)
        return response.text.strip()

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
        
        system_instruction = """
        You are a helpful Interview Copilot. Provide natural, conversational talking points that a human candidate would actually say.
        - Speak in the FIRST PERSON ("I have...", "In my experience...").
        - NO meta-advice. Never say "You should mention" or "Talk about".
        - Act as the candidate's inner voice, providing a ready-to-use professional response.
        - Keep it brief (1-3 short sentences max).
        - Correct STT errors mentally (e.g., "We're back" -> "Webpack") based on context.
        - Be technical but professional and natural.
        """
        
        # Using gemini-flash-latest with system instruction
        self.model = genai.GenerativeModel(
            model_name='gemini-flash-latest',
            system_instruction=system_instruction
        )
        self.chat = self.model.start_chat(history=[])

    def get_response(self, transcript):
        response = self.chat.send_message(transcript)
        return response.text.strip()

    def reset_history(self):
        self.chat = self.model.start_chat(history=[])

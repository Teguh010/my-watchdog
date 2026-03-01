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
        You are an Interview Copilot. Your goal is to help a candidate by providing 
        concise, professional, and natural suggestions based on the interviewer's words.
        - Be brief (1-2 sentences).
        - Maintain context of the previous parts of the conversation.
        - Note: The STT might mishear technical terms (e.g., "We're back" often means "Webpack"). 
          Correct these mentally based on the technical context.
        - provide high-level answer or talking points for technical questions.
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

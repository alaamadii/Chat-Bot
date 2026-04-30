from ai_brain.models import Context, Intent, AIResponse
import os
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

class ResponseGenerator:
    """
    Task 6: Response Generator
    LLM produces smart reply using Gemini
    """
    def __init__(self):
        # The client automatically picks up GEMINI_API_KEY from the environment
        try:
            self.client = genai.Client()
        except Exception as e:
            print(f"[Response Generator] Warning: Could not initialize Gemini client: {e}")
            self.client = None

    def generate(self, user_message: str, intent: Intent, context: Context) -> AIResponse:
        if not self.client:
            return AIResponse(
                text="Sorry, I am having trouble connecting to the server. Please try again later.",
                reasoning="Gemini Client not initialized. Missing API key?"
            )
            
        system_instruction = f"""
        You are a helpful customer service assistant for NextTech, a software and AI solutions company in Dubai.
        The user's intent has been classified as: {intent.category}.
        
        Here is the relevant information from our knowledge base:
        {chr(10).join(context.knowledge_snippets)}
        
        Rules:
        1. Answer the user's question politely in English.
        2. Only use the provided knowledge base snippets. If the answer is not in the snippets, say you don't have that information.
        3. Be concise and professional.
        """
        
        prompt = f"User Message: {user_message}"
        
        try:
            print("[Response Generator] Calling Gemini API...")
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.3,
                ),
            )
            reply = response.text
            reasoning = f"Generated using gemini-2.5-flash based on {len(context.knowledge_snippets)} KB snippets."
            
        except Exception as e:
            print(f"[Response Generator] Error calling Gemini: {e}")
            reply = "An unexpected error occurred while processing your request."
            reasoning = str(e)

        return AIResponse(
            text=reply.strip(),
            reasoning=reasoning
        )

generator = ResponseGenerator()

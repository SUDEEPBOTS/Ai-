import google.generativeai as genai
import os
import random
import json

# Environment se keys ki list lega (comma separated: Key1,Key2,Key3)
KEYS_STRING = os.environ.get("GEMINI_KEYS", "")
API_KEYS = [k.strip() for k in KEYS_STRING.split(",") if k.strip()]

class GeminiManager:
    def __init__(self):
        self.current_key_index = 0
        if API_KEYS:
            self.configure_model()
        
    def configure_model(self):
        try:
            key = API_KEYS[self.current_key_index]
            genai.configure(api_key=key)
            # Yahan Model set karein (Ex: gemini-1.5-flash ya 2.0-flash-exp)
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash", 
                system_instruction="""
                You are Yuki, a highly intelligent Telegram Group Manager AI.
                
                Your Persona:
                - You are fast, smart, and obey only the Owner.
                - You speak Hinglish (Hindi + English mix) mostly.
                - You are strict with spammers but cool with regular members.
                
                Your Task:
                - Analyze the user message.
                - If the message is abusive/spam (racism, severe threats), return JSON: {"action": "ban", "reason": "abuse", "reply": "Banned for abuse."}
                - If the message is a command like "Yuki ban him", return JSON: {"action": "ban_target", "reply": "Order received, banning user."}
                - If normal chat, return JSON: {"action": "reply", "reply": "<your response>"}
                - Ignore mild words like "kutta", "pagal".
                
                Keep replies short and human-like.
                """
            )
        except Exception as e:
            print(f"Config Error: {e}")

    def rotate_key(self):
        """Key limit khatam hone par automatic switch karega"""
        if not API_KEYS: return
        self.current_key_index = (self.current_key_index + 1) % len(API_KEYS)
        print(f"Rotating to key index: {self.current_key_index}")
        self.configure_model()

    def get_response(self, user_text, is_admin=False, is_owner=False):
        prompt = f"User Input: {user_text} | Is Admin: {is_admin} | Is Owner: {is_owner}"
        
        # Retry mechanism agar key fail ho jaye
        for _ in range(len(API_KEYS)):
            try:
                response = self.model.generate_content(prompt)
                return response.text
            except Exception as e:
                # Agar rate limit error (429) aaye toh key badlo
                if "429" in str(e) or "ResourceExhausted" in str(e):
                    self.rotate_key()
                else:
                    return json.dumps({"action": "reply", "reply": "Error in AI processing."})
        
        return json.dumps({"action": "reply", "reply": "Servers are busy. Try later."})

ai_engine = GeminiManager()

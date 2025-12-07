import google.generativeai as genai
import os
import json

# Keys load karna
KEYS_STRING = os.environ.get("GEMINI_KEYS", "")
# Agar ek hi key hai tab bhi ye logic kaam karega
API_KEYS = [k.strip() for k in KEYS_STRING.split(",") if k.strip()]

class GeminiManager:
    def __init__(self):
        self.current_key_index = 0
        self.configure_model()
        
    def configure_model(self):
        if not API_KEYS:
            print("No API Keys found!")
            return
        
        try:
            key = API_KEYS[self.current_key_index]
            genai.configure(api_key=key)
            
            # --- FIX HERE: Simple name use karein ---
            self.model = genai.GenerativeModel(
                model_name="gemini-2.5-flash", 
                system_instruction="""
                You are Yuki, a Telegram Group Manager AI.
                Your Persona: Helpful, Strict with spammers, Obey Owner.
                Output JSON format: {"action": "reply", "reply": "Your text"} or {"action": "ban", "reply": "Reason"}
                """
            )
        except Exception as e:
            print(f"Config Error: {e}")

    def rotate_key(self):
        if not API_KEYS or len(API_KEYS) <= 1: return # Agar 1 hi key hai to rotate mat karo
        self.current_key_index = (self.current_key_index + 1) % len(API_KEYS)
        self.configure_model()

    def get_response(self, user_text, is_admin=False, is_owner=False):
        if not API_KEYS:
            return json.dumps({"action": "reply", "reply": "⚠️ API Keys missing!"})

        prompt = f"User: {user_text} | Is Owner: {is_owner}"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            
            # Agar rate limit aaye aur keys hain, to rotate karo
            if ("429" in error_msg or "ResourceExhausted" in error_msg) and len(API_KEYS) > 1:
                self.rotate_key()
                try:
                    response = self.model.generate_content(prompt)
                    return response.text
                except:
                    pass
            
            return json.dumps({"action": "reply", "reply": f"⚠️ Error: {error_msg}"})

ai_engine = GeminiManager()

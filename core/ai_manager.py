import google.generativeai as genai
import os
import json

# Keys load karna
KEYS_STRING = os.environ.get("GEMINI_KEYS", "")
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
            # FIXED MODEL NAME HERE 👇
            self.model = genai.GenerativeModel(
                model_name="gemini-1.5-flash-001", 
                system_instruction="""
                You are Yuki, a Telegram Group Manager AI.
                Your Persona: Helpful, Strict with spammers, Obey Owner.
                Output JSON format: {"action": "reply", "reply": "Your text"} or {"action": "ban", "reply": "Reason"}
                """
            )
        except Exception as e:
            print(f"Config Error: {e}")

    def rotate_key(self):
        if not API_KEYS: return
        self.current_key_index = (self.current_key_index + 1) % len(API_KEYS)
        self.configure_model()

    def get_response(self, user_text, is_admin=False, is_owner=False):
        if not API_KEYS:
            return json.dumps({"action": "reply", "reply": "⚠️ API Keys missing in Vercel Settings!"})

        prompt = f"User: {user_text} | Is Owner: {is_owner}"
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "ResourceExhausted" in error_msg:
                self.rotate_key()
                try:
                    response = self.model.generate_content(prompt)
                    return response.text
                except:
                    return json.dumps({"action": "reply", "reply": "All Keys Exhausted."})
            
            # Agar model error aye, to fallback pro model par jao
            return json.dumps({"action": "reply", "reply": f"⚠️ Technical Error: {error_msg}"})

ai_engine = GeminiManager()

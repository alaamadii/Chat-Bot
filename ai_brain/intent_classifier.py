from ai_brain.models import Intent
import re

class IntentClassifier:
    """
    Task 4: Intent Classifier
    What does the user want?
    """
    def classify(self, text: str) -> Intent:
        # Mock LLM classification using simple keywords (English and Arabic)
        text_lower = text.lower()
        
        if any(word in text_lower for word in ["سعر", "اسعار", "بكم", "تكلفة", "price", "cost", "how much", "quote"]):
            return Intent(category="pricing", confidence=0.9)
            
        if any(word in text_lower for word in ["مشكلة", "شكوى", "خربان", "مساعدة", "help", "problem", "issue", "complaint", "broken"]):
            return Intent(category="support", confidence=0.85)
            
        if any(word in text_lower for word in ["كيف", "هل", "استضافة", "برمجة", "how", "what", "hosting", "language"]):
            return Intent(category="faq", confidence=0.8)
            
        return Intent(category="general", confidence=0.5)

classifier = IntentClassifier()

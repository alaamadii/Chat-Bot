from delivery.models import FormattedMessage
import re

class SafetyFilter:
    """
    Task 12: Safety Filter
    Block inappropriate content
    """
    def check(self, msg: FormattedMessage) -> FormattedMessage:
        text = msg.text.lower()
        
        # Mock blocklist
        bad_words = ["احتيال", "نصب", "scam", "fraud"]
        
        for word in bad_words:
            if word in text:
                print(f"[Safety Filter] WARNING: Blocked inappropriate word: {word}")
                msg.text = "Sorry, I cannot send this message because it contains blocked content."
                msg.is_safe = False
                return msg
                
        # Mock PII check (e.g., matching a fake credit card pattern)
        # Just an example regex
        if re.search(r'\b(?:\d[ -]*?){13,16}\b', text):
            print("[Safety Filter] WARNING: Blocked potential Credit Card number!")
            msg.text = "Sorry, the message was blocked to protect personal data."
            msg.is_safe = False
            return msg

        return msg

safety_filter = SafetyFilter()

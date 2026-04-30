import json
import os
from analytics.models import InteractionLog
from intake.models import NormalizedMessage
from ai_brain.models import FinalOutput
from actions.models import ExecutionResult
from delivery.models import DeliveryStatus
from datetime import datetime

class ConversationLogger:
    """
    Task 14: Conversation Logger
    Store all interactions & outcomes
    """
    def __init__(self, log_file="chat_logs.jsonl"):
        self.log_file = log_file

    def log_interaction(self, msg: NormalizedMessage, ai_output: FinalOutput, 
                        exec_result: ExecutionResult, status: DeliveryStatus) -> InteractionLog:
        
        log_entry = InteractionLog(
            session_id=msg.session_id,
            user_id=msg.user_id,
            intent_category=ai_output.response.reasoning.split(" ")[3].replace(".", "") if "Intent identified as" in ai_output.response.reasoning else "unknown", # Workaround to extract mock intent
            ai_confidence=ai_output.confidence_score,
            action_taken=exec_result.action_taken,
            delivery_success=status.success,
            timestamp=datetime.utcnow().isoformat()
        )
        
        # Append to JSONL file
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(log_entry.model_dump_json() + "\n")
            
        print(f"[Conversation Logger] Saved interaction log for session {msg.session_id}")
        return log_entry

logger = ConversationLogger()

import os
from datetime import datetime
from intake.models import NormalizedMessage
from ai_brain.pipeline import process_message
from actions.pipeline import execute_action
from delivery.pipeline import deliver_response
from analytics.pipeline import record_interaction, generate_dashboard

def run_test():
    # Clear old logs for clean test
    if os.path.exists("chat_logs.jsonl"):
        os.remove("chat_logs.jsonl")

    # 1. Intake Layer Mock
    test_msg_pricing = NormalizedMessage(
        session_id="test_session_123",
        user_id="+971501234567",
        channel="whatsapp",
        original_text="How much does it cost to design an e-commerce website?",
        clean_text="How much does it cost to design an e-commerce website?",
        received_at=datetime.utcnow(),
        metadata={}
    )
    
    test_msg_support = NormalizedMessage(
        session_id="test_session_456",
        user_id="+971509876543",
        channel="web_chat",
        original_text="I have a problem with my website",
        clean_text="I have a problem with my website",
        received_at=datetime.utcnow(),
        metadata={}
    )
    
    messages_to_test = [test_msg_pricing, test_msg_support]
    
    for msg in messages_to_test:
        print(f"\n=========================================")
        print(f"Testing Message from: {msg.channel} | User: {msg.user_id}")
        print(f"Content: {msg.clean_text}")
        print(f"=========================================")
        
        # 2. Run AI Brain (Tasks 4-7)
        print("--- [AI Brain Processing] ---")
        final_output = process_message(msg, history=[])
        
        # 3. Run Actions & Integrations (Tasks 8-10)
        print("\n--- [Actions & Integrations] ---")
        execution_result = execute_action(msg, final_output)
        
        # 4. Run Delivery (Tasks 11-13)
        print("\n--- [Delivery Pipeline] ---")
        delivery_status = deliver_response(execution_result, msg.channel, msg.user_id)
        
        # 5. Run Analytics (Tasks 14-16)
        print("\n--- [Analytics Pipeline] ---")
        record_interaction(msg, final_output, execution_result, delivery_status)

    # Finally, generate the dashboard
    generate_dashboard()

if __name__ == "__main__":
    run_test()

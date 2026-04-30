import os
from datetime import datetime
from intake.models import NormalizedMessage
from ai_brain.pipeline import process_message
from actions.pipeline import execute_action
from delivery.pipeline import deliver_response
from analytics.pipeline import record_interaction

def interactive_chat():
    print("==================================================")
    print("  NextTech AI Support Bot (Interactive Pipeline)  ")
    print("==================================================")
    print("Type 'exit' or 'quit' to stop.\n")
    
    session_id = "live_session_999"
    user_phone = "+971550000000"
    
    # Simple mock history list for this session
    history = []

    while True:
        try:
            user_input = input("\nYou: ")
            if user_input.lower() in ['exit', 'quit']:
                print("Exiting...")
                break
            if not user_input.strip():
                continue
                
            # 1. INTAKE
            msg = NormalizedMessage(
                session_id=session_id,
                user_id=user_phone,
                channel="whatsapp",
                original_text=user_input,
                clean_text=user_input.strip(),
                received_at=datetime.utcnow(),
                metadata={}
            )
            print(f"\n[Intake] Processed clean text -> {msg.clean_text}")
            
            # 2. AI BRAIN
            print("[AI Brain] Analyzing Intent & Generating Response...")
            final_output = process_message(msg, history=history)
            
            # 3. ACTIONS
            print(f"[Actions] Decision -> Escalate: {final_output.escalate_to_human}")
            execution_result = execute_action(msg, final_output)
            
            # 4. DELIVERY
            print("[Delivery] Formatting and Checking Safety...")
            delivery_status = deliver_response(execution_result, msg.channel, msg.user_id)
            
            # 5. ANALYTICS
            record_interaction(msg, final_output, execution_result, delivery_status)
            
            # Print the final result back to the user
            print(f"\nBot: {execution_result.message_to_user}")
            
            # Update history
            history.append(msg)
            
        except KeyboardInterrupt:
            print("\nExiting...")
            break
        except Exception as e:
            print(f"\n[Error] Pipeline failed: {e}")

if __name__ == "__main__":
    interactive_chat()

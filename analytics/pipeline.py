from intake.models import NormalizedMessage
from ai_brain.models import FinalOutput
from actions.models import ExecutionResult
from delivery.models import DeliveryStatus
from analytics.logger import logger
from analytics.updater import updater
from analytics.dashboard import dashboard

def record_interaction(msg: NormalizedMessage, ai_output: FinalOutput, 
                       exec_result: ExecutionResult, status: DeliveryStatus):
    """
    Orchestrates the Analytics layer (Tasks 14-16).
    """
    # Task 14: Log the conversation
    log = logger.log_interaction(msg, ai_output, exec_result, status)
    
    # Task 15: Check if KB needs updating based on confidence
    updater.check_for_gaps(log)

def generate_dashboard():
    # Task 16: Print the daily metrics report
    dashboard.generate_report()

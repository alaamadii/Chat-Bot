from actions.models import ExecutionResult
from ai_brain.models import FinalOutput
from intake.models import NormalizedMessage
from actions.router import router

def execute_action(message: NormalizedMessage, ai_output: FinalOutput) -> ExecutionResult:
    """
    Orchestrates the Actions & Integrations layer (Tasks 8-10).
    """
    return router.route(message, ai_output)

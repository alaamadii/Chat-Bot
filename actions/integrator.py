from intake.models import NormalizedMessage

class APIIntegrator:
    """
    Task 9: API Integrator
    CRM, ERP, order systems
    """
    def create_crm_lead(self, message: NormalizedMessage) -> str:
        # Simulate creating a lead in a CRM like Salesforce
        print(f"[API Integrator] Calling CRM API to create lead for user {message.user_id}...")
        ticket_id = "LD-99214"
        return ticket_id
        
    def check_order_status(self, user_id: str) -> str:
        # Simulate an ERP or Shopify check
        print(f"[API Integrator] Calling Order API for user {user_id}...")
        return "Order shipped"

integrator = APIIntegrator()

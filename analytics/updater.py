from analytics.models import InteractionLog

class KBUpdater:
    """
    Task 15: KB Updater
    Improve answers from feedback
    """
    def check_for_gaps(self, log: InteractionLog):
        # Simulate feedback loop: if confidence is low, flag for review
        if log.ai_confidence < 0.6:
            print(f"[KB Updater] ALERT: Low confidence ({log.ai_confidence}) for topic '{log.intent_category}'.")
            print(f"[KB Updater] Action required: Add more FAQs about '{log.intent_category}' to knowledge_base.json!")

updater = KBUpdater()

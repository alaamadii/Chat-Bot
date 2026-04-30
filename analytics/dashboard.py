import json
import os
from analytics.models import DashboardReport

class DashboardBuilder:
    """
    Task 16: Dashboard Builder
    Metrics, CSAT & bottleneck reports
    """
    def __init__(self, log_file="chat_logs.jsonl"):
        self.log_file = log_file

    def generate_report(self) -> DashboardReport:
        if not os.path.exists(self.log_file):
            print("[Dashboard Builder] No logs found.")
            return DashboardReport(total_interactions=0, handoff_rate=0.0, average_confidence=0.0)

        total = 0
        handoffs = 0
        confidence_sum = 0.0

        with open(self.log_file, "r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    data = json.loads(line)
                    total += 1
                    confidence_sum += data.get("ai_confidence", 0)
                    if data.get("action_taken") == "sent_to_agent":
                        handoffs += 1

        avg_conf = (confidence_sum / total) if total > 0 else 0
        handoff_rate = (handoffs / total) * 100 if total > 0 else 0

        report = DashboardReport(
            total_interactions=total,
            handoff_rate=handoff_rate,
            average_confidence=avg_conf
        )
        
        self._print_dashboard(report)
        return report

    def _print_dashboard(self, report: DashboardReport):
        print("\n=========================================")
        print("[ DAILY CHATBOT METRICS DASHBOARD ]")
        print("=========================================")
        print(f"Total Interactions: {report.total_interactions}")
        print(f"Average AI Confidence: {report.average_confidence:.2f} / 1.0")
        print(f"Human Handoff Rate: {report.handoff_rate:.1f}%")
        
        if report.handoff_rate > 30:
            print("[!] BOTTLENECK DETECTED: Handoff rate is too high. Check KB Updater alerts!")
        print("=========================================\n")

dashboard = DashboardBuilder()

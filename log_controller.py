from datetime import datetime


class LogController:
    def __init__(self, app):
        self.app = app

    def clear_logs(self):
        self.app.log_lines = []
        self.app.log_label.text = "System Log:\n"

    def write_log(self, text):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.app.log_lines.append(f"[{timestamp}] {text}")
        # Keep log compact to avoid UI slowdown.
        if len(self.app.log_lines) > 120:
            self.app.log_lines = self.app.log_lines[-120:]
        self.app.log_label.text = "System Log:\n" + "\n".join(self.app.log_lines)

    def on_scan_status(self, text):
        if text in {"Scan started", "Scanning Bluetooth..."}:
            # Clear logs at each new scan round.
            self.clear_logs()
        self.app.status_label.text = text
        self.write_log(text)

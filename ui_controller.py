class UIController:
    def __init__(self, app):
        self.app = app

    def show_scan(self):
        self.app.manager.current = "scan"

    def show_log(self):
        self.app.manager.current = "log"

    def refresh_spinner_values(self, *_):
        self.app.device_spinner.values = self.app.repo.spinner_values()
        self.app.scan_list_label.text = self.app.repo.scan_list_text()
        if self.app.repo.selected_address is None:
            return
        selected = self.app.repo.get_device(self.app.repo.selected_address)
        if selected is None:
            return
        rssi_text = (
            f"{selected['rssi']} dBm"
            if isinstance(selected["rssi"], int)
            else "N/A"
        )
        self.app.device_spinner.text = (
            f"{selected['name']} | {self.app.repo.selected_address} | "
            f"{rssi_text} | {selected.get('source', 'n/a')}"
        )

    def on_select_device(self, _spinner, text):
        address = self.app.repo.select_from_spinner_text(text)
        if not address:
            return
        self.app.scanner.set_selected_device(address)
        self.app._write_service_state()
        self.app.write_log(f"Selected device: {text}")
        self.app.apply_selected_device_output(0)

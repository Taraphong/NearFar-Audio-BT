class RSSIRepository:
    def __init__(self):
        self.devices = {}
        self.selected_address = None

    def update_device(self, address, name, rssi, source="unknown"):
        prev = self.devices.get(address, {})
        resolved_rssi = int(rssi) if rssi is not None else prev.get("rssi")
        self.devices[address] = {
            "name": name or "Unknown",
            "rssi": resolved_rssi,
            "source": source,
        }
        return self.devices[address]

    def get_device(self, address):
        return self.devices.get(address)

    def sorted_items(self):
        return sorted(
            self.devices.items(),
            key=lambda item: (item[1]["rssi"] if isinstance(item[1]["rssi"], int) else -1000),
            reverse=True,
        )

    def spinner_values(self):
        values = []
        for address, data in self.sorted_items():
            rssi_text = f"{data['rssi']} dBm" if isinstance(data["rssi"], int) else "N/A"
            values.append(
                f"{data['name']} | {address} | {rssi_text} | {data.get('source', 'n/a')}"
            )
        return tuple(values)

    @staticmethod
    def estimate_distance_m(rssi, tx_power=-59, path_loss_exponent=2.0):
        if not isinstance(rssi, int):
            return None
        return 10 ** ((tx_power - float(rssi)) / (10 * path_loss_exponent))

    def scan_list_text(self):
        if not self.devices:
            return "No device scanned yet"
        rows = []
        for address, data in self.sorted_items():
            rssi = data.get("rssi")
            rssi_text = f"{rssi} dBm" if isinstance(rssi, int) else "N/A"
            dist = self.estimate_distance_m(rssi)
            dist_text = f"{dist:.2f} m" if isinstance(dist, float) else "N/A"
            rows.append(
                f"{data.get('name', 'Unknown')}\n"
                f"  {address}\n"
                f"  RSSI: {rssi_text} | Distance: {dist_text} | {data.get('source', 'n/a')}"
            )
        return "\n\n".join(rows)

    def select_from_spinner_text(self, text):
        if " | " not in text:
            return None
        parts = text.split(" | ")
        if len(parts) < 2:
            return None
        self.selected_address = parts[1].strip()
        return self.selected_address

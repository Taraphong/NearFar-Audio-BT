from time import monotonic


class RSSIRepository:
    def __init__(self):
        self.devices = {}
        self.selected_address = None
        self._ema_alpha = 0.4

    def update_device(self, address, name, rssi, source="unknown"):
        prev = self.devices.get(address, {})
        now = monotonic()
        raw_rssi = int(rssi) if rssi is not None else prev.get("raw_rssi")
        prev_filtered = prev.get("filtered_rssi")
        if isinstance(raw_rssi, int):
            if isinstance(prev_filtered, (int, float)):
                filtered_rssi = round(
                    (self._ema_alpha * float(raw_rssi))
                    + ((1.0 - self._ema_alpha) * float(prev_filtered))
                )
            else:
                filtered_rssi = int(raw_rssi)
        else:
            filtered_rssi = prev_filtered
        self.devices[address] = {
            "name": name or "Unknown",
            "raw_rssi": raw_rssi,
            "filtered_rssi": filtered_rssi,
            "rssi": filtered_rssi,
            "source": source,
            "updated_at": now,
        }
        return self.devices[address]

    def get_device(self, address):
        return self.devices.get(address)

    def sorted_items(self):
        return sorted(
            self.devices.items(),
            key=lambda item: (
                item[1]["filtered_rssi"]
                if isinstance(item[1].get("filtered_rssi"), int)
                else -1000
            ),
            reverse=True,
        )

    def spinner_values(self):
        values = []
        for address, data in self.sorted_items():
            filtered = data.get("filtered_rssi")
            raw = data.get("raw_rssi")
            filtered_text = f"{filtered} dBm" if isinstance(filtered, int) else "N/A"
            raw_text = f"{raw} dBm" if isinstance(raw, int) else "N/A"
            values.append(
                f"{data['name']} | {address} | F:{filtered_text} R:{raw_text} | {data.get('source', 'n/a')}"
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
            filtered = data.get("filtered_rssi")
            raw = data.get("raw_rssi")
            filtered_text = f"{filtered} dBm" if isinstance(filtered, int) else "N/A"
            raw_text = f"{raw} dBm" if isinstance(raw, int) else "N/A"
            dist = self.estimate_distance_m(filtered)
            dist_text = f"{dist:.2f} m" if isinstance(dist, float) else "N/A"
            rows.append(
                f"{data.get('name', 'Unknown')}\n"
                f"  {address}\n"
                f"  RSSI(F): {filtered_text} | RSSI(R): {raw_text}\n"
                f"  Distance: {dist_text} | {data.get('source', 'n/a')}"
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

from kivy.uix.boxlayout import BoxLayout
from kivy.uix.button import Button
from kivy.uix.label import Label
from kivy.uix.screenmanager import NoTransition, Screen, ScreenManager
from kivy.uix.scrollview import ScrollView
from kivy.uix.spinner import Spinner


def build_main_ui(app):
    root = BoxLayout(orientation="vertical", padding=8, spacing=8)

    nav = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
    app.scan_page_btn = Button(text="Scan")
    app.log_page_btn = Button(text="Log")
    nav.add_widget(app.scan_page_btn)
    nav.add_widget(app.log_page_btn)
    root.add_widget(nav)

    app.manager = ScreenManager(transition=NoTransition())

    scan_screen = Screen(name="scan")
    scan_layout = BoxLayout(orientation="vertical", padding=8, spacing=8)

    app.status_label = Label(
        text="Initializing...",
        size_hint_y=None,
        height="44dp",
        bold=True,
        halign="left",
        valign="middle",
    )
    app.status_label.bind(size=app._resize_status)
    scan_layout.add_widget(app.status_label)

    app.rssi_label = Label(
        text="Selected RSSI: N/A",
        size_hint_y=None,
        height="36dp",
        halign="left",
        valign="middle",
    )
    app.rssi_label.bind(size=app._resize_rssi)
    scan_layout.add_widget(app.rssi_label)

    app.device_spinner = Spinner(
        text="Select smart watch device",
        values=(),
        size_hint_y=None,
        height="44dp",
    )
    app.device_spinner.bind(text=app.ui_controller.on_select_device)
    scan_layout.add_widget(app.device_spinner)

    button_row = BoxLayout(size_hint_y=None, height="44dp", spacing=8)
    app.scan_btn = Button(text="Start Scan")
    app.stop_btn = Button(text="Stop Scan")
    button_row.add_widget(app.scan_btn)
    button_row.add_widget(app.stop_btn)
    scan_layout.add_widget(button_row)

    scan_scroll = ScrollView(size_hint_y=1)
    app.scan_list_label = Label(
        text="No device scanned yet",
        size_hint_y=None,
        halign="left",
        valign="top",
    )
    app.scan_list_label.bind(texture_size=app.scan_list_label.setter("size"))
    scan_scroll.add_widget(app.scan_list_label)
    scan_layout.add_widget(scan_scroll)

    scan_screen.add_widget(scan_layout)
    app.manager.add_widget(scan_screen)

    log_screen = Screen(name="log")
    log_layout = BoxLayout(orientation="vertical", padding=8, spacing=8)
    clear_log_btn = Button(text="Clear Log", size_hint_y=None, height="44dp")
    clear_log_btn.bind(on_release=lambda *_: app.clear_logs())
    log_layout.add_widget(clear_log_btn)

    scroll = ScrollView(size_hint_y=1)
    app.log_label = Label(
        text="System Log:\n",
        size_hint_y=None,
        halign="left",
        valign="top",
    )
    app.log_label.bind(texture_size=app.log_label.setter("size"))
    scroll.add_widget(app.log_label)
    log_layout.add_widget(scroll)
    log_screen.add_widget(log_layout)
    app.manager.add_widget(log_screen)

    root.add_widget(app.manager)

    app.scan_page_btn.bind(on_release=lambda *_: app.show_scan())
    app.log_page_btn.bind(on_release=lambda *_: app.show_log())
    app.scan_btn.bind(on_release=lambda *_: app.scanner.start_scan())
    app.stop_btn.bind(on_release=lambda *_: app.scanner.stop_scan())
    return root

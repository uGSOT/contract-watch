from app import create_app
import threading
import time
import webbrowser


app = create_app()


if __name__ == "__main__":
    # 5000 is claimed by macOS's AirPlay Receiver on most Macs, so we default
    # to 5050 instead of fighting it.
    port = 5050
    url = f"http://127.0.0.1:{port}/"
    print(f"\n  Contract Watch is running at http://127.0.0.1:{port}\n")
    print(f"  Landing page : http://127.0.0.1:{port}/")
    print(f"  Dashboard    : http://127.0.0.1:{port}/dashboard\n")
    print("  Keep this terminal open while you use the app.\n")

    def _open_browser():
        time.sleep(1.2)
        webbrowser.open(url)

    threading.Thread(target=_open_browser, daemon=True).start()

    # use_reloader=False keeps the process alive when started in the background
    app.run(debug=True, host="127.0.0.1", port=port, use_reloader=False)
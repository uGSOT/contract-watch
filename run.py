from app import create_app


app = create_app()


if __name__ == "__main__":
    # 5000 is claimed by macOS's AirPlay Receiver on most Macs, so we default
    # to 5050 instead of fighting it.
    app.run(debug=True, port=5050)
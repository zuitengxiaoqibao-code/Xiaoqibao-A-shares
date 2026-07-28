def run_window(url: str) -> None:
    try:
        import webview
    except ImportError as error:
        raise RuntimeError("pywebview is not installed") from error
    webview.create_window(
        "小七宝量化决策台",
        url,
        width=1500,
        height=920,
        min_size=(1080, 700),
        background_color="#06080d",
    )
    webview.start(debug=False)

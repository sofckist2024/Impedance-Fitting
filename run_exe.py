"""PyInstaller 진입점: 번들된 Streamlit 앱을 실행하고 브라우저를 연다.

이 파일을 PyInstaller 로 빌드하면, exe 를 더블클릭했을 때
로컬 Streamlit 서버가 뜨고 기본 브라우저가 자동으로 열린다.
"""
import os
import sys
import threading
import time
import webbrowser

from streamlit.web import cli as stcli

PORT = 8501


def _resource(rel: str) -> str:
    """번들(onefile) 또는 실행 폴더(onedir)에서 리소스 경로를 찾는다."""
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, rel)


def _open_browser() -> None:
    time.sleep(3.0)  # 서버가 뜰 시간을 준 뒤 브라우저 열기
    webbrowser.open(f"http://localhost:{PORT}")


def main() -> None:
    app_path = _resource("app.py")
    # app.py 가 impedance_fit 를 import 할 수 있도록 경로 추가
    sys.path.insert(0, os.path.dirname(app_path))

    threading.Thread(target=_open_browser, daemon=True).start()

    sys.argv = [
        "streamlit", "run", app_path,
        f"--server.port={PORT}",
        "--server.headless=true",            # 브라우저는 우리가 직접 연다
        "--global.developmentMode=false",
        "--browser.gatherUsageStats=false",
    ]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()

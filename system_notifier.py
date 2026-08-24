import platform
import subprocess

def notify(title: str, message: str):
    system = platform.system().lower()

    try:
        if system == "windows":
            # Bez zewnętrznych zależności: fallback do MessageBox PowerShell.
            script = f'[System.Reflection.Assembly]::LoadWithPartialName("PresentationFramework");[System.Windows.MessageBox]::Show("{message}","{title}")'
            subprocess.Popen(["powershell", "-NoProfile", "-Command", script])
            return True

        if system == "darwin":
            subprocess.Popen([
                "osascript",
                "-e",
                f'display notification "{message}" with title "{title}"'
            ])
            return True

        subprocess.Popen(["notify-send", title, message])
        return True

    except Exception:
        return False

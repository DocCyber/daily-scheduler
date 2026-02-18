"""Local chime and TTS client - plays a beep and speaks announcements on the local machine."""
import subprocess
import winsound


class LocalChimeClient:
    """Drop-in replacement for VoiceMonkeyClient that announces locally via chime + TTS."""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled

    def announce(self, message: str) -> bool:
        """Play a chime then speak the message using Windows TTS."""
        if not self.enabled:
            return True

        try:
            # Chime first
            winsound.MessageBeep(winsound.MB_OK)

            # Sanitize message to avoid PowerShell injection
            safe_message = message.replace('"', '').replace("'", '').replace(';', '').replace('`', '')

            # Non-blocking TTS via PowerShell SpeechSynthesizer (no extra installs needed)
            subprocess.Popen(
                [
                    "powershell", "-NoProfile", "-NonInteractive", "-Command",
                    f'Add-Type -AssemblyName System.Speech; '
                    f'(New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak("{safe_message}")'
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            return True
        except Exception as e:
            print(f"[LocalChime] Error: {e}")
            return False

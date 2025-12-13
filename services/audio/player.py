import asyncio
import logging
import os
import platform
import subprocess
import time

log = logging.getLogger("audio_player")

class AudioPlayer:
    """
    Handles audio playback using system command-line players.
    Supports macOS (afplay) and Linux (paplay/aplay).
    """
    
    def __init__(self):
        self._audio_process: subprocess.Popen = None
        self._cancelled = False

    def play_audio(self, audio_path: str) -> bool:
        """
        Play audio file ephemerally (no file retention).
        Uses system audio player (afplay on macOS, aplay/paplay on Linux).
        
        Args:
            audio_path: Path to the audio file
        
        Returns:
            True if playback started successfully
        """
        
        if not os.path.exists(audio_path):
            log.warning(f"Audio file not found: {audio_path}")
            return False
        
        try:
            system = platform.system()
            
            if system == "Darwin":  # macOS
                cmd = ["afplay", audio_path]
            elif system == "Linux":
                # Try paplay (PulseAudio) first, fall back to aplay
                cmd = ["paplay", audio_path]
            elif system == "Windows":
                # Use ffplay on Windows
                # -nodisp: No window
                # -autoexit: Exit when done
                # -hide_banner: Less log spam
                cmd = ["ffplay", "-nodisp", "-autoexit", "-hide_banner", audio_path]
            else:
                log.warning(f"Unsupported platform for audio playback: {system}")
                return False
            
            # Ensure previous playback is stopped
            self.stop_playback()
            
            # Reset cancelled flag for new playback (MUST be after stop_playback which sets it True)
            self._cancelled = False
            
            # Start audio playback as subprocess
            # Note: Don't capture stderr on Windows as it can block
            self._audio_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,  # CRITICAL: Don't capture stderr - causes blocking
                creationflags=subprocess.CREATE_NO_WINDOW if system == "Windows" else 0
            )
            
            # Brief check for immediate crash
            import time as time_mod
            time_mod.sleep(0.1)
            if self._audio_process.poll() is not None:
                log.error(f"Audio player crashed immediately (code {self._audio_process.returncode})")
                return False
            
            log.info(f"🔊 Playing audio: {os.path.basename(audio_path)}")
            return True
            
        except FileNotFoundError:
            log.warning(f"Audio player not found. Install afplay (macOS) or paplay/aplay (Linux)")
            return False
        except Exception as e:
            log.error(f"Error playing audio: {e}")
            return False

    def stop_playback(self):
        """
        Stop current playback immediately.
        """
        self._cancelled = True
        if self._audio_process:
            if self._audio_process.poll() is None:
                try:
                    self._audio_process.terminate()
                    # log.info("🔇 Stopped audio playback")
                except Exception as e:
                    log.warning(f"Error terminating audio process: {e}")
            self._audio_process = None

    async def wait_for_playback(self, timeout: float = 30.0) -> bool:
        """
        Wait for current audio playback to complete.
        
        Args:
            timeout: Maximum seconds to wait
        
        Returns:
            True if playback completed, False if cancelled or timeout
        """
        if not self._audio_process:
            return True
        
        start = time.time()
        while time.time() - start < timeout:
            if self._cancelled:
                return False
            
            if self._audio_process.poll() is not None:
                return True
            
            await asyncio.sleep(0.1)
        
        # Timeout - kill process
        log.warning(f"Audio playback timed out after {timeout}s")
        self.stop_playback()
        return False

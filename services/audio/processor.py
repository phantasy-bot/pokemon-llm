import logging
import os
import subprocess
from typing import Optional

log = logging.getLogger("audio_processor")

class AudioProcessor:
    """
    Handles audio processing tasks using ffmpeg and mutagen/soundfile.
    Includes duration detection and speed/pitch adjustment.
    """
    
    def get_duration_ms(self, audio_path: str) -> Optional[int]:
        """
        Get audio duration in milliseconds.
        
        Returns:
            Duration in milliseconds, or None if detection fails
        """
        if not os.path.exists(audio_path):
            return None
            
        try:
            from mutagen import File as MutagenFile
            audio = MutagenFile(audio_path)
            if audio and audio.info:
                duration_ms = int(audio.info.length * 1000)
                # log.info(f"🔊 Audio duration: {duration_ms}ms ({audio.info.length:.2f}s)")
                return duration_ms
        except ImportError:
            log.warning("mutagen not installed, trying fallback audio duration detection")
            # Fallback for FLAC using soundfile or wave
            try:
                import soundfile as sf
                with sf.SoundFile(audio_path) as f:
                    duration_ms = int((len(f) / f.samplerate) * 1000)
                    log.info(f"🔊 Audio duration (soundfile): {duration_ms}ms")
                    return duration_ms
            except ImportError:
                log.warning("soundfile not installed, cannot detect audio duration")
            except Exception as e:
                log.warning(f"soundfile fallback failed: {e}")
        except Exception as e:
            log.warning(f"Failed to get audio duration: {e}")
        
        return None
    
    def process_speed_pitch(self, audio_path: str, speed: float = 1.0, pitch: float = 0) -> str:
        """
        Apply speed and pitch adjustments to audio using ffmpeg.
        
        Args:
            audio_path: Path to the input audio file
            speed: Speed multiplier (1.0 = normal)
            pitch: Pitch shift in semitones (0 = normal)
            
        Returns:
            Path to processed audio file (or original if no processing needed)
        """
        # Skip if no processing needed
        if speed == 1.0 and pitch == 0:
            return audio_path
        
        try:
            # Build output path
            base, ext = os.path.splitext(audio_path)
            processed_path = f"{base}_processed{ext}"
            
            # Build ffmpeg filter chain
            filters = []
            
            # Detect actual sample rate from the audio file
            original_sample_rate = 44100  # Default fallback
            try:
                from mutagen import File as MutagenFile
                audio = MutagenFile(audio_path)
                if audio and audio.info and hasattr(audio.info, 'sample_rate'):
                    original_sample_rate = audio.info.sample_rate
            except Exception as e:
                log.warning(f"🔊 Could not detect sample rate, using 44100Hz default: {e}")
            
            # Pitch adjustment using asetrate + aresample + atempo compensation
            if pitch != 0:
                pitch_factor = 2 ** (pitch / 12)
                
                # Method: Change sample rate to shift pitch, then resample back and 
                # compensate tempo with atempo (1/pitch_factor)
                new_rate = int(original_sample_rate * pitch_factor)
                filters.append(f"asetrate={new_rate}")
                filters.append(f"aresample={original_sample_rate}")
                
                # Tempo compensation: pitch up = speed up, so we slow down to compensate
                tempo_comp = 1.0 / pitch_factor
                
                comp = tempo_comp
                while comp > 2.0:
                    filters.append("atempo=2.0")
                    comp /= 2.0
                while comp < 0.5:
                    filters.append("atempo=0.5")
                    comp *= 2.0
                if abs(comp - 1.0) > 0.001:
                    filters.append(f"atempo={comp:.6f}")
            
            # Speed adjustment using atempo (applied after pitch compensation)
            if speed != 1.0:
                s = speed
                # atempo only supports 0.5-2.0, so chain multiple if needed
                while s > 2.0:
                    filters.append("atempo=2.0")
                    s /= 2.0
                while s < 0.5:
                    filters.append("atempo=0.5")
                    s *= 2.0
                if s != 1.0:
                    filters.append(f"atempo={s:.4f}")
            
            if not filters:
                return audio_path
            
            filter_str = ",".join(filters)
            # log.info(f"🔊 Processing audio: speed={speed}x, pitch={pitch} semitones")
            
            # Run ffmpeg
            cmd = [
                "ffmpeg", "-y", "-i", audio_path,
                "-af", filter_str,
                "-acodec", "flac" if audio_path.endswith(".flac") else "libmp3lame",
                processed_path
            ]
            
            result = subprocess.run(
                cmd, 
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE,
                timeout=30
            )
            
            if result.returncode == 0 and os.path.exists(processed_path):
                # Remove original, rename processed
                os.remove(audio_path)
                os.rename(processed_path, audio_path)
                return audio_path
            else:
                log.warning(f"🔊 FFmpeg processing failed: {result.stderr.decode()[:200]}")
                return audio_path
                
        except FileNotFoundError:
            log.warning("🔊 ffmpeg not found, skipping audio processing. Install with: brew install ffmpeg")
            return audio_path
        except subprocess.TimeoutExpired:
            log.warning("🔊 FFmpeg processing timed out")
            return audio_path
        except Exception as e:
            log.warning(f"🔊 Audio processing failed: {e}")
            return audio_path

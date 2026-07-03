"""Captura de audio desde micrófono y conversión a texto."""

from __future__ import annotations

import os
import tempfile
from typing import Any, Optional, Union


def transcribe_audio_bytes(audio_bytes: bytes, language: str = "es-ES") -> str:
    """
    Transcribe audio (WAV/OGG/WEBM bytes) a texto usando SpeechRecognition (Google).
    Retorna el texto reconocido o lanza RuntimeError si falla.
    """
    import speech_recognition as sr

    # Detectar extensión por cabecera
    suffix = ".wav"
    if audio_bytes[:4] == b"OggS":
        suffix = ".ogg"
    elif audio_bytes[:4] == b"fLaC":
        suffix = ".flac"
    elif len(audio_bytes) > 8 and audio_bytes[4:8] == b"ftyp":
        suffix = ".mp4"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        # Intentar como archivo de audio directo
        try:
            with sr.AudioFile(tmp_path) as source:
                audio_data = sr.Recognizer().record(source)
            return sr.Recognizer().recognize_google(audio_data, language=language)
        except Exception:
            # Convertir con pydub si el formato no es WAV (p. ej. webm de st.audio_input)
            return _transcribe_via_pydub(tmp_path, language)
    except sr.UnknownValueError:
        raise RuntimeError("No se pudo entender el audio. Intenta hablar más claro.")
    except sr.RequestError as e:
        raise RuntimeError(f"Error al conectar con el servicio de reconocimiento: {e}")
    except Exception as e:
        raise RuntimeError(f"Error al procesar el audio: {e}")
    finally:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass


def _transcribe_via_pydub(path: str, language: str) -> str:
    """Convierte a WAV en memoria y transcribe (para webm/ogg de navegadores)."""
    import speech_recognition as sr

    try:
        from pydub import AudioSegment
    except ImportError:
        raise RuntimeError(
            "No se pudo leer el formato de audio. "
            "Graba de nuevo o usa texto/archivo."
        )

    audio = AudioSegment.from_file(path)
    wav_path = path + ".wav"
    audio.export(wav_path, format="wav")
    try:
        with sr.AudioFile(wav_path) as source:
            audio_data = sr.Recognizer().record(source)
        return sr.Recognizer().recognize_google(audio_data, language=language)
    finally:
        try:
            os.unlink(wav_path)
        except OSError:
            pass


def render_audio_recorder(key: Union[str, int] = "default") -> Optional[bytes]:
    """
    Muestra el widget de grabación. Preferimos st.audio_input (nativo, estable en Cloud).
    Retorna bytes del audio o None.
    """
    import streamlit as st

    # Widget nativo de Streamlit (no depende de componentes de terceros)
    if hasattr(st, "audio_input"):
        audio_file = st.audio_input(
            "Graba un segmento del proceso",
            key=f"audio_in_{key}",
        )
        if audio_file is not None:
            return audio_file.getvalue()
        return None

    # Fallback legacy
    try:
        from audio_recorder_streamlit import audio_recorder
        return audio_recorder(
            text="Haz clic para grabar",
            recording_color="#e74c3c",
            neutral_color="#2c3e50",
            icon_size="2x",
            key=f"audio_rec_{key}",
        )
    except Exception:
        st.warning("Grabación de audio no disponible en este entorno.")
        return None


def new_segment(
    segment_id: int, text: str = "", audio_bytes: Optional[bytes] = None
) -> dict[str, Any]:
    return {
        "id": segment_id,
        "text": text,
        "audio_bytes": audio_bytes,
    }


def merge_segment_texts(segments: list, separator: str = "\n\n") -> str:
    """Une los textos de todos los segmentos en orden."""
    parts = [s.get("text", "").strip() for s in segments if s.get("text", "").strip()]
    return separator.join(parts)

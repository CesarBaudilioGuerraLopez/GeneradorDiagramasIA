"""Captura de audio desde micrófono y conversión a texto."""

import os
import tempfile
from typing import Any


def transcribe_audio_bytes(audio_bytes: bytes, language: str = "es-ES") -> str:
    """
    Transcribe audio (WAV/OGG bytes) a texto usando SpeechRecognition (Google).
    Retorna el texto reconocido o lanza RuntimeError si falla.
    """
    import speech_recognition as sr

    recognizer = sr.Recognizer()

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    try:
        with sr.AudioFile(tmp_path) as source:
            audio_data = recognizer.record(source)
        text = recognizer.recognize_google(audio_data, language=language)
        return text
    except sr.UnknownValueError:
        raise RuntimeError("No se pudo entender el audio. Intenta hablar más claro.")
    except sr.RequestError as e:
        raise RuntimeError(f"Error al conectar con el servicio de reconocimiento: {e}")
    finally:
        os.unlink(tmp_path)


def render_audio_recorder(key: str | int = "default"):
    """
    Muestra el widget de grabación de audio en Streamlit.
    Retorna bytes del audio grabado o None si no hay grabación.
    """
    try:
        from audio_recorder_streamlit import audio_recorder
        return audio_recorder(
            text="Haz clic para grabar",
            recording_color="#e74c3c",
            neutral_color="#2c3e50",
            icon_size="2x",
            key=f"audio_rec_{key}",
        )
    except ImportError:
        import streamlit as st
        st.warning(
            "El módulo `audio-recorder-streamlit` no está instalado. "
            "Ejecuta: `pip install audio-recorder-streamlit`"
        )
        return None


def new_segment(segment_id: int, text: str = "", audio_bytes: bytes | None = None) -> dict[str, Any]:
    return {
        "id": segment_id,
        "text": text,
        "audio_bytes": audio_bytes,
    }


def merge_segment_texts(segments: list[dict[str, Any]], separator: str = "\n\n") -> str:
    """Une los textos de todos los segmentos en orden."""
    parts = [s.get("text", "").strip() for s in segments if s.get("text", "").strip()]
    return separator.join(parts)

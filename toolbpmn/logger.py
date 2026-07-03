"""Registro de uso en SQLite — quién usa la herramienta, cuántos tokens, qué exporta."""

import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

DB_PATH = Path(__file__).parent / "usage.db"

# Costo referencial Claude Sonnet (USD por token)
COST_INPUT_PER_TOKEN  = 3e-6    # $3 / 1M tokens
COST_OUTPUT_PER_TOKEN = 15e-6   # $15 / 1M tokens


def _conn() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, check_same_thread=False)
    con.row_factory = sqlite3.Row
    return con


def init_db() -> None:
    with _conn() as con:
        con.executescript("""
            CREATE TABLE IF NOT EXISTS analyses (
                id             INTEGER PRIMARY KEY AUTOINCREMENT,
                ts             TEXT    NOT NULL,
                usuario        TEXT,
                proceso        TEXT,
                metodo_entrada TEXT,
                chars_entrada  INTEGER DEFAULT 0,
                tokens_entrada INTEGER DEFAULT 0,
                tokens_salida  INTEGER DEFAULT 0,
                tokens_total   INTEGER DEFAULT 0,
                costo_usd      REAL    DEFAULT 0,
                modelo         TEXT,
                duracion_seg   REAL    DEFAULT 0,
                exito          INTEGER DEFAULT 1
            );
            CREATE TABLE IF NOT EXISTS exports (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                ts          TEXT NOT NULL,
                usuario     TEXT,
                proceso     TEXT,
                tipo_export TEXT
            );
        """)


def log_analysis(
    usuario:  str,
    proceso:  str,
    metodo:   str,
    chars:    int,
    tok_in:   int,
    tok_out:  int,
    modelo:   str,
    dur_seg:  float,
    exito:    bool = True,
) -> None:
    tok_total = (tok_in or 0) + (tok_out or 0)
    costo     = (tok_in or 0) * COST_INPUT_PER_TOKEN + (tok_out or 0) * COST_OUTPUT_PER_TOKEN
    with _conn() as con:
        con.execute(
            """INSERT INTO analyses
               (ts, usuario, proceso, metodo_entrada, chars_entrada,
                tokens_entrada, tokens_salida, tokens_total, costo_usd,
                modelo, duracion_seg, exito)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (datetime.now().isoformat(), usuario or "Anónimo", proceso or "",
             metodo, chars, tok_in or 0, tok_out or 0, tok_total, costo,
             modelo, round(dur_seg, 2), int(exito)),
        )


def log_export(usuario: str, proceso: str, tipo: str) -> None:
    with _conn() as con:
        con.execute(
            "INSERT INTO exports (ts, usuario, proceso, tipo_export) VALUES (?,?,?,?)",
            (datetime.now().isoformat(), usuario or "Anónimo", proceso or "", tipo),
        )


def get_analyses() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM analyses ORDER BY ts DESC", con,
            parse_dates=["ts"],
        )


def get_exports() -> pd.DataFrame:
    with _conn() as con:
        return pd.read_sql(
            "SELECT * FROM exports ORDER BY ts DESC", con,
            parse_dates=["ts"],
        )


def summary_stats() -> dict:
    with _conn() as con:
        row = con.execute("""
            SELECT
                COUNT(*)                         AS total_analisis,
                COUNT(DISTINCT usuario)          AS usuarios_unicos,
                COALESCE(SUM(tokens_total),  0)  AS tokens_totales,
                COALESCE(SUM(costo_usd),     0)  AS costo_total_usd,
                COALESCE(AVG(duracion_seg),  0)  AS duracion_promedio,
                COALESCE(SUM(CASE WHEN exito=1 THEN 1 ELSE 0 END), 0) AS exitosos
            FROM analyses
        """).fetchone()
        exp = con.execute("SELECT COUNT(*) FROM exports").fetchone()[0]
    d = dict(row)
    d["total_exports"] = exp
    return d


# Inicializar al importar
init_db()

# app/db/db_client.py  (reemplaza tu módulo de engine/session)
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Optional

from dotenv import load_dotenv, find_dotenv
from supabase import create_client, Client

load_dotenv(find_dotenv())  # carga variables de .env

SUPABASE_URL = os.getenv("SUPABASE_URL")    # p.ej. https://xxxx.supabase.co
SUPABASE_KEY = os.getenv("SUPABASE_KEY")    # anon o service_role (backend seguro)

if not SUPABASE_URL or not SUPABASE_KEY:
    raise RuntimeError(
        "Faltan SUPABASE_URL o SUPABASE_KEY en tu .env "
        "(Settings → API en el dashboard de Supabase)."
    )

# “engine” singleton
_client: Optional[Client] = None

def get_engine() -> Client:
    global _client
    if _client is None:
        _client = create_client(SUPABASE_URL, SUPABASE_KEY)  # cliente oficial
    return _client

# Mantén el mismo nombre para minimizar cambios río arriba
@contextmanager
def get_db():
    """
    Equivalente a tu SessionLocal() de SQLAlchemy, pero entrega el cliente de Supabase.
    Uso:
        with get_db() as db:
            db.table("employees").select("*").execute()
    """
    client = get_engine()
    try:
        yield client
    finally:
        # supabase-py es stateless HTTP; no hay .close() necesario
        pass

# Útil para tests locales — en Supabase no aplica crear tablas desde código
def create_all_for_tests():
    """
    No-op: en Supabase las tablas se crean vía SQL o el dashboard.
    Déjalo para compatibilidad, o lanza NotImplementedError si prefieres.
    """
    return None

# (Opcional) pequeño "ping" para healthcheck
def ping() -> str:
    db = get_engine()
    res = db.table("employees").select("id", count="exact").limit(1).execute()
    return f"Ping OK — empleados totales (si RLS permite): {res.count}"

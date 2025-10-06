from __future__ import annotations
from datetime import date
from typing import Iterable

def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

# =========
# 09:00 - Seguimiento diario
# =========

def body_daily_text(d: date, employee_name: str) -> str:
    return f"""Hola {employee_name},

Por favor responde con este bloque (puedes editarlo). Si lo prefieres, responde en texto libre;
nuestro sistema interpretará el contenido automáticamente:

empleado: {employee_name}
fecha: {_fmt(d)}
tareas:
  - title: <tarea>
    status: pendiente|en_progreso|completado
    progress: 0
    next_steps: <pasos>
    blocker: ninguno

¡Gracias!
"""

# =========
# 11:00 - Recordatorio (mismo hilo)
# =========

def body_reminder_text(employee_name: str) -> str:
    return f"""Hola {employee_name},

Recordatorio amable: aún no recibimos tu actualización de hoy.
¿Nos ayudas respondiendo a este hilo? ¡Gracias!
"""

# =========
# Render helpers
# =========

def render_daily(name: str, d: date) -> str:
    return body_daily_text(d, name)

def render_reminder(name: str, d: date) -> str:
    return body_reminder_text(name)
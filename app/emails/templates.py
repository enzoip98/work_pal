# app/emails/templates.py
from __future__ import annotations
from datetime import date
from typing import Iterable

# =========
# Helpers
# =========

def _fmt(d: date) -> str:
    return d.strftime("%Y-%m-%d")

# =========
# 09:00 - Seguimiento diario
# =========

def subject_daily(d: date, employee_name: str) -> str:
    return f"[Seguimiento diario] {_fmt(d)} — {employee_name}"

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

def body_daily_html(d: date, employee_name: str) -> str:
    # Si vas a enviar HTML, recuerda enviar como multipart en tu gmail_client.
    return f"""\
<html>
  <body style="font-family: Arial, sans-serif; line-height:1.45;">
    <p>Hola <strong>{employee_name}</strong>,</p>
    <p>Por favor responde con este bloque (puedes editarlo). Si lo prefieres, responde en texto libre;
    nuestro sistema interpretará el contenido automáticamente:</p>
    <pre style="background:#f6f8fa; padding:12px; border-radius:6px; overflow:auto;">
empleado: {employee_name}
fecha: {_fmt(d)}
tareas:
  - title: &lt;tarea&gt;
    status: pendiente|en_progreso|completado
    progress: 0
    next_steps: &lt;pasos&gt;
    blocker: ninguno
    </pre>
    <p>¡Gracias!</p>
  </body>
</html>
"""

# =========
# 11:00 - Recordatorio (mismo hilo)
# =========

def subject_reminder(d: date, employee_name: str) -> str:
    # El "Re:" ayuda a mantener el asunto coherente si algún cliente no lo agrega solo.
    return f"Re: [Seguimiento diario] {_fmt(d)} — {employee_name}"

def body_reminder_text(employee_name: str) -> str:
    return f"""Hola {employee_name},

Recordatorio amable: aún no recibimos tu actualización de hoy.
¿Nos ayudas respondiendo a este hilo? ¡Gracias!
"""

def body_reminder_html(employee_name: str) -> str:
    return f"""\
<html>
  <body style="font-family: Arial, sans-serif; line-height:1.45;">
    <p>Hola <strong>{employee_name}</strong>,</p>
    <p>Recordatorio amable: aún no recibimos tu actualización de hoy.
    ¿Nos ayudas respondiendo a este hilo con el bloque YAML o en texto libre?</p>
    <p>¡Gracias!</p>
  </body>
</html>
"""

def subject_digest(d: date) -> str:
    return f"[Resumen diario] {_fmt(d)}"

def body_digest_text(d: date, totals: dict, per_employee: Iterable[dict]) -> str:
    lines = [
        f"Fecha: {_fmt(d)}",
        f"Equipo total (check-ins): {totals.get('total_checkins', 0)}",
        f"Respondieron: {totals.get('responded', 0)}",
        f"Pendientes: {totals.get('pending', 0)}",
        f"Tareas con bloqueo: {totals.get('blockers', 0)}",
        "",
        "Detalle por persona:",
    ]
    for p in per_employee:
        name = p.get("name") or "—"
        counts = p.get("counts") or {}
        blockers = p.get("blockers") or []
        c = counts.get("completado", 0)
        e = counts.get("en_progreso", 0)
        pe = counts.get("pendiente", 0)
        lines.append(f"- {name}: {c} completadas, {e} en progreso, {pe} pendientes")
        if blockers:
            for b in blockers:
                lines.append(f"    • Bloqueo: {b}")
    return "\n".join(lines) + "\n"

def body_digest_html(d: date, totals: dict, per_employee: Iterable[dict]) -> str:
    head = f"""
    <p><strong>Fecha:</strong> {_fmt(d)}</p>
    <ul>
      <li><strong>Equipo total (check-ins):</strong> {totals.get('total_checkins', 0)}</li>
      <li><strong>Respondieron:</strong> {totals.get('responded', 0)}</li>
      <li><strong>Pendientes:</strong> {totals.get('pending', 0)}</li>
      <li><strong>Tareas con bloqueo:</strong> {totals.get('blockers', 0)}</li>
    </ul>
    <h3>Detalle por persona</h3>
    """
    rows = []
    for p in per_employee:
        name = p.get("name") or "—"
        counts = p.get("counts") or {}
        blockers = p.get("blockers") or []
        c = counts.get("completado", 0)
        e = counts.get("en_progreso", 0)
        pe = counts.get("pendiente", 0)
        blks = ""
        if blockers:
            blks = "<ul>" + "".join(f"<li>{b}</li>" for b in blockers) + "</ul>"
        rows.append(f"""
        <tr>
          <td style="padding:6px 8px; border:1px solid #ddd;">{name}</td>
          <td style="padding:6px 8px; border:1px solid #ddd; text-align:center;">{c}</td>
          <td style="padding:6px 8px; border:1px solid #ddd; text-align:center;">{e}</td>
          <td style="padding:6px 8px; border:1px solid #ddd; text-align:center;">{pe}</td>
          <td style="padding:6px 8px; border:1px solid #ddd;">{blks or '—'}</td>
        </tr>
        """)

    table = f"""
    <table cellpadding="0" cellspacing="0" style="border-collapse:collapse; width:100%; font-family:Arial, sans-serif;">
      <thead>
        <tr>
          <th style="padding:6px 8px; border:1px solid #ddd; background:#f6f8fa; text-align:left;">Persona</th>
          <th style="padding:6px 8px; border:1px solid #ddd; background:#f6f8fa;">Completadas</th>
          <th style="padding:6px 8px; border:1px solid #ddd; background:#f6f8fa;">En progreso</th>
          <th style="padding:6px 8px; border:1px solid #ddd; background:#f6f8fa;">Pendientes</th>
          <th style="padding:6px 8px; border:1px solid #ddd; background:#f6f8fa; text-align:left;">Bloqueos</th>
        </tr>
      </thead>
      <tbody>
        {''.join(rows)}
      </tbody>
    </table>
    """

    return f"""\
<html>
  <body style="font-family: Arial, sans-serif; line-height:1.45;">
    <h2 style="margin:0 0 8px 0;">Resumen diario</h2>
    {head}
    {table}
  </body>
</html>
"""

# =========
# Render helpers
# =========

def render_daily(name: str, d: date, html: bool = False) -> str:
    return body_daily_html(d, name) if html else body_daily_text(d, name)

def render_reminder(name: str, d: date, html: bool = False) -> str:
    return body_reminder_html(name) if html else body_reminder_text(name)

def render_digest(d: date, totals: dict, per_employee: Iterable[dict], html: bool = False) -> str:
    return body_digest_html(d, totals, per_employee) if html else body_digest_text(d, totals, per_employee)

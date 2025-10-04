# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import Iterable, Optional, List, Dict, Any, Tuple
from datetime import date, datetime, timezone

# NOTA: aquí ya NO usamos SQLAlchemy
# Usamos el cliente de Supabase (PostgREST)
# from supabase import Client

# Si quieres tipos ligeros de retorno (opcionales)
Employee = Dict[str, Any]
Checkin = Dict[str, Any]
Task = Dict[str, Any]

# --------------------------
# Helpers generales
# --------------------------
def _norm_email(email: str) -> str:
    return (email or "").lower().strip()

def _strip_or_none(s: Optional[str]) -> Optional[str]:
    if s is None:
        return None
    s2 = s.strip()
    return s2 if s2 else ""

# --------------------------
# Employees
# --------------------------
def create_employee(client, *, email: str, name: str, active: bool = True) -> Employee:
    """
    INSERT en employees. Devuelve la fila insertada.
    """
    payload = {
        "email": _norm_email(email),
        "name": (name or "").strip(),
        "active": active,
    }
    res = client.table("employees").insert(payload, returning="representation").execute()
    return (res.data or [None])[0]

def get_employees(client, active_only: bool = True) -> List[Employee]:
    q = client.table("employees").select("*")
    if active_only:
        q = q.eq("active", True)  # filtro por igualdad
    res = q.order("id", desc=False).execute()
    return res.data or []

def get_employee_by_email(client, email: str) -> Optional[Employee]:
    res = (
        client.table("employees")
        .select("*")
        .eq("email", _norm_email(email))
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None

# --------------------------
# Checkins
# --------------------------
def upsert_checkin(
    client,
    *,
    the_date: date,
    employee: Employee,
    thread_id: Optional[str],
    first_message_id: Optional[str],
) -> Checkin:
    """
    Idempotente por (date, employee_id). Si quieres que el PK id del check-in
    esté ligado al hilo de Gmail, usamos thread_id como id.
    """
    # Validación: necesitamos al menos uno
    if not (thread_id or first_message_id):
        raise ValueError("Se requiere thread_id (o first_message_id) para generar el id del check-in.")

    # 👇 clave: setear id ligado al hilo
    checkin_id = thread_id or first_message_id  # preferimos thread_id

    payload = {
        "id": checkin_id,                 # <<<<<<<<<<<<<<<< importa esto
        "date": str(the_date),
        "employee_id": employee["id"],
        "thread_id": thread_id,
        "first_message_id": first_message_id,
    }

    res = (
        client.table("checkins")
        .upsert(payload, on_conflict="date,employee_id", returning="representation")
        .execute()
    )
    chk = (res.data or [None])[0]

    if chk:
        # Completar campos si venían nulos
        patch = {}
        if thread_id and not chk.get("thread_id"):
            patch["thread_id"] = thread_id
        if first_message_id and not chk.get("first_message_id"):
            patch["first_message_id"] = first_message_id
        if patch:
            res2 = (
                client.table("checkins")
                .update(patch)
                .eq("date", str(the_date))
                .eq("employee_id", employee["id"])
                .execute()
            )
            if res2.data:
                return res2.data[0]
            # fallback: leerlo después del update (por RLS/Prefer headers)
            res3 = (
                client.table("checkins")
                .select("*")
                .eq("date", str(the_date))
                .eq("employee_id", employee["id"])
                .limit(1)
                .execute()
            )
            return (res3.data or [chk])[0]
        return chk

    # Si por alguna razón no devolvió representación, re-lee
    res3 = (
        client.table("checkins")
        .select("*")
        .eq("date", str(the_date))
        .eq("employee_id", employee["id"])
        .limit(1)
        .execute()
    )
    rows = res3.data or []
    return rows[0] if rows else None

def get_today_checkins_by_thread(client, thread_id: str) -> Optional[Checkin]:
    today = date.today()
    res = (
        client.table("checkins")
        .select("*")
        .eq("date", str(today))
        .eq("thread_id", thread_id)
        .limit(1)
        .execute()
    )
    rows = res.data or []
    return rows[0] if rows else None

def mark_replied(client, checkin_id: str, ts: Optional[datetime] = None) -> None:
    when = (ts or datetime.now(timezone.utc)).isoformat()
    _ = (
        client.table("checkins")
        .update({"reply_received_at": when})
        .eq("id", checkin_id)
        .execute()
    )

def get_pending_checkins(client, *, the_date: date) -> List[Checkin]:
    """
    Check-ins del día sin respuesta para empleados activos.
    En dos pasos para evitar JOINs complejos en el cliente:
      1) ids de empleados activos
      2) checkins del día con reply_received_at IS NULL y employee_id en esos ids
    """
    # 1) empleados activos
    emp_res = client.table("employees").select("id").eq("active", True).execute()
    emp_ids = [r["id"] for r in (emp_res.data or [])]
    if not emp_ids:
        return []

    # 2) checkins filtrados (IS NULL y fecha)
    res = (
        client.table("checkins")
        .select("*")
        .eq("date", str(the_date))
        .is_("reply_received_at", "null")  # IS NULL
        .in_("employee_id", emp_ids)
        .order("id", desc=False)
        .execute()
    )
    return res.data or []

# --------------------------
# Tasks
# --------------------------
def replace_tasks(client, *, checkin_id: str, tasks: Iterable[dict]) -> List[Task]:
    """
    Borra todas las tareas del checkin y vuelve a insertarlas (idempotente a nivel de checkin).
    Normaliza 'status' y 'progress'.
    """
    # Borrado por checkin_id
    _ = client.table("tasks").delete().eq("checkin_id", checkin_id).execute()

    created: List[Task] = []
    batch: List[Dict[str, Any]] = []

    for t in tasks:
        title = (t.get("title") or "").strip()
        if not title:
            continue

        status = (t.get("status") or "en_progreso").strip().lower()
        if status not in {"pendiente", "en_progreso", "completado"}:
            status = "en_progreso"

        progress = t.get("progress")
        if isinstance(progress, int):
            progress = max(0, min(100, progress))
        else:
            progress = None

        batch.append(
            {   
                "checkin_id": checkin_id,
                "title": title,
                "status": status,
                "progress": progress,
                "next_steps": t.get("next_steps"),
                "blocker": t.get("blocker"),
            }
        )

    if batch:
        print("batch being inserted")
        res = client.table("tasks").insert(batch, returning="representation").execute()
        created = res.data or []

    return created

# --------------------------
# Digest / Resumen
# --------------------------
def _count_checkins(client, where: List[Tuple[str, str, Any]]) -> int:
    q = client.table("checkins").select("id", count="exact")  # usa header Prefer: count=exact
    for col, op, val in where:
        if op == "eq":
            q = q.eq(col, val)
        elif op == "is_null":
            q = q.is_(col, "null")
        elif op == "not_null":
            q = q.not_.is_(col, "null")
        else:
            raise ValueError(f"Operador no soportado: {op}")
    res = q.execute()
    return int(res.count or 0)

def build_summary_text(client, *, the_date: date) -> str:
    total = _count_checkins(client, [("date", "eq", str(the_date))])
    responded = _count_checkins(
        client,
        [("date", "eq", str(the_date)), ("reply_received_at", "not_null", None)],
    )
    pending = total - responded

    # Blockers: tareas cuyo checkin es del día y blocker no es NULL ni vacío
    # 1) ids de checkins del día
    chks = (
        client.table("checkins")
        .select("id")
        .eq("date", str(the_date))
        .execute()
        .data
        or []
    )
    chk_ids = [c["id"] for c in chks]
    blockers = 0
    if chk_ids:
        res_tasks = (
            client.table("tasks")
            .select("id,blocker")
            .in_("checkin_id", chk_ids)
            .not_.is_("blocker", "null")  # NOT IS NULL
            .neq("blocker", "")           # y no vacío
            .execute()
        )
        blockers = len(res_tasks.data or [])

    return (
        f"Fecha: {the_date}\n"
        f"Total check-ins: {total}\n"
        f"Respondieron: {responded}\n"
        f"Pendientes: {pending}\n"
        f"Tareas con bloqueo: {blockers}\n"
    )

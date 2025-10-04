from dotenv import load_dotenv
from app.db.base import get_db
from app.services.gmail_client import send_email

load_dotenv()  # APP_TZ, OPENAI_API_KEY, etc.

def _fetch_snapshot(db, the_date: date) -> List[Dict[str, Any]]:
    """
    Devuelve una lista de tasks enriquecidas con datos de empleado.
    """
    # Check-ins del día
    chks = (
        db.table("checkins")
        .select("id, employee_id, thread_id, first_message_id")
        .eq("date", str(the_date))
        .execute()
        .data
        or []
    )
    if not chks:
        return []

    checkin_ids = [c["id"] for c in chks]
    employee_ids = list({c["employee_id"] for c in chks})

    # Empleados
    emps = (
        db.table("employees")
        .select("id, name, email")
        .in_("id", employee_ids)
        .execute()
        .data
        or []
    )
    employees_by_id: Dict[str, Dict[str, Any]] = {e["id"]: e for e in emps}

    # Tasks
    tasks = (
        db.table("tasks")
        .select("id, checkin_id, title, status, progress, next_steps, blocker, task_order")
        .in_("checkin_id", checkin_ids)
        .order("checkin_id")
        .order("task_order", desc=False)
        .execute()
        .data
        or []
    )

    emp_by_checkin = {c["id"]: c["employee_id"] for c in chks}
    enriched: List[Dict[str, Any]] = []
    for t in tasks:
        eid = emp_by_checkin.get(t["checkin_id"])
        emp = employees_by_id.get(eid, {})
        enriched.append({
            **t,
            "employee_id": eid,
            "employee_name": (emp.get("name") or emp.get("email") or "").strip(),
            "employee_email": emp.get("email"),
        })
    return enriched
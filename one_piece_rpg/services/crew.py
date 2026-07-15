"""Ship crew management."""

from one_piece_rpg.data import SHIPS
from one_piece_rpg.database import _now, get_db


def get_crew_cap(ship_id: str) -> int:
    return SHIPS.get(ship_id, {}).get("crew_cap", 0)


def get_crew(captain_id: int) -> list[dict]:
    with get_db() as conn:
        rows = conn.execute(
            """SELECT sc.member_id, sc.title, sc.joined_at, p.username as name
               FROM ship_crew sc
               LEFT JOIN players p ON p.user_id = sc.member_id
               WHERE sc.captain_id = ?""",
            (captain_id,)
        ).fetchall()
    return [dict(r) for r in rows]


def invite_to_crew(captain_id: int, member_id: int) -> dict:
    if captain_id == member_id:
        return {"ok": False, "msg": "نمیشه خودت رو دعوت کنی!"}

    with get_db() as conn:
        captain = conn.execute("SELECT ship_id FROM players WHERE user_id=?", (captain_id,)).fetchone()
        if not captain or not captain["ship_id"]:
            return {"ok": False, "msg": "اول باید کشتی داشته باشی!"}

        cap = get_crew_cap(captain["ship_id"])
        current = conn.execute("SELECT COUNT(*) as c FROM ship_crew WHERE captain_id=?", (captain_id,)).fetchone()["c"]
        if current >= cap:
            ship_name = SHIPS[captain["ship_id"]]["name"]
            return {"ok": False, "msg": f"کشتی {ship_name} پر شده! ({current}/{cap})"}

        # چک که member تو crew دیگه‌ای نباشه
        already = conn.execute("SELECT captain_id FROM ship_crew WHERE member_id=?", (member_id,)).fetchone()
        if already:
            return {"ok": False, "msg": "این بازیکن تو کشتی دیگه‌ایه!"}

        try:
            conn.execute(
                "INSERT INTO ship_crew (captain_id, member_id, joined_at) VALUES (?,?,?)",
                (captain_id, member_id, _now())
            )
        except Exception:
            return {"ok": False, "msg": "این بازیکن قبلاً تو خدمته!"}

    return {"ok": True, "cap": cap, "current": current + 1}


def set_title(captain_id: int, member_id: int, title: str) -> dict:
    if len(title) > 20:
        return {"ok": False, "msg": "لقب حداکثر ۲۰ کاراکتر باشه"}
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM ship_crew WHERE captain_id=? AND member_id=?",
            (captain_id, member_id)
        ).fetchone()
        if not row:
            return {"ok": False, "msg": "این بازیکن تو خدمه تو نیست!"}
        conn.execute("UPDATE ship_crew SET title=? WHERE captain_id=? AND member_id=?",
                     (title, captain_id, member_id))
    return {"ok": True}


def kick_from_crew(captain_id: int, member_id: int) -> dict:
    with get_db() as conn:
        conn.execute("DELETE FROM ship_crew WHERE captain_id=? AND member_id=?",
                     (captain_id, member_id))
    return {"ok": True}


def leave_crew(member_id: int) -> dict:
    with get_db() as conn:
        conn.execute("DELETE FROM ship_crew WHERE member_id=?", (member_id,))
    return {"ok": True}


def get_captain(member_id: int) -> dict | None:
    with get_db() as conn:
        row = conn.execute(
            """SELECT sc.captain_id, p.username as name, p.ship_id
               FROM ship_crew sc
               LEFT JOIN players p ON p.user_id = sc.captain_id
               WHERE sc.member_id = ?""",
            (member_id,)
        ).fetchone()
    return dict(row) if row else None

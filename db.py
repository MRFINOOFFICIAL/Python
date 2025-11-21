# db.py
import aiosqlite
from datetime import datetime
from typing import Optional

DB = "economy.db"

# ---------- Inicialización ----------
async def init_db():
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id TEXT PRIMARY KEY,
            dinero INTEGER DEFAULT 0,
            experiencia INTEGER DEFAULT 0,
            rango TEXT DEFAULT 'Novato',
            trabajo TEXT DEFAULT 'Desempleado'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            item TEXT,
            rareza TEXT,
            usos INTEGER DEFAULT 1,
            durabilidad INTEGER DEFAULT 100,
            categoria TEXT DEFAULT 'desconocido',
            poder INTEGER DEFAULT 0
        )
        """)
        # intentar agregar columnas si la tabla es antigua (safe)
        try:
            await db.execute("ALTER TABLE inventory ADD COLUMN categoria TEXT DEFAULT 'desconocido'")
        except aiosqlite.OperationalError:
            pass
        try:
            await db.execute("ALTER TABLE inventory ADD COLUMN poder INTEGER DEFAULT 0")
        except aiosqlite.OperationalError:
            pass

        await db.execute("""
        CREATE TABLE IF NOT EXISTS shop (
            name TEXT PRIMARY KEY,
            price INTEGER,
            type TEXT,
            effect TEXT,
            rarity TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS work_cooldowns (
            user_id TEXT,
            job_name TEXT,
            last_work TIMESTAMP,
            PRIMARY KEY(user_id, job_name)
        )
        """)
        # tabla para buffs activos (consumibles que el usuario activa con !use)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS active_buffs (
            user_id TEXT,
            buff TEXT,
            uses INTEGER DEFAULT 1,
            expires_at TIMESTAMP,
            PRIMARY KEY(user_id, buff)
        )
        """)
        await db.commit()

# ---------- Users ----------
async def ensure_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT user_id FROM users WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if not row:
            await db.execute(
                "INSERT INTO users(user_id, dinero, experiencia, rango, trabajo) VALUES (?,0,0,'Novato','Desempleado')",
                (str(user_id),)
            )
            await db.commit()

async def get_user(user_id):
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT user_id, dinero, experiencia, rango, trabajo FROM users WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        return {"id": row[0], "dinero": row[1], "experiencia": row[2], "rango": row[3], "trabajo": row[4]}

async def add_money(user_id, amount):
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET dinero = dinero + ? WHERE user_id = ?", (int(amount), str(user_id)))
        await db.commit()

async def set_money(user_id, amount):
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET dinero = ? WHERE user_id = ?", (int(amount), str(user_id)))
        await db.commit()

async def update_rank(user_id):
    user = await get_user(user_id)
    dinero = user["dinero"]
    if dinero >= 100000:
        rango = "Enfermo Supremo"
    elif dinero >= 50000:
        rango = "Enfermo Avanzado"
    elif dinero >= 10000:
        rango = "Enfermo Básico"
    else:
        rango = "Novato"
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET rango = ? WHERE user_id = ?", (rango, str(user_id)))
        await db.commit()

async def set_job(user_id, job_name):
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE users SET trabajo = ? WHERE user_id = ?", (job_name, str(user_id)))
        await db.commit()

# ---------- Inventory ----------
async def add_item_to_user(user_id, item, rareza="comun", usos=1, durabilidad=100, categoria="desconocido", poder=0):
    """Agrega item; acepta categoria y poder (para robos)."""
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO inventory(user_id, item, rareza, usos, durabilidad, categoria, poder) VALUES (?,?,?,?,?,?,?)",
            (str(user_id), item, rareza, usos, durabilidad, categoria, poder)
        )
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id, item, rareza, usos, durabilidad, categoria, poder FROM inventory WHERE user_id = ?", (str(user_id),))
        rows = await cur.fetchall()
        return [
            {"id": r[0], "item": r[1], "rareza": r[2], "usos": r[3], "durabilidad": r[4], "categoria": r[5] or "desconocido", "poder": r[6] or 0}
            for r in rows
        ]

async def get_item_by_id(item_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id, user_id, item, rareza, usos, durabilidad, categoria, poder FROM inventory WHERE id = ?", (item_id,))
        r = await cur.fetchone()
        if not r:
            return None
        return {"id": r[0], "user_id": r[1], "item": r[2], "rareza": r[3], "usos": r[4], "durabilidad": r[5], "categoria": r[6], "poder": r[7]}

async def remove_item(user_id, item_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM inventory WHERE id = ? AND user_id = ?", (item_id, str(user_id)))
        await db.commit()

async def consume_item(item_id, amount=1):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT usos FROM inventory WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        if not row:
            return False
        usos = row[0] - amount
        if usos <= 0:
            await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        else:
            await db.execute("UPDATE inventory SET usos = ? WHERE id = ?", (usos, item_id))
        await db.commit()
        return True

async def damage_item(item_id, dmg):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT durabilidad FROM inventory WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        if not row:
            return False
        new = row[0] - dmg
        if new <= 0:
            await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        else:
            await db.execute("UPDATE inventory SET durabilidad = ? WHERE id = ?", (new, item_id))
        await db.commit()
        return True

async def repair_item(item_id, amount, requester_id):
    """
    Repara un item: solo si requester_id es dueño del item.
    Devuelve la nueva durabilidad o None si no existe/permiso.
    """
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT user_id, durabilidad FROM inventory WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        if not row:
            return None
        owner, cur_dur = row[0], row[1]
        if str(owner) != str(requester_id):
            return None
        new = min(100, (cur_dur or 0) + int(amount))
        await db.execute("UPDATE inventory SET durabilidad = ? WHERE id = ?", (new, item_id))
        await db.commit()
        return new

# ---------- Shop ----------
async def add_shop_item(name, price, type_, effect="", rarity="comun"):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO shop(name, price, type, effect, rarity) VALUES (?,?,?,?,?)",
                         (name, price, type_, effect, rarity))
        await db.commit()

async def get_shop():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop")
        rows = await cur.fetchall()
        return [{"name": r[0], "price": r[1], "type": r[2], "effect": r[3], "rarity": r[4]} for r in rows]

async def get_shop_item(name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop WHERE name = ?", (name,))
        r = await cur.fetchone()
        if not r:
            return None
        return {"name": r[0], "price": r[1], "type": r[2], "effect": r[3], "rarity": r[4]}

# ---------- Buffs (active_buffs) ----------
async def add_buff(user_id, buff_name, uses: int = 1, expires_at: Optional[datetime] = None):
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT INTO active_buffs(user_id, buff, uses, expires_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(user_id, buff) DO UPDATE SET uses = active_buffs.uses + excluded.uses, expires_at = excluded.expires_at
        """, (str(user_id), buff_name, int(uses), expires_at.isoformat() if expires_at else None))
        await db.commit()

async def get_buffs(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT buff, uses, expires_at FROM active_buffs WHERE user_id = ?", (str(user_id),))
        rows = await cur.fetchall()
        return [{"buff": r[0], "uses": r[1], "expires_at": r[2]} for r in rows]

async def consume_buff(user_id, buff_name):
    """
    Decrementa 1 uso del buff y lo elimina si llega a 0.
    Devuelve True si un buff fue consumido, False si no existía.
    """
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT uses FROM active_buffs WHERE user_id = ? AND buff = ?", (str(user_id), buff_name))
        row = await cur.fetchone()
        if not row:
            return False
        uses = row[0] - 1
        if uses <= 0:
            await db.execute("DELETE FROM active_buffs WHERE user_id = ? AND buff = ?", (str(user_id), buff_name))
        else:
            await db.execute("UPDATE active_buffs SET uses = ? WHERE user_id = ? AND buff = ?", (uses, str(user_id), buff_name))
        await db.commit()
        return True

# ---------- Work Cooldowns ----------
async def get_work_cooldown(user_id, job_name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_work FROM work_cooldowns WHERE user_id = ? AND job_name = ?",
                               (str(user_id), job_name))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

async def set_work_cooldown(user_id, job_name, timestamp: datetime):
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT INTO work_cooldowns(user_id, job_name, last_work)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, job_name) DO UPDATE SET last_work=excluded.last_work
        """, (str(user_id), job_name, timestamp.isoformat()))
        await db.commit()



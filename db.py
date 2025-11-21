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
        await db.execute("""
        CREATE TABLE IF NOT EXISTS bot_settings (
            guild_id TEXT PRIMARY KEY,
            allowed_channel_id TEXT
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

async def remove_item_from_inventory(item_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        await db.commit()

async def get_inventory(user_id):
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id, user_id, item, rareza, usos, durabilidad, categoria, poder FROM inventory WHERE user_id = ?",
            (str(user_id),)
        )
        rows = await cur.fetchall()
        return [
            {
                "id": row[0],
                "user_id": row[1],
                "item": row[2],
                "rareza": row[3],
                "usos": row[4],
                "durabilidad": row[5],
                "categoria": row[6],
                "poder": row[7]
            }
            for row in rows
        ]

async def get_item_by_id(item_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id, user_id, item, rareza, usos, durabilidad, categoria, poder FROM inventory WHERE id = ?",
            (item_id,)
        )
        row = await cur.fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "user_id": row[1],
            "item": row[2],
            "rareza": row[3],
            "usos": row[4],
            "durabilidad": row[5],
            "categoria": row[6],
            "poder": row[7]
        }

async def has_item(user_id, item_name: str) -> bool:
    """Verifica si el usuario tiene al menos 1 del item."""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM inventory WHERE user_id = ? AND item = ?",
            (str(user_id), item_name)
        )
        row = await cur.fetchone()
        return row[0] > 0 if row else False

async def count_items(user_id, item_name: str) -> int:
    """Cuenta cuántos del item tiene el usuario."""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT COUNT(*) FROM inventory WHERE user_id = ? AND item = ?",
            (str(user_id), item_name)
        )
        row = await cur.fetchone()
        return row[0] if row else 0

async def update_item_durability(item_id, new_durability: int):
    """Actualiza la durabilidad de un item específico."""
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE inventory SET durabilidad = ? WHERE id = ?", (new_durability, item_id))
        await db.commit()

# ---------- Shop ----------
async def get_shop_item(name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop WHERE name = ?", (name,))
        row = await cur.fetchone()
        if not row:
            return None
        return {"name": row[0], "price": row[1], "type": row[2], "effect": row[3], "rarity": row[4]}

async def get_shop():
    """Get all shop items (alias for compatibility)"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop")
        rows = await cur.fetchall()
        return [{"name": row[0], "price": row[1], "type": row[2], "effect": row[3], "rarity": row[4]} for row in rows]

async def get_all_shop_items():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop")
        rows = await cur.fetchall()
        return [{"name": row[0], "price": row[1], "type": row[2], "effect": row[3], "rarity": row[4]} for row in rows]

async def add_shop_item(name, price, type_item, effect, rarity):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO shop(name, price, type, effect, rarity) VALUES (?,?,?,?,?)",
            (name, price, type_item, effect, rarity)
        )
        await db.commit()

# ---------- Active Buffs ----------
async def add_active_buff(user_id, buff_name, uses=1, duration_seconds=3600):
    """Agrega un buff activo al usuario por X segundos."""
    await ensure_user(user_id)
    expires_at = (datetime.now() + __import__('datetime').timedelta(seconds=duration_seconds)).isoformat()
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO active_buffs(user_id, buff, uses, expires_at) VALUES (?,?,?,?)",
            (str(user_id), buff_name, uses, expires_at)
        )
        await db.commit()

async def get_active_buffs(user_id):
    """Obtiene todos los buffs activos del usuario (eliminando expirados)."""
    await ensure_user(user_id)
    async with aiosqlite.connect(DB) as db:
        # Eliminar expirados
        await db.execute(
            "DELETE FROM active_buffs WHERE user_id = ? AND expires_at < ?",
            (str(user_id), datetime.now().isoformat())
        )
        await db.commit()
        
        # Obtener los vigentes
        cur = await db.execute(
            "SELECT buff, uses, expires_at FROM active_buffs WHERE user_id = ?",
            (str(user_id),)
        )
        rows = await cur.fetchall()
        return [{"buff": row[0], "uses": row[1], "expires_at": row[2]} for row in rows]

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

# ---------- Bot Settings ----------
async def set_allowed_channel(guild_id, channel_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("""
        INSERT INTO bot_settings(guild_id, allowed_channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET allowed_channel_id=excluded.allowed_channel_id
        """, (str(guild_id), str(channel_id) if channel_id else None))
        await db.commit()

async def get_allowed_channel(guild_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT allowed_channel_id FROM bot_settings WHERE guild_id = ?", (str(guild_id),))
        row = await cur.fetchone()
        return int(row[0]) if row and row[0] else None

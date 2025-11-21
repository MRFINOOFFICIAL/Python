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
            trabajo TEXT DEFAULT 'Desempleado',
            vidas INTEGER DEFAULT 1
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
        try:
            await db.execute("ALTER TABLE users ADD COLUMN vidas INTEGER DEFAULT 1")
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
            expira_en TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS boss_tables (
            guild_id TEXT,
            boss_name TEXT,
            current_hp INTEGER,
            max_hp INTEGER,
            active BOOLEAN DEFAULT 1,
            PRIMARY KEY (guild_id, boss_name)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            user_id TEXT PRIMARY KEY,
            item_id INTEGER,
            item_name TEXT
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS boss_cooldowns (
            user_id TEXT,
            guild_id TEXT,
            last_fight TIMESTAMP,
            PRIMARY KEY (user_id, guild_id)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS event_channels (
            guild_id TEXT,
            channel_id TEXT,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)
        await db.commit()

# ---------- USUARIOS ----------

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            return {"user_id": row[0], "dinero": row[1], "experiencia": row[2], "rango": row[3], "trabajo": row[4], "vidas": row[5] if len(row) > 5 else 1}
        return None

async def add_money(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET dinero = dinero + ? WHERE user_id = ?", (amount, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, dinero, vidas) VALUES (?, ?, ?)", (str(user_id), amount, 1))
        await db.commit()

async def get_money(user_id):
    user = await get_user(user_id)
    return user["dinero"] if user else 0

async def add_experiencia(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET experiencia = experiencia + ? WHERE user_id = ?", (amount, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, experiencia) VALUES (?, ?)", (str(user_id), amount))
        await db.commit()

async def get_experiencia(user_id):
    user = await get_user(user_id)
    return user["experiencia"] if user else 0

async def set_job(user_id, job):
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET trabajo = ? WHERE user_id = ?", (job, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, trabajo) VALUES (?, ?)", (str(user_id), job))
        await db.commit()

async def update_rank(user_id, new_rank):
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET rango = ? WHERE user_id = ?", (new_rank, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, rango) VALUES (?, ?)", (str(user_id), new_rank))
        await db.commit()

async def add_lives(user_id, amount: int):
    """Agregar vidas al usuario"""
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET vidas = vidas + ? WHERE user_id = ?", (amount, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, vidas) VALUES (?, ?)", (str(user_id), max(1, amount)))
        await db.commit()

async def set_lives(user_id, lives: int):
    """Establecer vidas del usuario"""
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET vidas = ? WHERE user_id = ?", (lives, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, vidas) VALUES (?, ?)", (str(user_id), lives))
        await db.commit()

async def get_lives(user_id):
    """Obtener vidas del usuario"""
    user = await get_user(user_id)
    return user["vidas"] if user and "vidas" in user else 1

async def reset_user_progress(user_id):
    """Resetear el progreso de un usuario: dinero, experiencia, trabajo, inventario"""
    async with aiosqlite.connect(DB) as db:
        # Resetear dinero y experiencia
        await db.execute("UPDATE users SET dinero = 0, experiencia = 0, trabajo = 'Desempleado' WHERE user_id = ?", (str(user_id),))
        # Eliminar todo el inventario
        await db.execute("DELETE FROM inventory WHERE user_id = ?", (str(user_id),))
        # Resetear vidas a 1
        await db.execute("UPDATE users SET vidas = 1 WHERE user_id = ?", (str(user_id),))
        await db.commit()

# ---------- INVENTARIO ----------

async def add_item_to_user(user_id, item_name, rareza="comun", usos=1, durabilidad=100, categoria="desconocido", poder=0):
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO inventory(user_id, item, rareza, usos, durabilidad, categoria, poder) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (str(user_id), item_name, rareza, usos, durabilidad, categoria, poder)
        )
        await db.commit()

async def get_inventory(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT id, item, rareza, usos, durabilidad, categoria, poder FROM inventory WHERE user_id = ?", (str(user_id),))
        rows = await cur.fetchall()
        return [{"id": r[0], "item": r[1], "rareza": r[2], "usos": r[3], "durabilidad": r[4], "categoria": r[5], "poder": r[6]} for r in rows]

async def remove_item(item_id):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        await db.commit()

async def damage_item(item_id, damage: int):
    """Reducir durabilidad de un item"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE inventory SET durabilidad = MAX(0, durabilidad - ?) WHERE id = ?", (damage, item_id))
        await db.commit()

async def repair_item(item_id, amount: int = 100):
    """Restaurar durabilidad de un item"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE inventory SET durabilidad = MIN(100, durabilidad + ?) WHERE id = ?", (amount, item_id))
        await db.commit()

async def use_item_once(item_id):
    """Usa un item una vez (reduce usos)"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT usos FROM inventory WHERE id = ?", (item_id,))
        row = await cur.fetchone()
        if row and row[0] > 1:
            await db.execute("UPDATE inventory SET usos = usos - 1 WHERE id = ?", (item_id,))
        else:
            await db.execute("DELETE FROM inventory WHERE id = ?", (item_id,))
        await db.commit()

# ---------- TIENDA ----------

async def get_shop():
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop ORDER BY name")
        rows = await cur.fetchall()
        return [{"name": r[0], "price": r[1], "type": r[2], "effect": r[3], "rarity": r[4]} for r in rows]

async def add_shop_item(name, price, item_type, effect, rarity):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO shop(name, price, type, effect, rarity) VALUES (?, ?, ?, ?, ?)", 
                        (name, price, item_type, effect, rarity))
        await db.commit()

async def get_shop_item(name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT name, price, type, effect, rarity FROM shop WHERE name = ?", (name,))
        row = await cur.fetchone()
        if row:
            return {"name": row[0], "price": row[1], "type": row[2], "effect": row[3], "rarity": row[4]}
        return None

# ---------- COOLDOWNS ----------

async def set_work_cooldown(user_id, job_name):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO work_cooldowns(user_id, job_name, last_work) VALUES (?, ?, ?)", 
                        (str(user_id), job_name, datetime.now().isoformat()))
        await db.commit()

async def get_work_cooldown(user_id, job_name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_work FROM work_cooldowns WHERE user_id = ? AND job_name = ?", (str(user_id), job_name))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

async def has_work_cooldown(user_id, job_name, minutes=10):
    last_work = await get_work_cooldown(user_id, job_name)
    if not last_work:
        return False
    from datetime import timedelta
    return datetime.now() - last_work < timedelta(minutes=minutes)

async def get_remaining_work_cooldown(user_id, job_name, minutes=10):
    from datetime import timedelta
    last_work = await get_work_cooldown(user_id, job_name)
    if not last_work:
        return 0
    elapsed = datetime.now() - last_work
    remaining = timedelta(minutes=minutes) - elapsed
    return max(0, int(remaining.total_seconds()))

# ---------- BUFFS ACTIVOS ----------

async def add_active_buff(user_id, buff_name, minutes=60):
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        expira_en = (datetime.now() + timedelta(minutes=minutes)).isoformat()
        await db.execute("INSERT INTO active_buffs(user_id, buff, expira_en) VALUES (?, ?, ?)", 
                        (str(user_id), buff_name, expira_en))
        await db.commit()

async def get_active_buffs(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT buff, expira_en FROM active_buffs WHERE user_id = ?", (str(user_id),))
        rows = await cur.fetchall()
        result = {}
        for buff, expira_en in rows:
            exp_dt = datetime.fromisoformat(expira_en)
            if exp_dt > datetime.now():
                result[buff] = exp_dt
            else:
                await db.execute("DELETE FROM active_buffs WHERE user_id = ? AND buff = ?", (str(user_id), buff))
        await db.commit()
        return result

async def has_active_buff(user_id, buff_name):
    buffs = await get_active_buffs(user_id)
    return buff_name in buffs

async def clear_active_buff(user_id, buff_name):
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM active_buffs WHERE user_id = ? AND buff = ?", (str(user_id), buff_name))
        await db.commit()

# ---------- JEFE ACTUAL ----------

async def get_active_boss(guild_id, boss_name):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT boss_name, current_hp, max_hp, active FROM boss_tables WHERE guild_id = ? AND boss_name = ?", (str(guild_id), boss_name))
        row = await cur.fetchone()
        if row:
            return {"boss_name": row[0], "current_hp": row[1], "max_hp": row[2], "active": row[3]}
        return None

async def create_boss(guild_id, boss_name, max_hp):
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO boss_tables(guild_id, boss_name, current_hp, max_hp, active) VALUES (?, ?, ?, ?, ?)", 
                        (str(guild_id), boss_name, max_hp, max_hp, 1))
        await db.commit()

async def damage_boss(guild_id, boss_name, damage):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE boss_tables SET current_hp = MAX(0, current_hp - ?) WHERE guild_id = ? AND boss_name = ?", 
                        (damage, str(guild_id), boss_name))
        await db.commit()

async def deactivate_boss(guild_id, boss_name):
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE boss_tables SET active = 0 WHERE guild_id = ? AND boss_name = ?", 
                        (str(guild_id), boss_name))
        await db.commit()

async def get_all_active_bosses(guild_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT boss_name, current_hp, max_hp FROM boss_tables WHERE guild_id = ? AND active = 1", (str(guild_id),))
        rows = await cur.fetchall()
        return [{"boss_name": r[0], "current_hp": r[1], "max_hp": r[2]} for r in rows]

# ---------- EVENTOS POR GUILD ----------

async def set_event_channel(guild_id, channel_id):
    """Save an event channel for a guild"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR IGNORE INTO event_channels(guild_id, channel_id) VALUES (?, ?)", (str(guild_id), str(channel_id)))
        await db.commit()

async def remove_event_channel(guild_id, channel_id):
    """Remove an event channel from a guild"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM event_channels WHERE guild_id = ? AND channel_id = ?", (str(guild_id), str(channel_id)))
        await db.commit()

async def get_event_channels(guild_id):
    """Get all event channels for a guild"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT channel_id FROM event_channels WHERE guild_id = ?", (str(guild_id),))
        rows = await cur.fetchall()
        return [int(row[0]) for row in rows]

async def set_equipped_item(user_id, item_id, item_name):
    """Equip an item for a user"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO equipment(user_id, item_id, item_name) VALUES (?, ?, ?)", (str(user_id), item_id, item_name))
        await db.commit()

async def get_equipped_item(user_id):
    """Get the equipped item for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT item_id, item_name FROM equipment WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            return {"item_id": row[0], "item_name": row[1]}
        return None

async def set_fight_cooldown(user_id, guild_id):
    """Set fight cooldown for a user in a guild"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("INSERT OR REPLACE INTO boss_cooldowns(user_id, guild_id, last_fight) VALUES (?, ?, ?)", (str(user_id), str(guild_id), datetime.now().isoformat()))
        await db.commit()

async def get_fight_cooldown(user_id, guild_id):
    """Get the last fight time for a user in a guild"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_fight FROM boss_cooldowns WHERE user_id = ? AND guild_id = ?", (str(user_id), str(guild_id)))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

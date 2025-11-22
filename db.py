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
            vidas INTEGER DEFAULT 3
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
            await db.execute("ALTER TABLE users ADD COLUMN vidas INTEGER DEFAULT 3")
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
        CREATE TABLE IF NOT EXISTS boss_spawn_times (
            guild_id TEXT,
            boss_type TEXT,
            last_spawn TIMESTAMP,
            PRIMARY KEY (guild_id, boss_type)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS event_channels (
            guild_id TEXT,
            channel_id TEXT,
            PRIMARY KEY (guild_id, channel_id)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS daily_missions (
            user_id TEXT,
            fecha TEXT,
            tipo TEXT,
            objetivo INTEGER,
            progreso INTEGER DEFAULT 0,
            recompensa INTEGER,
            completado BOOLEAN DEFAULT 0,
            PRIMARY KEY (user_id, fecha)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            remitente TEXT,
            receptor TEXT,
            item_remitente INTEGER,
            item_receptor INTEGER,
            estado TEXT DEFAULT 'pendiente'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS market (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vendedor TEXT,
            item_id INTEGER,
            precio INTEGER,
            fecha_lista TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS mascotas (
            user_id TEXT PRIMARY KEY,
            nombre TEXT NOT NULL,
            xp INTEGER DEFAULT 0,
            rareza TEXT DEFAULT 'común',
            equipada BOOLEAN DEFAULT 1
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS pet_xp (
            user_id TEXT PRIMARY KEY,
            xp INTEGER DEFAULT 0
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS duels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            retador TEXT,
            oponente TEXT,
            cantidad INTEGER,
            estado TEXT DEFAULT 'pendiente'
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS upgrades (
            user_id TEXT,
            nombre TEXT,
            PRIMARY KEY (user_id, nombre)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS clubs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT UNIQUE NOT NULL,
            lider TEXT NOT NULL,
            dinero INTEGER DEFAULT 0,
            miembros_max INTEGER DEFAULT 10,
            fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS club_members (
            club_id INTEGER,
            user_id TEXT,
            rango TEXT DEFAULT 'miembro',
            fecha_union TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (club_id, user_id),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
        """)
        await db.execute("""
        CREATE TABLE IF NOT EXISTS club_upgrades (
            club_id INTEGER,
            upgrade TEXT,
            PRIMARY KEY (club_id, upgrade),
            FOREIGN KEY (club_id) REFERENCES clubs(id)
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS rob_cooldowns (
            user_id TEXT,
            target_id TEXT,
            last_rob TIMESTAMP,
            PRIMARY KEY (user_id, target_id)
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS explore_cooldowns (
            user_id TEXT PRIMARY KEY,
            last_explore TIMESTAMP
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS duel_cooldowns (
            user_id TEXT PRIMARY KEY,
            last_duel TIMESTAMP
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS mining_cooldowns (
            user_id TEXT PRIMARY KEY,
            last_mine TIMESTAMP
        )
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS fishing_cooldowns (
            user_id TEXT PRIMARY KEY,
            last_fish TIMESTAMP
        )
        """)

        await db.commit()

# ---------- USUARIOS ----------

async def get_user(user_id):
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT * FROM users WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            return {"user_id": row[0], "dinero": row[1], "experiencia": row[2], "rango": row[3], "trabajo": row[4], "vidas": row[5] if len(row) > 5 else 3}
        return None

async def add_money(user_id, amount):
    async with aiosqlite.connect(DB) as db:
        user = await get_user(user_id)
        if user:
            await db.execute("UPDATE users SET dinero = dinero + ? WHERE user_id = ?", (amount, str(user_id)))
        else:
            await db.execute("INSERT INTO users(user_id, dinero, vidas) VALUES (?, ?, ?)", (str(user_id), amount, 3))
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
            await db.execute("INSERT INTO users(user_id, vidas) VALUES (?, ?)", (str(user_id), max(3, amount)))
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
    return user["vidas"] if user and "vidas" in user else 3

async def reset_user_progress(user_id):
    """Resetear el progreso de un usuario: dinero, experiencia, trabajo, inventario"""
    async with aiosqlite.connect(DB) as db:
        # Resetear dinero y experiencia
        await db.execute("UPDATE users SET dinero = 0, experiencia = 0, trabajo = 'Desempleado' WHERE user_id = ?", (str(user_id),))
        # Eliminar todo el inventario
        await db.execute("DELETE FROM inventory WHERE user_id = ?", (str(user_id),))
        # Resetear vidas a 3
        await db.execute("UPDATE users SET vidas = 3 WHERE user_id = ?", (str(user_id),))
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
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(minutes=10)
        await db.execute("INSERT OR REPLACE INTO work_cooldowns(user_id, job_name, last_work) VALUES (?, ?, ?)", 
                        (str(user_id), job_name, cooldown_expiry.isoformat()))
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

# ---------- ROB COOLDOWN (5 minutes) ----------

async def set_rob_cooldown(user_id, target_id):
    """Set rob cooldown for a user (5 minutes)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(minutes=5)
        await db.execute(
            "INSERT OR REPLACE INTO rob_cooldowns(user_id, target_id, last_rob) VALUES (?, ?, ?)",
            (str(user_id), str(target_id), cooldown_expiry.isoformat())
        )
        await db.commit()

async def get_rob_cooldown(user_id):
    """Get the last rob time for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_rob FROM rob_cooldowns WHERE user_id = ? ORDER BY last_rob DESC LIMIT 1", (str(user_id),))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

# ---------- EXPLORE COOLDOWN (25 seconds) ----------

async def set_explore_cooldown(user_id):
    """Set explore cooldown for a user (25 seconds)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(seconds=25)
        await db.execute(
            "INSERT OR REPLACE INTO explore_cooldowns(user_id, last_explore) VALUES (?, ?)",
            (str(user_id), cooldown_expiry.isoformat())
        )
        await db.commit()

async def get_explore_cooldown(user_id):
    """Get the last explore time for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_explore FROM explore_cooldowns WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

# ---------- DUEL COOLDOWN (1 minute) ----------

async def set_duel_cooldown(user_id):
    """Set duel cooldown for a user (1 minute)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(minutes=1)
        await db.execute(
            "INSERT OR REPLACE INTO duel_cooldowns(user_id, last_duel) VALUES (?, ?)",
            (str(user_id), cooldown_expiry.isoformat())
        )
        await db.commit()

async def get_duel_cooldown(user_id):
    """Get the last duel time for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_duel FROM duel_cooldowns WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

# ---------- MINING COOLDOWN (30 seconds) ----------

async def set_mining_cooldown(user_id):
    """Set mining cooldown for a user (30 seconds)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(seconds=30)
        await db.execute(
            "INSERT OR REPLACE INTO mining_cooldowns(user_id, last_mine) VALUES (?, ?)",
            (str(user_id), cooldown_expiry.isoformat())
        )
        await db.commit()

async def get_mining_cooldown(user_id):
    """Get the last mining time for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_mine FROM mining_cooldowns WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

# ---------- FISHING COOLDOWN (40 seconds) ----------

async def set_fishing_cooldown(user_id):
    """Set fishing cooldown for a user (40 seconds)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(seconds=40)
        await db.execute(
            "INSERT OR REPLACE INTO fishing_cooldowns(user_id, last_fish) VALUES (?, ?)",
            (str(user_id), cooldown_expiry.isoformat())
        )
        await db.commit()

async def get_fishing_cooldown(user_id):
    """Get the last fishing time for a user"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_fish FROM fishing_cooldowns WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

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
    """Set fight cooldown for a user in a guild (2 minutes)"""
    from datetime import timedelta
    async with aiosqlite.connect(DB) as db:
        cooldown_expiry = datetime.now() + timedelta(minutes=2)
        await db.execute("INSERT OR REPLACE INTO boss_cooldowns(user_id, guild_id, last_fight) VALUES (?, ?, ?)", (str(user_id), str(guild_id), cooldown_expiry.isoformat()))
        await db.commit()

async def get_fight_cooldown(user_id, guild_id):
    """Get the last fight time for a user in a guild"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT last_fight FROM boss_cooldowns WHERE user_id = ? AND guild_id = ?", (str(user_id), str(guild_id)))
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

async def set_boss_spawn_time(guild_id, boss_type):
    """Guardar el tiempo del último spawn de boss"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO boss_spawn_times(guild_id, boss_type, last_spawn) VALUES (?, ?, ?)",
            (str(guild_id), boss_type, datetime.now().isoformat())
        )
        await db.commit()

async def get_boss_spawn_time(guild_id, boss_type):
    """Obtener el tiempo del último spawn de boss"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT last_spawn FROM boss_spawn_times WHERE guild_id = ? AND boss_type = ?",
            (str(guild_id), boss_type)
        )
        row = await cur.fetchone()
        if row and row[0]:
            return datetime.fromisoformat(row[0])
        return None

# ---------- LEADERBOARDS ----------

async def get_leaderboard(guild_id, stat="dinero", limit=10):
    """Obtener top jugadores por stat"""
    async with aiosqlite.connect(DB) as db:
        query = f"SELECT user_id, {stat} FROM users ORDER BY {stat} DESC LIMIT ?"
        cur = await db.execute(query, (limit,))
        rows = await cur.fetchall()
        return [{"user_id": r[0], stat: r[1]} for r in rows]

# ---------- MISIONES DIARIAS ----------

async def init_daily_mission(user_id, mission_type="work", target=5, reward=500):
    """Crear misión diaria para usuario"""
    async with aiosqlite.connect(DB) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        await db.execute(
            """INSERT OR REPLACE INTO daily_missions(user_id, fecha, tipo, objetivo, progreso, recompensa, completado)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (str(user_id), today, mission_type, target, 0, reward, 0)
        )
        await db.commit()

async def get_daily_mission(user_id):
    """Obtener misión diaria del usuario"""
    async with aiosqlite.connect(DB) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        cur = await db.execute(
            "SELECT * FROM daily_missions WHERE user_id = ? AND fecha = ?",
            (str(user_id), today)
        )
        row = await cur.fetchone()
        if row:
            return {"user_id": row[0], "fecha": row[1], "tipo": row[2], "objetivo": row[3], 
                    "progreso": row[4], "recompensa": row[5], "completado": row[6]}
        return None

async def update_mission_progress(user_id, amount=1):
    """Actualizar progreso de misión"""
    async with aiosqlite.connect(DB) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        await db.execute(
            "UPDATE daily_missions SET progreso = progreso + ? WHERE user_id = ? AND fecha = ?",
            (amount, str(user_id), today)
        )
        await db.commit()

async def complete_mission(user_id):
    """Marcar misión como completada"""
    async with aiosqlite.connect(DB) as db:
        today = datetime.now().strftime("%Y-%m-%d")
        await db.execute(
            "UPDATE daily_missions SET completado = 1 WHERE user_id = ? AND fecha = ?",
            (str(user_id), today)
        )
        await db.commit()

# ---------- TRADING ----------

async def create_trade(sender_id, receiver_id, item_id, asking_item_id):
    """Crear propuesta de trade"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            """INSERT INTO trades(remitente, receptor, item_remitente, item_receptor, estado)
               VALUES (?, ?, ?, ?, 'pendiente')""",
            (str(sender_id), str(receiver_id), item_id, asking_item_id)
        )
        await db.commit()

async def get_pending_trades(user_id):
    """Obtener trades pendientes para usuario"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id, remitente, item_remitente, item_receptor FROM trades WHERE receptor = ? AND estado = 'pendiente'",
            (str(user_id),)
        )
        rows = await cur.fetchall()
        return [{"id": r[0], "remitente": r[1], "item_remitente": r[2], "item_receptor": r[3]} for r in rows]

async def accept_trade(trade_id):
    """Aceptar trade"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE trades SET estado = 'aceptado' WHERE id = ?", (trade_id,))
        await db.commit()

# ---------- MERCADO ----------

async def list_item_for_sale(user_id, item_id, price):
    """Poner item a la venta en el mercado"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO market(vendedor, item_id, precio) VALUES (?, ?, ?)",
            (str(user_id), item_id, price)
        )
        await db.commit()

async def get_market_listings(limit=25):
    """Obtener items en venta"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id, vendedor, item_id, precio FROM market LIMIT ?",
            (limit,)
        )
        rows = await cur.fetchall()
        return [{"id": r[0], "vendedor": r[1], "item_id": r[2], "precio": r[3]} for r in rows]

async def buy_from_market(market_id):
    """Comprar item del mercado"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("DELETE FROM market WHERE id = ?", (market_id,))
        await db.commit()

# ---------- PET XP ----------

async def add_pet_xp(user_id, xp=10):
    """Agregar XP a mascota"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT xp FROM pet_xp WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE pet_xp SET xp = xp + ? WHERE user_id = ?", (xp, str(user_id)))
        else:
            await db.execute("INSERT INTO pet_xp(user_id, xp) VALUES (?, ?)", (str(user_id), xp))
        await db.commit()

async def get_pet_level(user_id):
    """Obtener nivel de mascota (cada 100 XP = 1 nivel)"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT xp FROM pet_xp WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            return row[0] // 100
        return 0

# ---------- DUELOS ----------

async def create_duel(challenger_id, opponent_id, amount):
    """Crear desafío de duelo"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT INTO duels(retador, oponente, cantidad, estado) VALUES (?, ?, ?, 'pendiente')",
            (str(challenger_id), str(opponent_id), amount)
        )
        await db.commit()

async def accept_duel(duel_id):
    """Aceptar duelo"""
    async with aiosqlite.connect(DB) as db:
        await db.execute("UPDATE duels SET estado = 'aceptado' WHERE id = ?", (duel_id,))
        await db.commit()

async def get_pending_duels(user_id):
    """Obtener duelos pendientes"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT id, retador, cantidad FROM duels WHERE oponente = ? AND estado = 'pendiente'",
            (str(user_id),)
        )
        rows = await cur.fetchall()
        return [{"id": r[0], "retador": r[1], "cantidad": r[2]} for r in rows]

# ---------- UPGRADES ----------

async def buy_upgrade(user_id, upgrade_name):
    """Comprar upgrade permanente"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR IGNORE INTO upgrades(user_id, nombre) VALUES (?, ?)",
            (str(user_id), upgrade_name)
        )
        await db.commit()

async def has_upgrade(user_id, upgrade_name):
    """Verificar si usuario tiene upgrade"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute(
            "SELECT 1 FROM upgrades WHERE user_id = ? AND nombre = ?",
            (str(user_id), upgrade_name)
        )
        return await cur.fetchone() is not None

# ---------- CLUB UPGRADES ----------

async def club_has_upgrade(user_id, upgrade_name):
    """Verificar si el club del usuario tiene un upgrade específico"""
    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT 1 FROM club_upgrades cu JOIN club_members cm ON cu.club_id = cm.club_id "
                "WHERE cm.user_id = ? AND cu.upgrade = ?",
                (str(user_id), upgrade_name)
            )
            return await cur.fetchone() is not None
    except:
        return False

async def get_club_bonus(user_id):
    """Calcular bonificador de trabajo basado en dinero del club"""
    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT c.dinero FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                (str(user_id),)
            )
            row = await cur.fetchone()
            if row and row[0]:
                club_money = row[0]
                if club_money >= 50000:
                    return 0.50  # 50% bonus
                elif club_money >= 30000:
                    return 0.35  # 35% bonus
                elif club_money >= 10000:
                    return 0.20  # 20% bonus
                elif club_money >= 5000:
                    return 0.10  # 10% bonus
            return 0
    except:
        return 0

# ---------- MASCOTAS ----------

async def get_pet(user_id):
    """Obtener mascota del usuario"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT nombre, xp, rareza FROM mascotas WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            return {"nombre": row[0], "xp": row[1], "rareza": row[2]}
        return None

async def create_pet(user_id, nombre, rareza="común"):
    """Crear mascota para usuario"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO mascotas(user_id, nombre, xp, rareza, equipada) VALUES (?, ?, ?, ?, ?)",
            (str(user_id), nombre, 0, rareza, 1)
        )
        await db.commit()

async def add_pet_xp(user_id, xp=10):
    """Agregar XP a mascota"""
    async with aiosqlite.connect(DB) as db:
        cur = await db.execute("SELECT xp FROM mascotas WHERE user_id = ?", (str(user_id),))
        row = await cur.fetchone()
        if row:
            await db.execute("UPDATE mascotas SET xp = xp + ? WHERE user_id = ?", (xp, str(user_id)))
        await db.commit()

async def get_pet_level(user_id):
    """Obtener nivel de mascota (cada 100 XP = 1 nivel)"""
    pet = await get_pet(user_id)
    if pet:
        return pet["xp"] // 100
    return 0

async def get_pet_xp_total(user_id):
    """Obtener XP total de mascota"""
    pet = await get_pet(user_id)
    if pet:
        return pet["xp"]
    return 0

async def get_pet_bonus_multiplier(user_id):
    """Obtener multiplicador de bonificadores basado en nivel de mascota"""
    nivel = await get_pet_level(user_id)
    
    # Tabla de bonificadores por nivel
    BONUS_POR_NIVEL = {
        0: 1.0,
        1: 1.05,
        2: 1.10,
        3: 1.15,
        5: 1.25,
        10: 1.50,
        15: 1.75,
        20: 2.0,
    }
    
    # Buscar el multiplicador más cercano (hacia abajo)
    for level in sorted(BONUS_POR_NIVEL.keys(), reverse=True):
        if nivel >= level:
            return BONUS_POR_NIVEL[level]
    
    return 1.0

# ---------- HERRAMIENTAS ----------

async def initialize_user_tools(user_id):
    """Inicializar al usuario con pico normal y caña normal"""
    inv = await get_inventory(user_id)
    
    # Verificar si ya tiene herramientas
    has_pick = any(item["item"].lower() in ["pico normal", "pico mejorado", "pico épico"] for item in inv)
    has_rod = any(item["item"].lower() in ["caña normal", "caña mejorada", "caña épica"] for item in inv)
    
    if not has_pick:
        await add_item_to_user(user_id, "Pico Normal", rareza="comun", usos=1, durabilidad=100, categoria="pico_normal", poder=5)
    
    if not has_rod:
        await add_item_to_user(user_id, "Caña Normal", rareza="comun", usos=1, durabilidad=100, categoria="caña_normal", poder=5)

async def replace_tool(user_id, new_tool_type: str):
    """Reemplazar herramienta antigua con nueva (pico o caña)"""
    inv = await get_inventory(user_id)
    
    if new_tool_type == "mining":
        # Eliminar cualquier pico anterior (normal, mejorado, épico)
        old_picks = [item for item in inv if item["item"].lower() in ["pico normal", "pico mejorado", "pico épico"]]
        for pick in old_picks:
            await remove_item(pick["id"])
    
    elif new_tool_type == "fishing":
        # Eliminar cualquier caña anterior (normal, mejorada, épica)
        old_rods = [item for item in inv if item["item"].lower() in ["caña normal", "caña mejorada", "caña épica"]]
        for rod in old_rods:
            await remove_item(rod["id"])

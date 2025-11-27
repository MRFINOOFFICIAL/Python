import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite

DB = "economy.db"

async def club_autocomplete(interaction: discord.Interaction, current: str):
    """Autocompletado para nombres de clubs"""
    try:
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT nombre FROM clubs WHERE nombre LIKE ? LIMIT 25", (f"%{current}%",))
            rows = await cur.fetchall()
            return [app_commands.Choice(name=row[0][:100], value=row[0]) for row in rows]
    except Exception:
        return []

async def upgrades_autocomplete(interaction: discord.Interaction, current: str):
    """Autocompletado para upgrades disponibles del club"""
    try:
        UPGRADES = {
            "Aula de Entrenamiento": {"costo": 5000, "desc": "+25% dinero en trabajos"},
            "Sala de Meditación": {"costo": 8000, "desc": "+30% XP"},
            "Armería Mejorada": {"costo": 10000, "desc": "+15% daño en combate"},
            "Biblioteca Antigua": {"costo": 6000, "desc": "+20% éxito en minijuegos"},
            "Defensa de Clan": {"costo": 12000, "desc": "+50% HP en batallas de clanes"},
        }
        filtered = [name for name in UPGRADES.keys() if current.lower() in name.lower()] if current else list(UPGRADES.keys())
        return [app_commands.Choice(name=f"{name} ({UPGRADES[name]['costo']}💰)", value=name) for name in filtered[:25]]
    except Exception:
        return []

class ClubsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_club_by_name(self, nombre):
        """Obtener club por nombre"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT id, nombre, lider, dinero, miembros_max FROM clubs WHERE nombre = ?", (nombre,))
            row = await cur.fetchone()
            if row:
                return {"id": row[0], "nombre": row[1], "lider": row[2], "dinero": row[3], "miembros_max": row[4]}
            return None

    async def get_user_club(self, user_id):
        """Obtener club del usuario"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT c.id, c.nombre, c.lider, c.dinero FROM clubs c "
                "JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                (str(user_id),)
            )
            row = await cur.fetchone()
            if row:
                return {"id": row[0], "nombre": row[1], "lider": row[2], "dinero": row[3]}
            return None

    async def get_club_members(self, club_id):
        """Obtener miembros de un club"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT user_id, rango FROM club_members WHERE club_id = ? ORDER BY rango DESC",
                (club_id,)
            )
            rows = await cur.fetchall()
            return [{"user_id": row[0], "rango": row[1]} for row in rows]
    
    async def is_club_leader(self, club_id, user_id):
        """Verificar si el usuario es líder del club"""
        club = await self.get_club_by_id(club_id)
        return club and club["lider"] == str(user_id)
    
    async def get_club_by_id(self, club_id):
        """Obtener club por ID"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute("SELECT id, nombre, lider, dinero, miembros_max FROM clubs WHERE id = ?", (club_id,))
            row = await cur.fetchone()
            if row:
                return {"id": row[0], "nombre": row[1], "lider": row[2], "dinero": row[3], "miembros_max": row[4]}
            return None

    @app_commands.command(name="crear-club", description="🏢 Crear Grupo de Apoyo - Funda tu comunidad de recuperación")
    async def create_club(self, interaction: discord.Interaction, nombre: str):
        """Crear un nuevo club"""
        await interaction.response.defer()
        
        existing = await self.get_club_by_name(nombre)
        if existing:
            await interaction.followup.send("❌ Ya existe un club con ese nombre.")
            return
        
        user_club = await self.get_user_club(interaction.user.id)
        if user_club:
            await interaction.followup.send("❌ Ya estás en un club. Sal del actual para crear uno nuevo.")
            return
        
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "INSERT INTO clubs(nombre, lider) VALUES (?, ?) RETURNING id",
                (nombre, str(interaction.user.id))
            )
            row = await cur.fetchone()
            if not row:
                await interaction.followup.send("❌ Error al crear el club.")
                return
            club_id = row[0]
            
            await db.execute(
                "INSERT INTO club_members(club_id, user_id, rango) VALUES (?, ?, ?)",
                (club_id, str(interaction.user.id), "lider")
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Club **{nombre}** creado exitosamente. ¡Eres el líder!")

    @app_commands.command(name="unirse-club", description="Unirse a un club")
    @app_commands.autocomplete(club=club_autocomplete)
    async def join_club(self, interaction: discord.Interaction, club: str):
        """Unirse a un club"""
        await interaction.response.defer()
        
        club_info = await self.get_club_by_name(club)
        if not club_info:
            await interaction.followup.send("❌ Club no encontrado.")
            return
        
        user_club = await self.get_user_club(interaction.user.id)
        if user_club:
            await interaction.followup.send("❌ Ya estás en un club.")
            return
        
        members = await self.get_club_members(club_info["id"])
        if len(members) >= club_info["miembros_max"]:
            await interaction.followup.send("❌ Club lleno.")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "INSERT INTO club_members(club_id, user_id, rango) VALUES (?, ?, ?)",
                (club_info["id"], str(interaction.user.id), "miembro")
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ ¡Bienvenido a **{club}**!")

    @app_commands.command(name="club-info", description="Ver info de tu club")
    async def club_info(self, interaction: discord.Interaction):
        """Ver información del club"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        members = await self.get_club_members(club["id"])
        
        embed = discord.Embed(
            title=f"🏢 Club: {club['nombre']}",
            color=discord.Color.blue()
        )
        embed.add_field(name="👑 Líder", value=f"<@{club['lider']}>", inline=False)
        embed.add_field(name="💰 Dinero", value=f"{club['dinero']}💰", inline=False)
        embed.add_field(name="👥 Miembros", value=f"{len(members)}/10", inline=False)
        embed.add_field(
            name="📋 Lista de Miembros",
            value="\n".join([f"• <@{m['user_id']}> ({m['rango']})" for m in members]) if members else "Sin miembros",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="salir-club", description="Salir de tu club")
    async def leave_club(self, interaction: discord.Interaction):
        """Salir del club"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] == str(interaction.user.id):
            await interaction.followup.send("❌ El líder no puede salir. Transfiere liderazgo primero.")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "DELETE FROM club_members WHERE club_id = ? AND user_id = ?",
                (club["id"], str(interaction.user.id))
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Saliste de **{club['nombre']}**")

    @app_commands.command(name="depositar-club", description="Depositar dinero a tu club")
    async def deposit_club(self, interaction: discord.Interaction, cantidad: int):
        """Depositar dinero al club - Todos los miembros pueden depositar"""
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La cantidad debe ser mayor a 0.")
            return
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        from db import get_money, add_money
        balance = await get_money(interaction.user.id)
        if balance < cantidad:
            await interaction.followup.send(f"❌ No tienes {cantidad}💰. Tienes {balance}💰")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE users SET dinero = dinero - ? WHERE user_id = ?", (cantidad, str(interaction.user.id)))
            await db.execute("UPDATE clubs SET dinero = dinero + ? WHERE id = ?", (cantidad, club["id"]))
            await db.commit()
        
        await interaction.followup.send(f"✅ Depositaste {cantidad}💰 a **{club['nombre']}**")

    @app_commands.command(name="retirar-club", description="Retirar dinero del club (solo líder)")
    async def withdraw_club(self, interaction: discord.Interaction, cantidad: int):
        """Retirar dinero del club (solo líder)"""
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La cantidad debe ser mayor a 0.")
            return
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede retirar dinero.")
            return
        
        if club["dinero"] < cantidad:
            await interaction.followup.send(f"❌ El club no tiene {cantidad}💰. Tiene {club['dinero']}💰")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE clubs SET dinero = dinero - ? WHERE id = ?", (cantidad, club["id"]))
            await db.execute("UPDATE users SET dinero = dinero + ? WHERE user_id = ?", (cantidad, str(interaction.user.id)))
            await db.commit()
        
        await interaction.followup.send(f"✅ Retiraste {cantidad}💰 del club.")

    @app_commands.command(name="dar-dinero-club", description="Dar dinero a un miembro del club (solo líder)")
    async def give_money_to_member(self, interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        """Dar dinero a un miembro del club - Solo el líder puede hacerlo"""
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La cantidad debe ser mayor a 0.")
            return
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede dar dinero a los miembros.")
            return
        
        # Verificar que el usuario esté en el club
        target_club = await self.get_user_club(usuario.id)
        if not target_club or target_club["id"] != club["id"]:
            await interaction.followup.send("❌ Ese usuario no está en tu club.")
            return
        
        # Verificar que el club tenga suficiente dinero
        if club["dinero"] < cantidad:
            await interaction.followup.send(f"❌ El club no tiene {cantidad}💰. Tiene {club['dinero']}💰")
            return
        
        # Transferir dinero
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE clubs SET dinero = dinero - ? WHERE id = ?", (cantidad, club["id"]))
            await db.execute("UPDATE users SET dinero = dinero + ? WHERE user_id = ?", (cantidad, str(usuario.id)))
            await db.commit()
        
        embed = discord.Embed(
            title="💰 Donación de Club",
            description=f"✅ Diste {cantidad}💰 a {usuario.mention}",
            color=discord.Color.green()
        )
        embed.add_field(name="💚 Generosidad Terapéutica", value=f"El líder del grupo de apoyo compartió recursos para la recuperación grupal.", inline=False)
        embed.set_footer(text=f"Tesorería del club: {club['dinero'] - cantidad}💰")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="expulsar-miembro", description="Expulsar miembro del club (solo líder)")
    async def kick_member(self, interaction: discord.Interaction, usuario: discord.User):
        """Expulsar miembro del club"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede expulsar miembros.")
            return
        
        target_club = await self.get_user_club(usuario.id)
        if not target_club or target_club["id"] != club["id"]:
            await interaction.followup.send("❌ Ese usuario no está en tu club.")
            return
        
        if str(usuario.id) == club["lider"]:
            await interaction.followup.send("❌ No puedes expulsar al líder.")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "DELETE FROM club_members WHERE club_id = ? AND user_id = ?",
                (club["id"], str(usuario.id))
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Expulsaste a {usuario.mention} del club.")

    @app_commands.command(name="promover-miembro", description="Promover miembro a oficial (solo líder)")
    async def promote_member(self, interaction: discord.Interaction, usuario: discord.User):
        """Promover miembro a oficial"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede promover miembros.")
            return
        
        target_club = await self.get_user_club(usuario.id)
        if not target_club or target_club["id"] != club["id"]:
            await interaction.followup.send("❌ Ese usuario no está en tu club.")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute(
                "UPDATE club_members SET rango = 'oficial' WHERE club_id = ? AND user_id = ?",
                (club["id"], str(usuario.id))
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Promoviste a {usuario.mention} a oficial.")

    @app_commands.command(name="clubs", description="🏢 Lista de Grupos de Apoyo del Sanatorio")
    async def list_clubs(self, interaction: discord.Interaction):
        """Listar todos los clubs"""
        await interaction.response.defer()
        
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT id, nombre, lider, dinero, miembros_max FROM clubs ORDER BY dinero DESC LIMIT 20"
            )
            rows = await cur.fetchall()
        
        if not rows:
            await interaction.followup.send("📭 No hay clubs aún.")
            return
        
        embed = discord.Embed(title="🏢 Lista de Clubs", color=discord.Color.gold())
        for row in rows:
            club_id, nombre, lider, dinero, max_m = row
            members = await self.get_club_members(club_id)
            embed.add_field(
                name=f"**{nombre}**",
                value=f"👑 <@{lider}> | 💰 {dinero}💰 | 👥 {len(members)}/{max_m}",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="stats-club", description="Ver estadísticas detalladas del club")
    async def club_stats(self, interaction: discord.Interaction):
        """Ver estadísticas del club"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        members = await self.get_club_members(club["id"])
        
        from db import get_user
        dinero_total = 0
        exp_total = 0
        for member in members:
            user = await get_user(member["user_id"])
            if user:
                dinero_total += user["dinero"]
                exp_total += user["experiencia"]
        
        embed = discord.Embed(title=f"📊 Stats - {club['nombre']}", color=discord.Color.blurple())
        embed.add_field(name="👑 Líder", value=f"<@{club['lider']}>", inline=False)
        embed.add_field(name="💰 Tesorería", value=f"{club['dinero']}💰", inline=False)
        embed.add_field(name="💵 Dinero Total (miembros)", value=f"{dinero_total}💰", inline=False)
        embed.add_field(name="⭐ XP Total (miembros)", value=f"{exp_total} ⭐", inline=False)
        embed.add_field(name="👥 Miembros", value=f"{len(members)}/10", inline=False)
        embed.add_field(name="💪 Poder Total", value=f"{(dinero_total + club['dinero']) // 100} pts", inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="transferir-liderazgo", description="Transferir liderazgo a otro miembro")
    async def transfer_leadership(self, interaction: discord.Interaction, usuario: discord.User):
        """Transferir liderazgo"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede transferir liderazgo.")
            return
        
        target_club = await self.get_user_club(usuario.id)
        if not target_club or target_club["id"] != club["id"]:
            await interaction.followup.send("❌ Ese usuario no está en tu club.")
            return
        
        async with aiosqlite.connect(DB) as db:
            await db.execute("UPDATE clubs SET lider = ? WHERE id = ?", (str(usuario.id), club["id"]))
            await db.execute(
                "UPDATE club_members SET rango = 'oficial' WHERE club_id = ? AND user_id = ?",
                (club["id"], str(interaction.user.id))
            )
            await db.execute(
                "UPDATE club_members SET rango = 'lider' WHERE club_id = ? AND user_id = ?",
                (club["id"], str(usuario.id))
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Transferiste el liderazgo a {usuario.mention}.")

    @app_commands.command(name="upgrades-club", description="Ver upgrades disponibles del club")
    async def club_upgrades(self, interaction: discord.Interaction):
        """Ver upgrades del club"""
        await interaction.response.defer()
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        UPGRADES = {
            "Aula de Entrenamiento": {"costo": 5000, "desc": "+25% dinero en trabajos para todos", "tipo": "trabajo"},
            "Sala de Meditación": {"costo": 8000, "desc": "+30% XP para todos en actividades", "tipo": "xp"},
            "Armería Mejorada": {"costo": 10000, "desc": "+15% daño en combate contra bosses", "tipo": "combate"},
            "Biblioteca Antigua": {"costo": 6000, "desc": "+20% éxito en minijuegos", "tipo": "minigames"},
            "Defensa de Clan": {"costo": 12000, "desc": "+50% HP en batallas", "tipo": "batalla"},
            "Bunker Seguro": {"costo": 12000, "desc": "-25% daño recibido en batallas", "tipo": "batalla"},
            "Escudo Mental": {"costo": 15000, "desc": "40% probabilidad bloquear ataque", "tipo": "batalla"},
            "Fortaleza Emocional": {"costo": 18000, "desc": "Regenera 10 HP por turno", "tipo": "batalla"},
            "Muralla de Resistencia": {"costo": 14000, "desc": "+75% HP en batallas", "tipo": "batalla"},
            "Refugio Psicológico": {"costo": 16000, "desc": "Refleja 15% del daño", "tipo": "batalla"},
        }
        
        owned = []
        available = []
        
        async with aiosqlite.connect(DB) as db:
            for upg_name in UPGRADES.keys():
                cur = await db.execute(
                    "SELECT 1 FROM club_upgrades WHERE club_id = ? AND upgrade = ?",
                    (club["id"], upg_name)
                )
                if await cur.fetchone():
                    owned.append(upg_name)
                else:
                    available.append(upg_name)
        
        embed = discord.Embed(title=f"⚙️ Upgrades — {club['nombre']}", color=discord.Color.blue())
        embed.add_field(name="💰 Tesorería", value=f"{club['dinero']}💰", inline=False)
        
        if owned:
            embed.add_field(name="✅ Comprados", value="\n".join([f"• {u}" for u in owned]), inline=False)
        
        if available:
            value = "\n".join([f"• **{u}** — {UPGRADES[u]['costo']}💰\n  {UPGRADES[u]['desc']}" for u in available])
            embed.add_field(name="🛍️ Disponibles", value=value, inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="comprar-upgrade-club", description="Comprar upgrade para el club (solo líder)")
    @app_commands.autocomplete(upgrade=upgrades_autocomplete)
    async def buy_club_upgrade(self, interaction: discord.Interaction, upgrade: str):
        """Comprar upgrade del club"""
        await interaction.response.defer()
        
        UPGRADES = {
            "Aula de Entrenamiento": {"costo": 5000, "desc": "+25% dinero en trabajos"},
            "Sala de Meditación": {"costo": 8000, "desc": "+30% XP"},
            "Armería Mejorada": {"costo": 10000, "desc": "+15% daño en combate"},
            "Biblioteca Antigua": {"costo": 6000, "desc": "+20% éxito en minijuegos"},
            "Defensa de Clan": {"costo": 12000, "desc": "+50% HP en batallas"},
            "Bunker Seguro": {"costo": 12000, "desc": "-25% daño recibido"},
            "Escudo Mental": {"costo": 15000, "desc": "40% probabilidad bloquear"},
            "Fortaleza Emocional": {"costo": 18000, "desc": "Regenera 10 HP por turno"},
            "Muralla de Resistencia": {"costo": 14000, "desc": "+75% HP"},
            "Refugio Psicológico": {"costo": 16000, "desc": "Refleja 15% daño"},
        }
        
        if upgrade not in UPGRADES:
            await interaction.followup.send("❌ Upgrade no encontrado.")
            return
        
        club = await self.get_user_club(interaction.user.id)
        if not club:
            await interaction.followup.send("❌ No estás en un club.")
            return
        
        if club["lider"] != str(interaction.user.id):
            await interaction.followup.send("❌ Solo el líder puede comprar upgrades.")
            return
        
        costo = UPGRADES[upgrade]["costo"]
        if club["dinero"] < costo:
            await interaction.followup.send(f"❌ Dinero insuficiente. Necesitas {costo}💰 (tienes {club['dinero']}💰)")
            return
        
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT 1 FROM club_upgrades WHERE club_id = ? AND upgrade = ?",
                (club["id"], upgrade)
            )
            if await cur.fetchone():
                await interaction.followup.send("❌ Ya tienes este upgrade.")
                return
            
            await db.execute("UPDATE clubs SET dinero = dinero - ? WHERE id = ?", (costo, club["id"]))
            await db.execute(
                "INSERT INTO club_upgrades(club_id, upgrade) VALUES (?, ?)",
                (club["id"], upgrade)
            )
            await db.commit()
        
        await interaction.followup.send(f"✅ Compraste **{upgrade}** por {costo}💰!\n💡 {UPGRADES[upgrade]['desc']}")

async def setup(bot):
    await bot.add_cog(ClubsCog(bot))

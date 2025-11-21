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

    @app_commands.command(name="crear-club", description="Crear un nuevo club")
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

async def setup(bot):
    await bot.add_cog(ClubsCog(bot))

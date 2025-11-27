import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from datetime import datetime, timedelta
from db import get_money, add_money, get_user, add_experiencia

DB = "economy.db"

# EMOJIS TEMÁTICA PSIQUIÁTRICA
EMOJIS_GUERRA = {
    "batalla": "⚔️",
    "victoria": "🏆",
    "derrota": "💔",
    "vs": "⚡",
    "daño": "💥",
    "critico": "⭐",
    "defensa": "🛡️",
}

class ClanWarsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def get_clan_war_by_id(self, war_id):
        """Obtener guerra de clan por ID"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT id, club1_id, club2_id, estado, ganador, fecha_inicio FROM clan_wars WHERE id = ?",
                (war_id,)
            )
            row = await cur.fetchone()
            if row:
                return {
                    "id": row[0], "club1_id": row[1], "club2_id": row[2],
                    "estado": row[3], "ganador": row[4], "fecha_inicio": row[5]
                }
            return None

    async def get_pending_wars(self, club_id):
        """Obtener guerras pendientes de un club"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT id, club1_id, club2_id FROM clan_wars WHERE (club1_id = ? OR club2_id = ?) AND estado = 'pendiente'",
                (club_id, club_id)
            )
            rows = await cur.fetchall()
            return [{"id": r[0], "club1_id": r[1], "club2_id": r[2]} for r in rows]

    @app_commands.command(name="desafiar-clan", description="⚔️ Desafiar a otro Grupo de Apoyo a una batalla de clanes")
    @app_commands.describe(clan_enemigo="Nombre del Grupo de Apoyo a desafiar")
    async def challenge_clan(self, interaction: discord.Interaction, clan_enemigo: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            async with aiosqlite.connect(DB) as db:
                # Verificar que el usuario está en un clan
                cur = await db.execute(
                    "SELECT c.id, c.nombre FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                mi_clan = await cur.fetchone()
                if not mi_clan:
                    return await interaction.followup.send("❌ Debes estar en un Grupo de Apoyo para desafiar a otro.", ephemeral=True)
                
                mi_club_id, mi_club_nombre = mi_clan
                
                # Verificar que es líder del clan
                cur = await db.execute("SELECT lider FROM clubs WHERE id = ?", (mi_club_id,))
                club_data = await cur.fetchone()
                if club_data and club_data[0] != user_id:
                    return await interaction.followup.send("❌ Solo el líder del Grupo de Apoyo puede desafiar a otro.", ephemeral=True)
                
                # Obtener clan enemigo
                cur = await db.execute("SELECT id, nombre FROM clubs WHERE nombre = ?", (clan_enemigo,))
                enemy_club = await cur.fetchone()
                if not enemy_club:
                    return await interaction.followup.send(f"❌ No existe un Grupo de Apoyo llamado '{clan_enemigo}'.", ephemeral=True)
                
                enemy_club_id, enemy_club_nombre = enemy_club
                
                if mi_club_id == enemy_club_id:
                    return await interaction.followup.send("❌ No puedes retarte a ti mismo.", ephemeral=True)
                
                # Crear desafío de guerra
                await db.execute(
                    "INSERT INTO clan_wars (club1_id, club2_id, estado, fecha_inicio) VALUES (?, ?, 'pendiente', ?)",
                    (mi_club_id, enemy_club_id, datetime.now().isoformat())
                )
                await db.commit()
                
                embed = discord.Embed(
                    title="⚔️ DESAFÍO DE CLANES",
                    description=f"**{mi_club_nombre}** ha desafiado a **{enemy_club_nombre}** a una batalla épica de clanes.",
                    color=discord.Color.red()
                )
                embed.add_field(name="Clan Atacante", value=mi_club_nombre, inline=True)
                embed.add_field(name="Clan Defensor", value=enemy_club_nombre, inline=True)
                embed.set_footer(text="El líder del Grupo Defensor debe aceptar o rechazar con /aceptar-batalla-clan")
                
                await interaction.followup.send(embed=embed)
        except Exception as e:
            print(f"Error en desafiar-clan: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @app_commands.command(name="aceptar-batalla-clan", description="🛡️ Aceptar desafío de batalla de clanes")
    async def accept_clan_war(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            async with aiosqlite.connect(DB) as db:
                # Verificar que el usuario está en un clan
                cur = await db.execute(
                    "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                mi_clan = await cur.fetchone()
                if not mi_clan:
                    return await interaction.followup.send("❌ Debes estar en un Grupo de Apoyo.", ephemeral=True)
                
                mi_club_id = mi_clan[0]
                
                # Verificar que es líder del clan
                cur = await db.execute("SELECT lider FROM clubs WHERE id = ?", (mi_club_id,))
                club_data = await cur.fetchone()
                if club_data and club_data[0] != user_id:
                    return await interaction.followup.send("❌ Solo el líder puede aceptar batallas.", ephemeral=True)
                
                # Obtener desafío pendiente
                cur = await db.execute(
                    "SELECT id, club1_id FROM clan_wars WHERE club2_id = ? AND estado = 'pendiente'",
                    (mi_club_id,)
                )
                war = await cur.fetchone()
                if not war:
                    return await interaction.followup.send("❌ No tienes desafíos pendientes.", ephemeral=True)
                
                war_id, club1_id = war
                
                # Actualizar estado a activo
                await db.execute("UPDATE clan_wars SET estado = 'activo' WHERE id = ?", (war_id,))
                await db.commit()
                
                # Ejecutar batalla
                await self.execute_clan_war(interaction, war_id, club1_id, mi_club_id)
                
        except Exception as e:
            print(f"Error en aceptar-batalla-clan: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    async def execute_clan_war(self, interaction, war_id, club1_id, club2_id):
        """Ejecutar batalla de clan"""
        try:
            async with aiosqlite.connect(DB) as db:
                # Obtener miembros de ambos clanes
                cur = await db.execute("SELECT user_id FROM club_members WHERE club_id = ?", (club1_id,))
                rows = await cur.fetchall()
                club1_members = [str(row[0]) for row in rows] if rows else []
                
                cur = await db.execute("SELECT user_id FROM club_members WHERE club_id = ?", (club2_id,))
                rows = await cur.fetchall()
                club2_members = [str(row[0]) for row in rows] if rows else []
                
                # Obtener datos de clanes
                cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club1_id,))
                club1_row = await cur.fetchone()
                club1_name = club1_row[0] if club1_row else f"Club {club1_id}"
                
                cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club2_id,))
                club2_row = await cur.fetchone()
                club2_name = club2_row[0] if club2_row else f"Club {club2_id}"
                
                # Batalla: cada miembro ataca
                clan1_dmg = 0
                clan2_dmg = 0
                
                for member in club1_members:
                    hit = random.random() < 0.7
                    if hit:
                        dmg = random.randint(25, 75)
                        clan1_dmg += dmg
                
                for member in club2_members:
                    hit = random.random() < 0.7
                    if hit:
                        dmg = random.randint(25, 75)
                        clan2_dmg += dmg
                
                # Determinar ganador
                if clan1_dmg > clan2_dmg:
                    ganador = club1_id
                    ganador_nombre = club1_name
                    winner_members = club1_members
                    loser_members = club2_members
                elif clan2_dmg > clan1_dmg:
                    ganador = club2_id
                    ganador_nombre = club2_name
                    winner_members = club2_members
                    loser_members = club1_members
                else:
                    ganador = None
                    ganador_nombre = "EMPATE"
                    winner_members = []
                    loser_members = []
                
                # Actualizar guerra
                await db.execute(
                    "UPDATE clan_wars SET estado = 'completado', ganador = ? WHERE id = ?",
                    (ganador, war_id)
                )
                
                # Recompensas
                if ganador:
                    # Ganadores reciben dinero y XP
                    for member_id in winner_members:
                        dinero_reward = random.randint(500, 1000)
                        xp_reward = random.randint(100, 200)
                        await db.execute(
                            "UPDATE users SET dinero = dinero + ?, experiencia = experiencia + ? WHERE user_id = ?",
                            (dinero_reward, xp_reward, member_id)
                        )
                    
                    # Perdedores reciben menos
                    for member_id in loser_members:
                        dinero_reward = random.randint(50, 200)
                        xp_reward = random.randint(20, 50)
                        await db.execute(
                            "UPDATE users SET dinero = dinero + ?, experiencia = experiencia + ? WHERE user_id = ?",
                            (dinero_reward, xp_reward, member_id)
                        )
                
                await db.commit()
                
                # Mostrar resultado
                embed = discord.Embed(
                    title="⚔️ BATALLA DE CLANES - RESULTADO",
                    color=discord.Color.gold() if ganador else discord.Color.greyple()
                )
                embed.add_field(name=f"{club1_name} 💥", value=f"{clan1_dmg} daño", inline=True)
                embed.add_field(name=f"{club2_name} 💥", value=f"{clan2_dmg} daño", inline=True)
                embed.add_field(name="🏆 GANADOR", value=ganador_nombre, inline=False)
                
                if ganador:
                    embed.add_field(
                        name="Recompensas",
                        value=f"Ganadores: 500-1000💰 + 100-200 XP\nPerdedores: 50-200💰 + 20-50 XP",
                        inline=False
                    )
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            print(f"Error en execute_clan_war: {e}")
            await interaction.followup.send(f"❌ Error en batalla: {str(e)}", ephemeral=True)

    @app_commands.command(name="guerras-clan", description="📋 Ver guerras de clan activas y pendientes")
    async def view_clan_wars(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            async with aiosqlite.connect(DB) as db:
                # Obtener club del usuario
                cur = await db.execute(
                    "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                club = await cur.fetchone()
                if not club:
                    return await interaction.followup.send("❌ No estás en ningún Grupo de Apoyo.", ephemeral=True)
                
                club_id = club[0]
                
                # Obtener guerras del club
                cur = await db.execute(
                    "SELECT id, club1_id, club2_id, estado, ganador FROM clan_wars WHERE club1_id = ? OR club2_id = ? ORDER BY fecha_inicio DESC",
                    (club_id, club_id)
                )
                wars = await cur.fetchall()
                
                if not wars:
                    return await interaction.followup.send("📭 No tienes guerras registradas.", ephemeral=True)
                
                embed = discord.Embed(
                    title="⚔️ GUERRAS DE CLANES",
                    color=discord.Color.red()
                )
                
                for war in wars[:10]:
                    war_id, club1_id, club2_id, estado, ganador = war
                    
                    cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club1_id,))
                    club1_row = await cur.fetchone()
                    club1_name = club1_row[0] if club1_row else f"Club {club1_id}"
                    
                    cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club2_id,))
                    club2_row = await cur.fetchone()
                    club2_name = club2_row[0] if club2_row else f"Club {club2_id}"
                    
                    status_emoji = "⏳" if estado == "pendiente" else "⚡" if estado == "activo" else "✅"
                    valor = f"{status_emoji} {club1_name} vs {club2_name}"
                    
                    if estado == "completado" and ganador:
                        cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (ganador,))
                        ganador_row = await cur.fetchone()
                        ganador_name = ganador_row[0] if ganador_row else f"Club {ganador}"
                        valor += f"\n🏆 Ganador: {ganador_name}"
                    
                    embed.add_field(name=f"Guerra #{war_id}", value=valor, inline=False)
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            print(f"Error en guerras-clan: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

async def setup(bot):
    await bot.add_cog(ClanWarsCog(bot))

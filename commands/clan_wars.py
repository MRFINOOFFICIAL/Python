import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
import random
from datetime import datetime, timedelta
from db import get_money, add_money, get_user, add_experiencia

DB = "economy.db"

# Estado global de batallas activas: {war_id: {"club1_id": int, "club2_id": int, "club1_hp": int, "club2_hp": int}}
active_wars = {}

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

    async def get_user_war(self, user_id):
        """Obtener guerra activa del usuario"""
        async with aiosqlite.connect(DB) as db:
            cur = await db.execute(
                "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                (str(user_id),)
            )
            club = await cur.fetchone()
            if not club:
                return None
            club_id = club[0]
            
            cur = await db.execute(
                "SELECT id FROM clan_wars WHERE (club1_id = ? OR club2_id = ?) AND estado = 'activo'",
                (club_id, club_id)
            )
            war = await cur.fetchone()
            return war[0] if war else None

    @app_commands.command(name="desafiar-clan", description="⚔️ Desafiar a otro Grupo de Apoyo a una batalla de clanes")
    @app_commands.describe(clan_enemigo="Nombre del Grupo de Apoyo a desafiar")
    async def challenge_clan(self, interaction: discord.Interaction, clan_enemigo: str):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            async with aiosqlite.connect(DB) as db:
                cur = await db.execute(
                    "SELECT c.id, c.nombre FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                mi_clan = await cur.fetchone()
                if not mi_clan:
                    return await interaction.followup.send("❌ Debes estar en un Grupo de Apoyo para desafiar a otro.", ephemeral=True)
                
                mi_club_id, mi_club_nombre = mi_clan
                
                cur = await db.execute("SELECT lider FROM clubs WHERE id = ?", (mi_club_id,))
                club_data = await cur.fetchone()
                if club_data and club_data[0] != user_id:
                    return await interaction.followup.send("❌ Solo el líder del Grupo de Apoyo puede desafiar a otro.", ephemeral=True)
                
                cur = await db.execute("SELECT id, nombre FROM clubs WHERE nombre = ?", (clan_enemigo,))
                enemy_club = await cur.fetchone()
                if not enemy_club:
                    return await interaction.followup.send(f"❌ No existe un Grupo de Apoyo llamado '{clan_enemigo}'.", ephemeral=True)
                
                enemy_club_id, enemy_club_nombre = enemy_club
                
                if mi_club_id == enemy_club_id:
                    return await interaction.followup.send("❌ No puedes retarte a ti mismo.", ephemeral=True)
                
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
                cur = await db.execute(
                    "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                mi_clan = await cur.fetchone()
                if not mi_clan:
                    return await interaction.followup.send("❌ Debes estar en un Grupo de Apoyo.", ephemeral=True)
                
                mi_club_id = mi_clan[0]
                
                cur = await db.execute("SELECT lider FROM clubs WHERE id = ?", (mi_club_id,))
                club_data = await cur.fetchone()
                if club_data and club_data[0] != user_id:
                    return await interaction.followup.send("❌ Solo el líder puede aceptar batallas.", ephemeral=True)
                
                cur = await db.execute(
                    "SELECT id, club1_id FROM clan_wars WHERE club2_id = ? AND estado = 'pendiente'",
                    (mi_club_id,)
                )
                war = await cur.fetchone()
                if not war:
                    return await interaction.followup.send("❌ No tienes desafíos pendientes.", ephemeral=True)
                
                war_id, club1_id = war
                
                await db.execute("UPDATE clan_wars SET estado = 'activo' WHERE id = ?", (war_id,))
                await db.commit()
                
                # Iniciar batalla
                await self.start_clan_war(interaction, war_id, club1_id, mi_club_id)
                
        except Exception as e:
            print(f"Error en aceptar-batalla-clan: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    async def start_clan_war(self, interaction, war_id, club1_id, club2_id):
        """Iniciar batalla de clan interactiva"""
        try:
            async with aiosqlite.connect(DB) as db:
                # Obtener HP base de cada clan (por defensa)
                cur = await db.execute("SELECT COUNT(*) FROM club_members WHERE club_id = ?", (club1_id,))
                club1_row = await cur.fetchone()
                club1_members_count = club1_row[0] if club1_row else 0
                
                cur = await db.execute("SELECT COUNT(*) FROM club_members WHERE club_id = ?", (club2_id,))
                club2_row = await cur.fetchone()
                club2_members_count = club2_row[0] if club2_row else 0
                
                # HP base: 100 por miembro
                club1_hp = club1_members_count * 100
                club2_hp = club2_members_count * 100
                
                # Obtener upgrades de defensa de clan
                cur = await db.execute("SELECT upgrade FROM club_upgrades WHERE club_id = ?", (club1_id,))
                club1_upgrades = [row[0] for row in await cur.fetchall()]
                
                cur = await db.execute("SELECT upgrade FROM club_upgrades WHERE club_id = ?", (club2_id,))
                club2_upgrades = [row[0] for row in await cur.fetchall()]
                
                # Aplicar efectos de defensa
                if "Defensa de Clan" in club1_upgrades:
                    club1_hp = int(club1_hp * 1.5)  # +50%
                if "Muralla de Resistencia" in club1_upgrades:
                    club1_hp = int(club1_hp * 1.75)  # +75%
                
                if "Defensa de Clan" in club2_upgrades:
                    club2_hp = int(club2_hp * 1.5)  # +50%
                if "Muralla de Resistencia" in club2_upgrades:
                    club2_hp = int(club2_hp * 1.75)  # +75%
                
                # Obtener nombres
                cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club1_id,))
                club1_row = await cur.fetchone()
                club1_name = club1_row[0] if club1_row else f"Club {club1_id}"
                
                cur = await db.execute("SELECT nombre FROM clubs WHERE id = ?", (club2_id,))
                club2_row = await cur.fetchone()
                club2_name = club2_row[0] if club2_row else f"Club {club2_id}"
                
                # Guardar estado de batalla
                active_wars[war_id] = {
                    "club1_id": club1_id,
                    "club2_id": club2_id,
                    "club1_hp": club1_hp,
                    "club2_hp": club2_hp,
                    "club1_name": club1_name,
                    "club2_name": club2_name,
                    "club1_upgrades": club1_upgrades,
                    "club2_upgrades": club2_upgrades,
                    "log": []
                }
                
                embed = discord.Embed(
                    title=f"⚔️ BATALLA DE CLANES #{war_id}",
                    description=f"**{club1_name}** vs **{club2_name}**",
                    color=discord.Color.red()
                )
                embed.add_field(name=f"{club1_name} 🩹", value=f"{club1_hp} HP", inline=True)
                embed.add_field(name=f"{club2_name} 🩹", value=f"{club2_hp} HP", inline=True)
                embed.add_field(name="📋 Instrucciones", value="Usa `!atacar` para atacar en batalla. ¡Cada ataque hace 20-50 daño!", inline=False)
                embed.set_footer(text=f"Batalla iniciada a las {datetime.now().strftime('%H:%M:%S')}")
                
                await interaction.followup.send(embed=embed)
                
        except Exception as e:
            print(f"Error en start_clan_war: {e}")
            await interaction.followup.send(f"❌ Error: {str(e)}", ephemeral=True)

    @commands.command(name="atacar")
    async def attack_in_war(self, ctx):
        """Atacar en batalla de clan activa"""
        user_id = str(ctx.author.id)
        
        try:
            # Obtener guerra activa del usuario
            war_id = await self.get_user_war(user_id)
            if not war_id or war_id not in active_wars:
                return await ctx.send("❌ No estás en una batalla de clan activa.", delete_after=5)
            
            war = active_wars[war_id]
            
            async with aiosqlite.connect(DB) as db:
                # Verificar a qué clan pertenece
                cur = await db.execute(
                    "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                club = await cur.fetchone()
                club_id = club[0]
                
                if club_id == war["club1_id"]:
                    # Club 1 ataca a Club 2
                    dmg = random.randint(20, 50)
                    
                    # Aplicar reducciones de defensa de Club 2
                    if "Bunker Seguro" in war["club2_upgrades"]:
                        dmg = int(dmg * 0.75)  # -25% daño
                    
                    # Bloqueo de Escudo Mental
                    blocked = False
                    if "Escudo Mental" in war["club2_upgrades"]:
                        if random.random() < 0.4:  # 40% chance
                            dmg = 0
                            blocked = True
                    
                    # Aplicar daño
                    war["club2_hp"] -= dmg
                    
                    # Reflejo de Refugio Psicológico
                    reflect_dmg = 0
                    if "Refugio Psicológico" in war["club2_upgrades"] and dmg > 0:
                        reflect_dmg = int(dmg * 0.15)  # 15% reflejo
                        war["club1_hp"] -= reflect_dmg
                    
                    attacker = war["club1_name"]
                    defender = war["club2_name"]
                    msg = f"⚔️ **{attacker}** atacó! -{dmg} HP"
                    if blocked:
                        msg += " *(bloqueado por Escudo Mental)*"
                    if reflect_dmg > 0:
                        msg += f"\n💫 **Reflejo**: -{reflect_dmg} HP a {attacker}"
                    msg += f"\n{defender}: {max(0, war['club2_hp'])} HP"
                    
                    # Regeneración de Fortaleza Emocional
                    if "Fortaleza Emocional" in war["club2_upgrades"]:
                        war["club2_hp"] += 10
                        msg += f"\n🌱 **Fortaleza Emocional**: +10 HP a {defender}"
                    
                    # Verificar si club 2 fue derrotado
                    if war["club2_hp"] <= 0:
                        await self.finish_clan_war(ctx, war_id, war["club1_id"], war["club2_id"], war["club1_name"], war["club2_name"])
                        
                elif club_id == war["club2_id"]:
                    # Club 2 ataca a Club 1
                    dmg = random.randint(20, 50)
                    
                    # Aplicar reducciones de defensa de Club 1
                    if "Bunker Seguro" in war["club1_upgrades"]:
                        dmg = int(dmg * 0.75)  # -25% daño
                    
                    # Bloqueo de Escudo Mental
                    blocked = False
                    if "Escudo Mental" in war["club1_upgrades"]:
                        if random.random() < 0.4:  # 40% chance
                            dmg = 0
                            blocked = True
                    
                    # Aplicar daño
                    war["club1_hp"] -= dmg
                    
                    # Reflejo de Refugio Psicológico
                    reflect_dmg = 0
                    if "Refugio Psicológico" in war["club1_upgrades"] and dmg > 0:
                        reflect_dmg = int(dmg * 0.15)  # 15% reflejo
                        war["club2_hp"] -= reflect_dmg
                    
                    attacker = war["club2_name"]
                    defender = war["club1_name"]
                    msg = f"⚔️ **{attacker}** atacó! -{dmg} HP"
                    if blocked:
                        msg += " *(bloqueado por Escudo Mental)*"
                    if reflect_dmg > 0:
                        msg += f"\n💫 **Reflejo**: -{reflect_dmg} HP a {attacker}"
                    msg += f"\n{defender}: {max(0, war['club1_hp'])} HP"
                    
                    # Regeneración de Fortaleza Emocional
                    if "Fortaleza Emocional" in war["club1_upgrades"]:
                        war["club1_hp"] += 10
                        msg += f"\n🌱 **Fortaleza Emocional**: +10 HP a {defender}"
                    
                    # Verificar si club 1 fue derrotado
                    if war["club1_hp"] <= 0:
                        await self.finish_clan_war(ctx, war_id, war["club2_id"], war["club1_id"], war["club2_name"], war["club1_name"])
                else:
                    return await ctx.send("❌ No eres miembro de ningún clan en esta batalla.", delete_after=5)
                
                # Mostrar estado
                embed = discord.Embed(title="⚔️ GOLPE CONECTADO", description=msg, color=discord.Color.orange())
                embed.add_field(name=f"{war['club1_name']} 🩹", value=f"{max(0, war['club1_hp'])} HP", inline=True)
                embed.add_field(name=f"{war['club2_name']} 🩹", value=f"{max(0, war['club2_hp'])} HP", inline=True)
                await ctx.send(embed=embed, delete_after=10)
                
        except Exception as e:
            print(f"Error en atacar: {e}")
            await ctx.send(f"❌ Error: {str(e)}", delete_after=5)

    async def finish_clan_war(self, ctx, war_id, winner_id, loser_id, winner_name, loser_name):
        """Finalizar batalla de clan"""
        try:
            async with aiosqlite.connect(DB) as db:
                # Actualizar BD
                await db.execute(
                    "UPDATE clan_wars SET estado = 'completado', ganador = ? WHERE id = ?",
                    (winner_id, war_id)
                )
                
                # Recompensas
                cur = await db.execute("SELECT user_id FROM club_members WHERE club_id = ?", (winner_id,))
                winner_members = [str(row[0]) for row in await cur.fetchall()]
                
                cur = await db.execute("SELECT user_id FROM club_members WHERE club_id = ?", (loser_id,))
                loser_members = [str(row[0]) for row in await cur.fetchall()]
                
                for member_id in winner_members:
                    dinero_reward = random.randint(500, 1000)
                    xp_reward = random.randint(100, 200)
                    await db.execute(
                        "UPDATE users SET dinero = dinero + ?, experiencia = experiencia + ? WHERE user_id = ?",
                        (dinero_reward, xp_reward, member_id)
                    )
                
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
                title="🏆 BATALLA DE CLANES FINALIZADA",
                description=f"**{winner_name}** ha derrotado a **{loser_name}**",
                color=discord.Color.gold()
            )
            embed.add_field(name="🏆 Ganador", value=winner_name, inline=False)
            embed.add_field(name="Recompensas", 
                value=f"Ganadores: 500-1000💰 + 100-200 XP c/u\nPerdedores: 50-200💰 + 20-50 XP c/u", inline=False)
            
            await ctx.send(embed=embed)
            
            # Limpiar estado
            if war_id in active_wars:
                del active_wars[war_id]
                
        except Exception as e:
            print(f"Error en finish_clan_war: {e}")
            await ctx.send(f"❌ Error finalizando batalla: {str(e)}", delete_after=5)

    @app_commands.command(name="guerras-clan", description="📋 Ver guerras de clan activas y pendientes")
    async def view_clan_wars(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = str(interaction.user.id)
        
        try:
            async with aiosqlite.connect(DB) as db:
                cur = await db.execute(
                    "SELECT c.id FROM clubs c JOIN club_members cm ON c.id = cm.club_id WHERE cm.user_id = ?",
                    (user_id,)
                )
                club = await cur.fetchone()
                if not club:
                    return await interaction.followup.send("❌ No estás en ningún Grupo de Apoyo.", ephemeral=True)
                
                club_id = club[0]
                
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

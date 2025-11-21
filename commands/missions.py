import discord
from discord.ext import commands
from discord import app_commands
from db import (get_daily_mission, init_daily_mission, update_mission_progress, 
                complete_mission, add_money, get_money)

class MissionsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.missions_types = {
            "trabajar": ("Completa 5 trabajos", 5, 500),
            "explorar": ("Explora 3 veces", 3, 400),
            "robar": ("Roba 2 veces exitosamente", 2, 600),
        }

    @app_commands.command(name="misiones", description="Ver tu misión diaria")
    async def missions(self, interaction: discord.Interaction):
        await interaction.response.defer()
        mission = await get_daily_mission(interaction.user.id)
        
        if not mission:
            import random
            tipo = random.choice(list(self.missions_types.keys()))
            desc, obj, reward = self.missions_types[tipo]
            await init_daily_mission(interaction.user.id, tipo, obj, reward)
            mission = await get_daily_mission(interaction.user.id)
        
        embed = discord.Embed(
            title="📋 Misión Diaria",
            description=self.missions_types[mission["tipo"]][0],
            color=discord.Color.blue()
        )
        embed.add_field(name="Progreso", value=f"{mission['progreso']}/{mission['objetivo']}", inline=False)
        embed.add_field(name="Recompensa", value=f"{mission['recompensa']}💰", inline=False)
        embed.add_field(name="Estado", value="✅ Completada" if mission['completado'] else "⏳ En progreso", inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="completar-mision", description="Reclamar recompensa de misión")
    async def complete_mission_cmd(self, interaction: discord.Interaction):
        await interaction.response.defer()
        mission = await get_daily_mission(interaction.user.id)
        
        if not mission:
            await interaction.followup.send("❌ No tienes misión activa.")
            return
        
        if mission['completado']:
            await interaction.followup.send("❌ Ya completaste la misión hoy.")
            return
        
        if mission['progreso'] < mission['objetivo']:
            await interaction.followup.send(f"❌ Te faltan {mission['objetivo'] - mission['progreso']} acciones.")
            return
        
        await add_money(interaction.user.id, mission['recompensa'])
        await complete_mission(interaction.user.id)
        
        embed = discord.Embed(
            title="✅ Misión Completada",
            description=f"Ganaste {mission['recompensa']}💰",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(MissionsCog(bot))

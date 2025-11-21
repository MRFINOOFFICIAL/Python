import discord
from discord.ext import commands
from discord import app_commands
import random
from db import (create_duel, get_pending_duels, accept_duel, 
                add_money, get_user)

async def cantidad_sugerida_autocomplete(interaction: discord.Interaction, current: str):
    """Sugerencias de cantidad para duelos"""
    try:
        user = await get_user(interaction.user.id)
        dinero = user['dinero'] if user else 0
        suggestions = [100, 500, 1000, 5000]
        if dinero >= 10000:
            suggestions.append(10000)
        filtered = [str(c) for c in suggestions if str(c).startswith(current)] if current else [str(c) for c in suggestions]
        return [app_commands.Choice(name=f"{c}💰", value=c) for c in filtered[:5]]
    except Exception:
        return []

class DuelsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="desafiar", description="Desafiar a un jugador a duelo por dinero")
    @app_commands.autocomplete(cantidad=cantidad_sugerida_autocomplete)
    async def challenge(self, interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ Cantidad debe ser mayor a 0.")
            return
        
        user_money = await get_user(interaction.user.id)
        if not user_money or user_money['dinero'] < cantidad:
            await interaction.followup.send(f"❌ No tienes suficiente dinero.")
            return
        
        await create_duel(interaction.user.id, usuario.id, cantidad)
        await interaction.followup.send(f"⚔️ Desafío enviado a {usuario.mention}: {cantidad}💰")

    @app_commands.command(name="mis-duelos", description="Ver desafíos pendientes")
    async def my_duels(self, interaction: discord.Interaction):
        await interaction.response.defer()
        duels = await get_pending_duels(interaction.user.id)
        
        if not duels:
            await interaction.followup.send("No tienes duelos pendientes.")
            return
        
        embed = discord.Embed(title="⚔️ Duelos Pendientes", color=discord.Color.red())
        for duel in duels:
            try:
                user = await self.bot.fetch_user(int(duel['retador']))
                embed.add_field(
                    name=f"ID: {duel['id']} - {user.name}",
                    value=f"Apuesta: {duel['cantidad']}💰",
                    inline=False
                )
            except:
                pass
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(DuelsCog(bot))

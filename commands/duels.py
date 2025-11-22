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
                    value=f"Apuesta: {duel['cantidad']}💰\n\nUsa `/aceptar-duel {duel['id']}` para aceptar",
                    inline=False
                )
            except:
                pass
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="aceptar-duel", description="Aceptar un desafío de duelo")
    async def accept_duel_cmd(self, interaction: discord.Interaction, duel_id: int):
        await interaction.response.defer()
        
        # Aceptar el duelo
        result = await accept_duel(duel_id, interaction.user.id)
        if not result:
            await interaction.followup.send("❌ Duelo no encontrado o ya fue aceptado.")
            return
        
        retador_id = result['retador']
        cantidad = result['cantidad']
        
        # Calcular ganador
        ganador = random.choice([interaction.user.id, int(retador_id)])
        perdedor = int(retador_id) if ganador == interaction.user.id else interaction.user.id
        
        # Transferir dinero
        await add_money(ganador, cantidad)
        await add_money(perdedor, -cantidad)
        
        # Mensaje de resultado
        try:
            ganador_user = await self.bot.fetch_user(ganador)
            perdedor_user = await self.bot.fetch_user(perdedor)
            embed = discord.Embed(
                title="⚔️ ¡Duelo Completado!",
                description=f"**Ganador:** {ganador_user.mention}\n**Perdedor:** {perdedor_user.mention}\n**Cantidad:** {cantidad}💰",
                color=discord.Color.gold()
            )
            await interaction.followup.send(embed=embed)
        except:
            await interaction.followup.send(f"⚔️ Duelo completado. Ganador: <@{ganador}>")

async def setup(bot):
    await bot.add_cog(DuelsCog(bot))

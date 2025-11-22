# commands/fishing.py
"""
Sistema de pesca para encontrar objetos acuáticos.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, add_pet_xp, update_mission_progress, set_fishing_cooldown, get_fishing_cooldown
from datetime import datetime
import random

FISHING_LOOT = [
    ("Pez común", "comun", 1),
    ("Camarón rosado", "comun", 1),
    ("Concha marina", "comun", 1),
    ("Alga preciosa", "comun", 1),
    ("Perla imperfecta", "comun", 1),
    ("Pez dorado", "raro", 1),
    ("Coral rojo", "raro", 1),
    ("Caracol antiguo", "raro", 1),
    ("Pez espada", "epico", 1),
    ("Perla de agua dulce", "epico", 1),
    ("Leviatán pequeño", "legendario", 1),
    ("Sirena petrificada", "maestro", 1),
]

FISHING_WEIGHTS = [35, 30, 25, 25, 30, 15, 12, 10, 5, 4, 2, 1]

class FishingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="pescar")
    @commands.cooldown(1, 40, commands.BucketType.user)
    async def fish_prefix(self, ctx):
        """Comando prefix: pescar"""
        await self._do_fish(ctx.author, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="pescar", description="🎣 Pesca objetos acuáticos")
    async def fish_slash(self, interaction: discord.Interaction):
        """Comando slash: pescar"""
        from datetime import datetime, timedelta
        
        # Verificar cooldown de 40 segundos
        last_fish = await get_fishing_cooldown(interaction.user.id)
        if last_fish and datetime.now() < last_fish:
            remaining = last_fish - datetime.now()
            secs = int(remaining.total_seconds())
            return await interaction.response.send_message(f"⏳ Aún estás pescando. Espera {secs}s.", ephemeral=True)
        
        await interaction.response.defer()
        await self._do_fish(interaction.user, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _do_fish(self, user, send_fn):
        """Lógica de pesca"""
        await set_fishing_cooldown(user.id)
        
        inv = await get_inventory(user.id)
        
        # Seleccionar criatura marina aleatoria
        item = random.choices(FISHING_LOOT, weights=FISHING_WEIGHTS, k=1)[0]
        name, rarity, usos = item
        
        # Si hay espacio en el inventario
        if len(inv) < 3:
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="marino", poder=5)
            await add_pet_xp(user.id, 8)
            await update_mission_progress(user.id)
            
            rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
            
            embed = discord.Embed(
                title=f"{rarity_emoji.get(rarity, '')} 🎣 Pesca",
                description=f"{user.mention}, atrapaste **{name}** ({rarity})!",
                color=discord.Color.blue()
            )
            embed.set_footer(text="Sigue pescando para encontrar criaturas raras.")
            await send_fn(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ Inventario lleno",
                description=f"Atrapaste **{name}** ({rarity}) pero tu inventario está lleno.\n\nUsa `/inventario` para ver tus items.",
                color=discord.Color.orange()
            )
            await send_fn(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

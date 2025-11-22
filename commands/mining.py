# commands/mining.py
"""
Sistema de minería para encontrar minerales y objetos.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, add_pet_xp, update_mission_progress, set_mining_cooldown, get_mining_cooldown
from datetime import datetime
import random

MINING_LOOT = [
    ("Piedra de carbón", "comun", 1),
    ("Cristal azul", "comun", 1),
    ("Mineral de hierro", "comun", 1),
    ("Polvo de cuarzo", "comun", 1),
    ("Roca brillante", "comun", 1),
    ("Esmeralda cruda", "raro", 1),
    ("Diamante sin tallar", "raro", 1),
    ("Cristal de ámbar", "raro", 1),
    ("Gema de rubí", "epico", 1),
    ("Zafiro puro", "epico", 1),
    ("Ópalo místico", "legendario", 1),
    ("Meteorito antiguo", "maestro", 1),
]

MINING_WEIGHTS = [35, 30, 30, 25, 25, 15, 12, 10, 5, 4, 2, 1]

class MiningCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="minar")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def mine_prefix(self, ctx):
        """Comando prefix: minar minerales"""
        await self._do_mine(ctx.author, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="minar", description="⛏️ Mina minerales y cristales")
    async def mine_slash(self, interaction: discord.Interaction):
        """Comando slash: minar"""
        from datetime import datetime, timedelta
        
        # Verificar cooldown de 30 segundos
        last_mine = await get_mining_cooldown(interaction.user.id)
        if last_mine and datetime.now() < last_mine:
            remaining = last_mine - datetime.now()
            secs = int(remaining.total_seconds())
            return await interaction.response.send_message(f"⏳ Aún estás minando. Espera {secs}s.", ephemeral=True)
        
        await interaction.response.defer()
        await self._do_mine(interaction.user, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _do_mine(self, user, send_fn):
        """Lógica de minería"""
        await set_mining_cooldown(user.id)
        
        inv = await get_inventory(user.id)
        
        # Seleccionar mineral aleatorio
        item = random.choices(MINING_LOOT, weights=MINING_WEIGHTS, k=1)[0]
        name, rarity, usos = item
        
        # Si hay espacio en el inventario
        if len(inv) < 3:
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="mineral", poder=5)
            await add_pet_xp(user.id, 8)
            await update_mission_progress(user.id)
            
            rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
            
            embed = discord.Embed(
                title=f"{rarity_emoji.get(rarity, '')} ⛏️ Minería",
                description=f"{user.mention}, extrajiste **{name}** ({rarity})!",
                color=discord.Color.dark_gray()
            )
            embed.set_footer(text="Sigue minando para encontrar gemas raras.")
            await send_fn(embed=embed)
        else:
            embed = discord.Embed(
                title="⚠️ Inventario lleno",
                description=f"Encontraste **{name}** ({rarity}) pero tu inventario está lleno.\n\nUsa `/inventario` para ver tus items.",
                color=discord.Color.orange()
            )
            await send_fn(embed=embed)

async def setup(bot):
    await bot.add_cog(MiningCog(bot))

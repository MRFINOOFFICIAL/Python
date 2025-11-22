# commands/mining.py
"""
Sistema de minería para encontrar minerales y objetos.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, add_pet_xp, update_mission_progress, set_mining_cooldown, get_mining_cooldown, initialize_user_tools
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
        
        # Inicializar herramientas si es la primera vez
        await initialize_user_tools(user.id)
        
        inv = await get_inventory(user.id)
        
        # Verificar si tiene picos mejorados
        has_epic_pick = any(item["item"].lower() == "pico épico" for item in inv)
        has_rare_pick = any(item["item"].lower() == "pico mejorado" for item in inv)
        
        # Ajustar pesos según herramientas
        weights = list(MINING_WEIGHTS)  # Copiar pesos originales
        
        if has_epic_pick:
            # +50% probabilidad para épico/legendario
            weights[8] = int(weights[8] * 1.5)  # Gema de rubí
            weights[9] = int(weights[9] * 1.5)  # Zafiro puro
            weights[10] = int(weights[10] * 1.5)  # Ópalo místico
            weights[11] = int(weights[11] * 1.5)  # Meteorito antiguo
        elif has_rare_pick:
            # +30% probabilidad para raro/épico
            weights[5] = int(weights[5] * 1.3)  # Esmeralda cruda
            weights[6] = int(weights[6] * 1.3)  # Diamante sin tallar
            weights[7] = int(weights[7] * 1.3)  # Cristal de ámbar
            weights[8] = int(weights[8] * 1.3)  # Gema de rubí
        
        # Seleccionar mineral aleatorio
        item = random.choices(MINING_LOOT, weights=weights, k=1)[0]
        name, rarity, usos = item
        
        # Si hay espacio en el inventario
        if len(inv) < 3:
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="mineral", poder=5)
            await add_pet_xp(user.id, 8)
            await update_mission_progress(user.id)
            
            rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
            
            # Mostrar bonus de herramienta si la tiene
            tool_bonus = ""
            if has_epic_pick:
                tool_bonus = "\n✨ **Pico Épico** activado (+50% loot épico/legendario)"
            elif has_rare_pick:
                tool_bonus = "\n✨ **Pico Mejorado** activado (+30% loot raro/épico)"
            
            embed = discord.Embed(
                title=f"{rarity_emoji.get(rarity, '')} ⛏️ Minería",
                description=f"{user.mention}, extrajiste **{name}** ({rarity})!{tool_bonus}",
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

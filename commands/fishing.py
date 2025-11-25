# commands/fishing.py
"""
Sistema de pesca para encontrar objetos acuáticos.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, add_pet_xp, update_mission_progress, set_fishing_cooldown, get_fishing_cooldown, initialize_user_tools
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

    @app_commands.command(name="pescar", description="🎣 Buceo en el Inconsciente - Pesca traumas sumergidos")
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
        
        # Inicializar herramientas si es la primera vez
        await initialize_user_tools(user.id)
        
        inv = await get_inventory(user.id)
        
        # Verificar si tiene cañas mejoradas
        has_epic_rod = any(item["item"].lower() == "caña épica" for item in inv)
        has_rare_rod = any(item["item"].lower() == "caña mejorada" for item in inv)
        
        # ========== MINIJUEGO: DADOS ==========
        # Tirada de dados (1-6) - necesitas 4+ para ganar (33% de probabilidad)
        dado = random.randint(1, 6)
        min_threshold = 4  # Pesca es más difícil que minería
        
        # Si pierdes el minijuego, no obtienes el pez
        if dado < min_threshold:
            embed = discord.Embed(
                title="🎣 Pesca — Fallo",
                description=f"{user.mention} sacaste un {dado} (🎲). ¡El pez se escapó!",
                color=discord.Color.blue()
            )
            embed.add_field(name="❌ Se Escapó", value="El pez fue más rápido. Vuelve a intentar.", inline=False)
            embed.set_footer(text="La paciencia en el inconsciente requiere destreza...")
            return await send_fn(embed=embed)
        
        # Si ganas, obtén el pez
        # Ajustar pesos según herramientas
        weights = list(FISHING_WEIGHTS)  # Copiar pesos originales
        
        if has_epic_rod:
            # +50% probabilidad para épico/legendario
            weights[8] = int(weights[8] * 1.5)  # Pez espada
            weights[9] = int(weights[9] * 1.5)  # Perla de agua dulce
            weights[10] = int(weights[10] * 1.5)  # Leviatán pequeño
            weights[11] = int(weights[11] * 1.5)  # Sirena petrificada
        elif has_rare_rod:
            # +30% probabilidad para raro/épico
            weights[5] = int(weights[5] * 1.3)  # Pez dorado
            weights[6] = int(weights[6] * 1.3)  # Coral rojo
            weights[7] = int(weights[7] * 1.3)  # Caracol antiguo
            weights[8] = int(weights[8] * 1.3)  # Pez espada
        
        # Seleccionar criatura marina aleatoria
        item = random.choices(FISHING_LOOT, weights=weights, k=1)[0]
        name, rarity, usos = item
        
        # Agregar criatura marina al inventario
        await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="marino", poder=5)
        await add_pet_xp(user.id, 8)
        await update_mission_progress(user.id)
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
        
        # Mostrar bonus de herramienta si la tiene
        tool_bonus = ""
        if has_epic_rod:
            tool_bonus = "\n✨ **Caña Épica** activada (+50% loot épico/legendario)"
        elif has_rare_rod:
            tool_bonus = "\n✨ **Caña Mejorada** activada (+30% loot raro/épico)"
        
        embed = discord.Embed(
            title=f"{rarity_emoji.get(rarity, '')} 🎣 Pesca — ¡Éxito!",
            description=f"{user.mention}, sacaste un {dado} (🎲) — ¡Atrapaste **{name}**!{tool_bonus}",
            color=discord.Color.blue()
        )
        embed.add_field(name="💚 Inmersión Profunda", value=f"Rareza: **{rarity}**", inline=False)
        embed.set_footer(text="Sigue pescando para encontrar criaturas raras.")
        await send_fn(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

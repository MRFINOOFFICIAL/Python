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

# Clicks necesarios según rareza
CLICKS_REQUIRED = {
    "comun": 3,
    "raro": 5,
    "epico": 7,
    "legendario": 10,
    "maestro": 15
}

# ========== VISTA DE PESCA: BOTÓN DE CLICKS ==========
class FishingClickView(discord.ui.View):
    def __init__(self, user_id: int, fish_name: str, required_clicks: int, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.fish_name = fish_name
        self.required_clicks = required_clicks
        self.current_clicks = 0
        self.result = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        self.result = False  # Si se acaba el tiempo, perdió
    
    @discord.ui.button(label="🎣 ¡JALA LA CAÑA!", style=discord.ButtonStyle.primary)
    async def click_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.current_clicks += 1
        remaining = self.required_clicks - self.current_clicks
        
        if self.current_clicks >= self.required_clicks:
            # ¡GANÓ!
            self.result = True
            button.disabled = True
            embed = discord.Embed(
                title="🎣 Pesca — ¡Atrapaste el pez!",
                description=f"¡Lo lograste! Atrapaste a **{self.fish_name}** después de {self.current_clicks} jaladas.",
                color=discord.Color.green()
            )
            await interaction.response.edit_message(embed=embed, view=self)
            self.stop()
        else:
            # Sigue intentando
            embed = discord.Embed(
                title="🎣 Pesca — ¡Sigue jalando!",
                description=f"Pez: **{self.fish_name}**\n\nJaladas: {self.current_clicks}/{self.required_clicks}",
                color=discord.Color.blue()
            )
            progress_bar = "▰" * self.current_clicks + "▱" * remaining
            embed.add_field(name="Progreso", value=f"`{progress_bar}`", inline=False)
            await interaction.response.edit_message(embed=embed)

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
        """Lógica de pesca con sistema de clicks"""
        await set_fishing_cooldown(user.id)
        
        # Inicializar herramientas si es la primera vez
        await initialize_user_tools(user.id)
        
        inv = await get_inventory(user.id)
        
        # Verificar si tiene cañas mejoradas
        has_epic_rod = any(item["item"].lower() == "caña épica" for item in inv)
        has_rare_rod = any(item["item"].lower() == "caña mejorada" for item in inv)
        
        # Ajustar pesos según herramientas
        weights = list(FISHING_WEIGHTS)
        
        if has_epic_rod:
            weights[8] = int(weights[8] * 1.5)
            weights[9] = int(weights[9] * 1.5)
            weights[10] = int(weights[10] * 1.5)
            weights[11] = int(weights[11] * 1.5)
        elif has_rare_rod:
            weights[5] = int(weights[5] * 1.3)
            weights[6] = int(weights[6] * 1.3)
            weights[7] = int(weights[7] * 1.3)
            weights[8] = int(weights[8] * 1.3)
        
        # Seleccionar criatura marina aleatoria
        item = random.choices(FISHING_LOOT, weights=weights, k=1)[0]
        name, rarity, usos = item
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
        
        # ========== MINIJUEGO: CLICKS ==========
        required_clicks = CLICKS_REQUIRED.get(rarity, 5)
        view = FishingClickView(user.id, name, required_clicks, timeout=60)
        
        tool_bonus = ""
        if has_epic_rod:
            tool_bonus = "\n✨ **Caña Épica** activada"
        elif has_rare_rod:
            tool_bonus = "\n✨ **Caña Mejorada** activada"
        
        embed = discord.Embed(
            title="🎣 Pesca — ¡Se muerde!",
            description=f"¡Captaste un **{name}** ({rarity})!\n\nNecesitas {required_clicks} jaladas para traerlo.{tool_bonus}",
            color=discord.Color.blue()
        )
        embed.set_footer(text="¡Rápido, jala la caña!")
        
        msg = await send_fn(embed=embed, view=view)
        await view.wait()
        
        if view.result is None or view.result == False:
            # Timeout o fallo
            embed = discord.Embed(
                title="🎣 Pesca — ¡Se Escapó!",
                description="El pez fue más rápido. Se escapó.",
                color=discord.Color.red()
            )
            return await send_fn(embed=embed)
        
        # ¡GANÓ!
        await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="marino", poder=5)
        await add_pet_xp(user.id, 8)
        await update_mission_progress(user.id)
        
        embed = discord.Embed(
            title=f"{rarity_emoji.get(rarity, '')} 🎣 Pesca — ¡Éxito!",
            description=f"¡Obtuviste un **{name}** ({rarity})!",
            color=discord.Color.gold()
        )
        embed.add_field(name="💚 Inmersión Profunda", value="Dominaste al pez con destreza terapéutica.", inline=False)
        await send_fn(embed=embed)

async def setup(bot):
    await bot.add_cog(FishingCog(bot))

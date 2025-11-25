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

# ========== VISTA DE MINERÍA: 4 BOTONES ==========
class MiningButtonsView(discord.ui.View):
    def __init__(self, user_id: int, winning_button: int, timeout: int = 30):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.winning_button = winning_button
        self.result = None
        
    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id
    
    async def on_timeout(self):
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
    
    @discord.ui.button(label="🪨 Piedra 1", style=discord.ButtonStyle.secondary)
    async def button1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_click(interaction, 1)
    
    @discord.ui.button(label="🪨 Piedra 2", style=discord.ButtonStyle.secondary)
    async def button2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_click(interaction, 2)
    
    @discord.ui.button(label="🪨 Piedra 3", style=discord.ButtonStyle.secondary)
    async def button3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_click(interaction, 3)
    
    @discord.ui.button(label="🪨 Piedra 4", style=discord.ButtonStyle.secondary)
    async def button4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.process_click(interaction, 4)
    
    async def process_click(self, interaction: discord.Interaction, button_num: int):
        if button_num == self.winning_button:
            self.result = True
        else:
            self.result = False
        
        for child in self.children:
            if isinstance(child, discord.ui.Button):
                child.disabled = True
        
        await interaction.response.edit_message(view=self)
        self.stop()

class MiningCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="minar")
    @commands.cooldown(1, 30, commands.BucketType.user)
    async def mine_prefix(self, ctx):
        """Comando prefix: minar minerales"""
        await self._do_mine(ctx.author, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="minar", description="⛏️ Excava Traumas - Busca cristales de sanación")
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
        """Lógica de minería con botones interactivos"""
        await set_mining_cooldown(user.id)
        
        # Inicializar herramientas si es la primera vez
        await initialize_user_tools(user.id)
        
        inv = await get_inventory(user.id)
        
        # Verificar si tiene picos mejorados
        has_epic_pick = any(item["item"].lower() == "pico épico" for item in inv)
        has_rare_pick = any(item["item"].lower() == "pico mejorado" for item in inv)
        
        # Ajustar pesos según herramientas
        weights = list(MINING_WEIGHTS)
        
        if has_epic_pick:
            weights[8] = int(weights[8] * 1.5)
            weights[9] = int(weights[9] * 1.5)
            weights[10] = int(weights[10] * 1.5)
            weights[11] = int(weights[11] * 1.5)
        elif has_rare_pick:
            weights[5] = int(weights[5] * 1.3)
            weights[6] = int(weights[6] * 1.3)
            weights[7] = int(weights[7] * 1.3)
            weights[8] = int(weights[8] * 1.3)
        
        # Seleccionar mineral aleatorio
        item = random.choices(MINING_LOOT, weights=weights, k=1)[0]
        name, rarity, usos = item
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠", "maestro": "🔶"}
        
        # ========== MINIJUEGO: 4 BOTONES ==========
        winning_button = random.randint(1, 4)
        view = MiningButtonsView(user.id, winning_button, timeout=30)
        
        tool_bonus = ""
        if has_epic_pick:
            tool_bonus = "\n✨ **Pico Épico** activado"
        elif has_rare_pick:
            tool_bonus = "\n✨ **Pico Mejorado** activado"
        
        embed = discord.Embed(
            title="⛏️ Minería — Elige una Piedra",
            description=f"Elige una de las 4 piedras. En una está el mineral **{name}** ({rarity}).{tool_bonus}",
            color=discord.Color.dark_gray()
        )
        embed.set_footer(text="¡Elige sabiamente!")
        
        msg = await send_fn(embed=embed, view=view)
        await view.wait()
        
        if view.result is None:
            # Timeout
            embed = discord.Embed(
                title="⏳ Minería — Timeout",
                description="Se acabó el tiempo. No obtuviste nada.",
                color=discord.Color.red()
            )
            return await send_fn(embed=embed)
        
        if view.result:
            # ¡GANÓ!
            await add_item_to_user(user.id, name, rarity, usos=usos, durabilidad=100, categoria="mineral", poder=5)
            await add_pet_xp(user.id, 8)
            await update_mission_progress(user.id)
            
            embed = discord.Embed(
                title=f"{rarity_emoji.get(rarity, '')} ⛏️ Minería — ¡Éxito!",
                description=f"¡Acertaste! Encontraste **{name}** ({rarity})",
                color=discord.Color.gold()
            )
            embed.add_field(name="💚 Destreza Terapéutica", value="Tu instinto te llevó al mineral correcto.", inline=False)
        else:
            # PERDIÓ
            embed = discord.Embed(
                title="⛏️ Minería — ¡Fallo!",
                description="Elegiste la piedra incorrecta. La piedra se derrumbó.",
                color=discord.Color.red()
            )
            embed.add_field(name="❌ Sin Suerte", value="No pudiste extraer nada esta vez.", inline=False)
        
        await send_fn(embed=embed)

async def setup(bot):
    await bot.add_cog(MiningCog(bot))

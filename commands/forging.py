# commands/forging.py
"""
Sistema de forja para crear armas únicas.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, add_money, remove_item
from typing import Optional
import random

# Armas por rareza
WEAPONS_BY_RARITY = {
    "comun": [
        ("Espada Leimma", 500),
        ("Espada Gato", 500),
        ("Bastón de Anciano con Clavos", 600),
        ("Daga Ratera", 400),
        ("Espada Pez", 450),
        ("Hélice de Ventilador", 350),
    ],
    "raro": [
        ("Espada de Finno", 2000),
        ("Kratos Espada", 2500),
        ("Espada de Energía del Halo", 2200),
    ],
    "epico": [
        ("Bate Golpeador de Parejas Felices", 8000),
        ("Katana de Musashi Miyamoto", 9000),
    ],
    "legendario": [
        ("Dragón Slayer", 25000),
    ],
}

class ForgeSelectView(discord.ui.View):
    def __init__(self, user_id: int, weapons: list, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.selected_weapon = None
        
        # Agregar botones para cada arma
        for weapon_name, cost in weapons:
            label = f"{weapon_name} ({cost}💰)"
            btn = discord.ui.Button(label=label[:80], style=discord.ButtonStyle.primary)
            
            async def btn_cb(interaction: discord.Interaction, name=weapon_name, c=cost):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ No puedes forjar aquí.", ephemeral=True)
                    return
                self.selected_weapon = (name, c)
                await interaction.response.defer()
                self.stop()
            
            btn.callback = btn_cb
            self.add_item(btn)

class ForgingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="forjar", description="🔨 Forja armas únicas")
    @app_commands.describe(rareza="Rareza del arma: comun, raro, epico, legendario")
    async def forge(self, interaction: discord.Interaction, rareza: str):
        """Forjar armas únicas"""
        await interaction.response.defer()
        
        rareza = rareza.lower()
        
        # Validar rareza
        if rareza not in WEAPONS_BY_RARITY:
            await interaction.followup.send(f"❌ Rareza no válida. Usa: comun, raro, epico, legendario")
            return
        
        weapons = WEAPONS_BY_RARITY[rareza]
        
        # Crear embed con opciones
        embed = discord.Embed(
            title="🔨 Forja de Armas",
            description=f"Selecciona el arma **{rareza.upper()}** que deseas forjar:",
            color=discord.Color.gold()
        )
        
        for weapon_name, cost in weapons:
            embed.add_field(
                name=f"⚔️ {weapon_name}",
                value=f"```{cost:,} 💰```",
                inline=False
            )
        
        embed.set_footer(text="Selecciona un arma para forjarla")
        
        view = ForgeSelectView(interaction.user.id, weapons, timeout=30)
        await interaction.followup.send(embed=embed, view=view)
        
        await view.wait()
        
        if not view.selected_weapon:
            return
        
        weapon_name, cost = view.selected_weapon
        user_id = interaction.user.id
        
        # Verificar dinero
        from db import get_user
        user = await get_user(user_id)
        if not user or user['dinero'] < cost:
            return await interaction.followup.send(f"❌ No tienes suficiente dinero. Necesitas {cost}💰")
        
        # Descontar dinero
        await add_money(user_id, -cost)
        
        # Agregar arma
        await add_item_to_user(user_id, weapon_name, rareza=rareza, usos=1, durabilidad=100, categoria="arma_forjada", poder=40)
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠"}
        
        result_embed = discord.Embed(
            title="✅ ¡Arma Forjada!",
            description=f"{rarity_emoji.get(rareza, '')} Has forjado exitosamente:\n\n**{weapon_name}** ({rareza.upper()})",
            color=discord.Color.gold()
        )
        result_embed.add_field(name="💸 Costo", value=f"`{cost:,}` 💰", inline=False)
        result_embed.add_field(name="📦 Inventario", value=f"El arma fue agregada a tu inventario", inline=False)
        
        await interaction.followup.send(embed=result_embed)

async def setup(bot):
    await bot.add_cog(ForgingCog(bot))

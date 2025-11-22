# commands/forging.py
"""
Sistema de forja para crear armas únicas usando objetos de minería y pesca.
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import add_item_to_user, get_inventory, remove_item
from typing import Optional, List, Tuple

# Armas por rareza con sus requisitos
WEAPONS_RECIPES = {
    "comun": [
        {
            "name": "Espada Leimma",
            "materials": [("Piedra de carbón", 2)],
            "description": "Una espada forjada con piedra de carbón"
        },
        {
            "name": "Espada Gato",
            "materials": [("Pez común", 2), ("Polvo de cuarzo", 1)],
            "description": "Espada inspirada en felinos, forjada con materiales acuáticos"
        },
        {
            "name": "Bastón de Anciano con Clavos",
            "materials": [("Mineral de hierro", 3)],
            "description": "Bastón antiguo reforzado con hierro"
        },
        {
            "name": "Daga Ratera",
            "materials": [("Cristal azul", 2)],
            "description": "Daga pequeña hecha de cristal afilado"
        },
        {
            "name": "Espada Pez",
            "materials": [("Pez común", 3)],
            "description": "Espada que parece un pez gigante"
        },
        {
            "name": "Hélice de Ventilador",
            "materials": [("Polvo de cuarzo", 2), ("Camarón rosado", 1)],
            "description": "Hélice afilada forjada en metal"
        },
    ],
    "raro": [
        {
            "name": "Espada de Finno",
            "materials": [("Esmeralda cruda", 2), ("Pez dorado", 2)],
            "description": "Espada legendaria de Finno, rara y valiosa"
        },
        {
            "name": "Kratos Espada",
            "materials": [("Diamante sin tallar", 2), ("Coral rojo", 2)],
            "description": "Espada de un dios guerrero, imponente"
        },
        {
            "name": "Espada de Energía del Halo",
            "materials": [("Cristal de ámbar", 3), ("Caracol antiguo", 1)],
            "description": "Espada que brilla con energía cósmica"
        },
    ],
    "epico": [
        {
            "name": "Bate Golpeador de Parejas Felices",
            "materials": [("Gema de rubí", 2), ("Pez espada", 2), ("Concha marina", 1)],
            "description": "Bate épico que golpea con precisión"
        },
        {
            "name": "Katana de Musashi Miyamoto",
            "materials": [("Zafiro puro", 3), ("Pez espada", 1)],
            "description": "Katana maestra del legendario Musashi"
        },
    ],
    "legendario": [
        {
            "name": "Dragón Slayer",
            "materials": [("Ópalo místico", 2), ("Leviatán pequeño", 1), ("Meteorito antiguo", 1)],
            "description": "La espada definitiva para matar dragones"
        },
    ],
}

class ForgeSelectView(discord.ui.View):
    def __init__(self, user_id: int, weapons: list, timeout: int = 60):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.selected_weapon = None
        
        # Agregar botones para cada arma
        for i, weapon_data in enumerate(weapons):
            weapon_name = weapon_data["name"]
            label = f"{i+1}. {weapon_name}"
            btn = discord.ui.Button(label=label[:80], style=discord.ButtonStyle.primary)
            
            async def btn_cb(interaction: discord.Interaction, data=weapon_data):
                if interaction.user.id != self.user_id:
                    await interaction.response.send_message("❌ No puedes forjar aquí.", ephemeral=True)
                    return
                self.selected_weapon = data
                await interaction.response.defer()
                self.stop()
            
            btn.callback = btn_cb
            self.add_item(btn)

class ForgingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_weapon_requirements_str(self, materials: List[Tuple[str, int]]) -> str:
        """Formatea los requisitos de materiales"""
        return "\n".join([f"• {amount}x {material}" for material, amount in materials])

    @app_commands.command(name="forjar", description="🔨 Forja armas únicas con materiales minados/pescados")
    @app_commands.describe(rareza="Rareza del arma: comun, raro, epico, legendario")
    async def forge(self, interaction: discord.Interaction, rareza: str):
        """Forjar armas únicas usando materiales de minería y pesca"""
        await interaction.response.defer()
        
        rareza = rareza.lower()
        
        # Validar rareza
        if rareza not in WEAPONS_RECIPES:
            await interaction.followup.send(f"❌ Rareza no válida. Usa: comun, raro, epico, legendario")
            return
        
        weapons = WEAPONS_RECIPES[rareza]
        
        # Crear embed con opciones
        embed = discord.Embed(
            title="🔨 Forja de Armas",
            description=f"Selecciona el arma **{rareza.upper()}** que deseas forjar:",
            color=discord.Color.gold()
        )
        
        for i, weapon_data in enumerate(weapons, 1):
            requirements = self.get_weapon_requirements_str(weapon_data["materials"])
            embed.add_field(
                name=f"{i}. ⚔️ {weapon_data['name']}",
                value=f"```\n{requirements}```",
                inline=False
            )
        
        embed.set_footer(text="Selecciona un arma para forjarla (debes tener los materiales)")
        
        view = ForgeSelectView(interaction.user.id, weapons, timeout=30)
        await interaction.followup.send(embed=embed, view=view)
        
        await view.wait()
        
        if not view.selected_weapon:
            return
        
        weapon_data = view.selected_weapon
        weapon_name = weapon_data["name"]
        materials = weapon_data["materials"]
        user_id = interaction.user.id
        
        # Obtener inventario del usuario
        inv = await get_inventory(user_id)
        
        # Verificar que tiene todos los materiales
        for material_name, amount_needed in materials:
            amount_have = sum(1 for item in inv if item["item"].lower() == material_name.lower())
            if amount_have < amount_needed:
                return await interaction.followup.send(
                    f"❌ No tienes suficientes materiales.\n"
                    f"**{material_name}**: tienes {amount_have}, necesitas {amount_needed}"
                )
        
        # Consumir materiales (eliminar del inventario)
        for material_name, amount_needed in materials:
            consumed = 0
            for item in inv:
                if consumed >= amount_needed:
                    break
                if item["item"].lower() == material_name.lower():
                    await remove_item(item["id"])
                    consumed += 1
        
        # Agregar arma forjada
        await add_item_to_user(user_id, weapon_name, rareza=rareza, usos=1, durabilidad=100, categoria="arma_forjada", poder=45)
        
        rarity_emoji = {"comun": "⚪", "raro": "🔵", "epico": "🟣", "legendario": "🟠"}
        
        result_embed = discord.Embed(
            title="✅ ¡Arma Forjada Exitosamente!",
            description=f"{rarity_emoji.get(rareza, '')} **{weapon_name}** ({rareza.upper()})",
            color=discord.Color.gold()
        )
        
        materials_used = self.get_weapon_requirements_str(materials)
        result_embed.add_field(name="📦 Materiales Consumidos", value=f"```\n{materials_used}```", inline=False)
        result_embed.add_field(name="✨ Resultado", value=f"El arma fue agregada a tu inventario", inline=False)
        
        await interaction.followup.send(embed=result_embed)

async def setup(bot):
    await bot.add_cog(ForgingCog(bot))

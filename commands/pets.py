"""
Sistema de mascotas con XP progresivo.
Comandos: /mi-mascota, /mascotas-disponibles, /cambiar-mascota
"""
import discord
from discord.ext import commands
from discord import app_commands
from db import get_pet, create_pet, get_pet_level, get_pet_xp_total, get_money, add_money

MASCOTAS = {
    "chihuahua": {"rareza": "común", "emojis": "🐕", "precio": 500, "poder": 5},
    "gato": {"rareza": "común", "emojis": "🐱", "precio": 500, "poder": 5},
    "perro": {"rareza": "común", "emojis": "🐶", "precio": 500, "poder": 5},
    "loro": {"rareza": "común", "emojis": "🦜", "precio": 500, "poder": 5},
    "conejo": {"rareza": "raro", "emojis": "🐰", "precio": 2500, "poder": 12},
    "hamster": {"rareza": "raro", "emojis": "🐹", "precio": 2500, "poder": 12},
    "dragón": {"rareza": "épico", "emojis": "🐉", "precio": 10000, "poder": 25},
    "fenix": {"rareza": "épico", "emojis": "🔥", "precio": 10000, "poder": 25},
    "saviteto": {"rareza": "legendario", "emojis": "✨", "precio": 50000, "poder": 50},
    "finopeluche": {"rareza": "legendario", "emojis": "💎", "precio": 50000, "poder": 50},
    "mechones": {"rareza": "legendario", "emojis": "👑", "precio": 50000, "poder": 50},
}

BONUS_POR_NIVEL = {
    0: {"dinero": 1.0, "xp": 1.0},
    1: {"dinero": 1.05, "xp": 1.05},
    2: {"dinero": 1.10, "xp": 1.10},
    3: {"dinero": 1.15, "xp": 1.15},
    5: {"dinero": 1.25, "xp": 1.25},
    10: {"dinero": 1.50, "xp": 1.50},
    15: {"dinero": 1.75, "xp": 1.75},
    20: {"dinero": 2.0, "xp": 2.0},
}

async def mascota_autocomplete(interaction: discord.Interaction, current: str):
    """Autocompletado para mascotas disponibles"""
    try:
        user_money = await get_money(interaction.user.id)
        available = [name for name, data in MASCOTAS.items() if data["precio"] <= user_money and current.lower() in name.lower()]
        return [app_commands.Choice(name=f"{name} ({data['rareza']})", value=name) for name, data in MASCOTAS.items() if name in available][:25]
    except Exception:
        return []

class PetsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mi-mascota", description="Ver tu mascota actual")
    async def my_pet(self, interaction: discord.Interaction):
        """Ver mascota del usuario"""
        await interaction.response.defer()
        
        pet = await get_pet(interaction.user.id)
        if not pet:
            embed = discord.Embed(
                title="🐾 Sin Mascota",
                description="No tienes mascota. Compra un huevo de mascota en `/shop` y úsalo con `/use` para eclosionarlo.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            return
        
        nivel = await get_pet_level(interaction.user.id)
        xp_total = await get_pet_xp_total(interaction.user.id)
        xp_para_siguiente = 100 - (xp_total % 100)
        
        data = MASCOTAS.get(pet["nombre"], {})
        emoji = data.get("emojis", "🐾")
        
        embed = discord.Embed(
            title=f"{emoji} {pet['nombre'].capitalize()}",
            description=f"**Rareza:** {pet['rareza'].upper()}\n**Nivel:** {nivel}\n**XP:** {xp_total}",
            color=discord.Color.gold()
        )
        embed.add_field(name="Poder", value=f"{data.get('poder', 0)} ⚡", inline=True)
        embed.add_field(name="Siguiente Nivel", value=f"{xp_para_siguiente} XP", inline=True)
        
        bonus_nivel = BONUS_POR_NIVEL.get(nivel, BONUS_POR_NIVEL.get(max([k for k in BONUS_POR_NIVEL.keys() if k <= nivel], default=0)))
        if bonus_nivel:
            embed.add_field(
                name="Bonificadores Actuales",
                value=f"💰 Dinero: +{(bonus_nivel['dinero']-1)*100:.0f}%\n📊 XP: +{(bonus_nivel['xp']-1)*100:.0f}%",
                inline=False
            )
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mascotas-disponibles", description="Ver todas las mascotas disponibles")
    async def available_pets(self, interaction: discord.Interaction):
        """Listar mascotas disponibles"""
        await interaction.response.defer()
        
        embed = discord.Embed(
            title="🐾 Mascotas Disponibles",
            color=discord.Color.blue()
        )
        
        por_rareza = {}
        for nombre, data in MASCOTAS.items():
            rareza = data["rareza"]
            if rareza not in por_rareza:
                por_rareza[rareza] = []
            por_rareza[rareza].append((nombre, data))
        
        for rareza in ["común", "raro", "épico", "legendario"]:
            if rareza in por_rareza:
                mascotas_text = "\n".join([
                    f"{data['emojis']} **{nombre.capitalize()}** - {data['precio']}💰 (Poder: {data['poder']})"
                    for nombre, data in por_rareza[rareza]
                ])
                embed.add_field(name=f"{rareza.upper()}", value=mascotas_text, inline=False)
        
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="cambiar-mascota", description="Cambiar a otra mascota")
    @app_commands.autocomplete(nombre=mascota_autocomplete)
    async def change_pet(self, interaction: discord.Interaction, nombre: str):
        """Cambiar mascota actual"""
        await interaction.response.defer()
        
        nombre = nombre.lower()
        if nombre not in MASCOTAS:
            await interaction.followup.send("❌ Mascota no encontrada.")
            return
        
        pet = await get_pet(interaction.user.id)
        if not pet:
            await interaction.followup.send("❌ No tienes mascota. Compra un huevo de mascota en `/shop` y úsalo con `/use`.")
            return
        
        data = MASCOTAS[nombre]
        dinero = await get_money(interaction.user.id)
        
        if dinero < data["precio"]:
            await interaction.followup.send(f"❌ No tienes suficiente dinero. Necesitas {data['precio']}💰")
            return
        
        await add_money(interaction.user.id, -data["precio"])
        await create_pet(interaction.user.id, nombre, data["rareza"])
        
        embed = discord.Embed(
            title="✅ Mascota Cambiada",
            description=f"{data['emojis']} Cambiaste a un **{nombre}**!\n\nTu {pet['nombre']} ha sido reemplazado.",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PetsCog(bot))

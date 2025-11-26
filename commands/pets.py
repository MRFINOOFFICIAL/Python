"""
Sistema de mascotas con XP progresivo, habilidades únicas y utilidades prácticas.
Comandos: /mi-mascota, /mis-mascotas, /mascotas-disponibles, /acariciar-mascota
"""
import discord
from discord.ext import commands
from discord import app_commands, ui
from db import get_pet, get_all_pets, create_pet, get_pet_level, get_pet_xp_total, get_money, add_money, set_active_pet, add_pet_xp
from datetime import datetime, timedelta
import random

MASCOTAS = {
    "chihuahua": {"rareza": "común", "emojis": "🐕", "precio": 500, "poder": 5, "desc": "Compañero leal de apoyo emocional", "habilidad": "Alerta: Detecta robos reduciendo su éxito en -15%"},
    "gato": {"rareza": "común", "emojis": "🐱", "precio": 500, "poder": 5, "desc": "Felino sanador del alma", "habilidad": "Independencia: +10% dinero en /work"},
    "perro": {"rareza": "común", "emojis": "🐶", "precio": 500, "poder": 5, "desc": "Perro de servicio psicológico", "habilidad": "Lealtad: +5% daño en combate"},
    "loro": {"rareza": "común", "emojis": "🦜", "precio": 500, "poder": 5, "desc": "Ave parlante que escucha tus traumas", "habilidad": "Sabiduría: +10% XP ganado"},
    "conejo": {"rareza": "raro", "emojis": "🐰", "precio": 2500, "poder": 12, "desc": "Conejo saltador de alegría", "habilidad": "Velocidad: +15% dinero en /work"},
    "hamster": {"rareza": "raro", "emojis": "🐹", "precio": 2500, "poder": 12, "desc": "Pequeño roedor de esperanza", "habilidad": "Acumulación: Guarda 5% de dinero ganado para recompensa diaria"},
    "basura ann": {"rareza": "raro", "emojis": "🗑️", "precio": 2500, "poder": 12, "desc": "Tacho de basura que absorbe desperdicios emocionales", "habilidad": "Protección: Reduce robos exitosos en -25%"},
    "dragón": {"rareza": "épico", "emojis": "🐉", "precio": 10000, "poder": 25, "desc": "Dragón sanador de fuego interior", "habilidad": "Fuego: +20% daño en combate contra jefes"},
    "fenix": {"rareza": "épico", "emojis": "🔥", "precio": 10000, "poder": 25, "desc": "Ave del renacimiento emocional", "habilidad": "Resurrección: +25% dinero y XP en victorias"},
    "saviteto": {"rareza": "legendario", "emojis": "✨", "precio": 50000, "poder": 50, "desc": "Ser mítico de sanación absoluta", "habilidad": "Sanación: Bloquea 40% de robos, gana 500💰 diarios"},
    "finopeluche": {"rareza": "legendario", "emojis": "💎", "precio": 50000, "poder": 50, "desc": "Peluche mágico de la verdad final", "habilidad": "Verdad: +50% dinero en /work y bloques 35% robos"},
    "mechones": {"rareza": "legendario", "emojis": "👑", "precio": 50000, "poder": 50, "desc": "Rey de la recuperación mental", "habilidad": "Imperio: +30% daño, +500💰 diarios, bloquea 45% robos"},
}

# Habilidades por mascota - Defensa contra robos
PET_ABILITIES = {
    "chihuahua": {"rob_defense": 0.15},
    "gato": {"work_bonus": 0.10},
    "perro": {"combat_bonus": 0.05},
    "loro": {"xp_bonus": 0.10},
    "conejo": {"work_bonus": 0.15},
    "hamster": {"daily_reward": 0.05},
    "basura ann": {"rob_defense": 0.25},
    "dragón": {"combat_bonus": 0.20, "boss_bonus": 0.15},
    "fenix": {"reward_multiplier": 0.25},
    "saviteto": {"rob_defense": 0.40, "daily_dinero": 500},
    "finopeluche": {"work_bonus": 0.50, "rob_defense": 0.35},
    "mechones": {"combat_bonus": 0.30, "rob_defense": 0.45, "daily_dinero": 500},
}

# Tabla de cooldowns para /acariciar-mascota
PET_INTERACTION_COOLDOWNS = {}

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

class PetsChangerView(ui.View):
    def __init__(self, user_id, pets, timeout=120):
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.pets = pets
        self.selected_pet = None
        
        options = []
        for pet in pets:
            emoji = MASCOTAS.get(pet["nombre"].lower(), {}).get("emojis", "🐾")
            label = f"{emoji} {pet['nombre']} (Nivel {pet['xp'] // 100})"
            value = str(pet["id"])
            options.append(discord.SelectOption(label=label, value=value, default=pet["activa"]))
        
        self.select = ui.Select(placeholder="Elige tu mascota activa...", options=options, min_values=1, max_values=1)
        self.select.callback = self.on_select
        self.add_item(self.select)
    
    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.user_id:
            await interaction.response.defer()
            return
        
        pet_id = int(self.select.values[0])
        await set_active_pet(self.user_id, pet_id)
        self.selected_pet = pet_id
        
        pet = next((p for p in self.pets if p["id"] == pet_id), None)
        if pet:
            emoji = MASCOTAS.get(pet["nombre"].lower(), {}).get("emojis", "🐾")
            await interaction.response.edit_message(content=f"✅ {emoji} **{pet['nombre']}** is now active!")
        self.stop()

class PetsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @app_commands.command(name="mi-mascota", description="Ver tu mascota activa")
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
        
        data = MASCOTAS.get(pet["nombre"].lower(), {})
        emoji = data.get("emojis", "🐾")
        
        embed = discord.Embed(
            title=f"{emoji} {pet['nombre'].capitalize()} (ACTIVA)",
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
        
        embed.set_footer(text="Usa /mis-mascotas para ver todas tus mascotas y cambiar la activa")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="mis-mascotas", description="Ver todas tus mascotas y cambiar la activa")
    async def all_pets(self, interaction: discord.Interaction):
        """Ver todas las mascotas y cambiar activa"""
        await interaction.response.defer()
        
        pets = await get_all_pets(interaction.user.id)
        if not pets:
            embed = discord.Embed(
                title="🐾 Sin Mascotas",
                description="No tienes ninguna mascota. Compra un huevo de mascota en `/shop` y úsalo con `/use`.",
                color=discord.Color.blue()
            )
            await interaction.followup.send(embed=embed)
            return
        
        # Embed con lista de mascotas
        embed = discord.Embed(
            title="🐾 Mis Mascotas",
            description=f"**Total:** {len(pets)} mascota(s)",
            color=discord.Color.gold()
        )
        
        for pet in pets:
            nivel = pet["xp"] // 100
            data = MASCOTAS.get(pet["nombre"].lower(), {})
            emoji = data.get("emojis", "🐾")
            active_badge = "✅ ACTIVA" if pet["activa"] else ""
            
            embed.add_field(
                name=f"{emoji} {pet['nombre']} {active_badge}",
                value=f"`{pet['rareza'].upper()}` | Nivel {nivel} | {pet['xp']} XP",
                inline=False
            )
        
        # View con selector
        view = PetsChangerView(interaction.user.id, pets)
        embed.set_footer(text="Usa el selector para cambiar tu mascota activa")
        await interaction.followup.send(embed=embed, view=view)

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
                    f"{data['emojis']} **{nombre.capitalize()}** (Poder: {data['poder']})\n⚡ {data['habilidad']}"
                    for nombre, data in por_rareza[rareza]
                ])
                embed.add_field(name=f"{rareza.upper()}", value=mascotas_text, inline=False)
        
        embed.set_footer(text="Compra huevos de mascotas en /shop para coleccionar más. Usa /acariciar-mascota diariamente!")
        await interaction.followup.send(embed=embed)

    @app_commands.command(name="acariciar-mascota", description="Interactúa con tu mascota diariamente para ganar recompensas")
    async def pet_interaction(self, interaction: discord.Interaction):
        """Interactuar con mascota para ganar recompensas diarias"""
        await interaction.response.defer()
        user_id = interaction.user.id
        
        # Verificar cooldown (1 vez por día)
        now = datetime.now()
        last_interaction = PET_INTERACTION_COOLDOWNS.get(user_id)
        if last_interaction and now < last_interaction:
            remaining = last_interaction - now
            hours, remainder = divmod(int(remaining.total_seconds()), 3600)
            minutes = remainder // 60
            return await interaction.followup.send(f"⏳ Ya acariciaste hoy. Vuelve en {hours}h {minutes}m.", ephemeral=True)
        
        pet = await get_pet(user_id)
        if not pet:
            return await interaction.followup.send("🐾 No tienes mascota activa. Compra un huevo en `/shop`.", ephemeral=True)
        
        # Actualizar cooldown
        PET_INTERACTION_COOLDOWNS[user_id] = now + timedelta(days=1)
        
        # Ganar XP
        xp_gained = random.randint(15, 35)
        await add_pet_xp(user_id, xp_gained)
        
        # Recompensas según mascota
        pet_name = pet["nombre"].lower()
        abilities = PET_ABILITIES.get(pet_name, {})
        
        rewards = f"📊 +{xp_gained} XP"
        dinero_reward = 0
        
        # Recompensa diaria especial
        if "daily_dinero" in abilities:
            dinero_reward = abilities["daily_dinero"]
            dinero_reward += random.randint(100, 300)
        else:
            dinero_reward = random.randint(200, 500)
        
        await add_money(user_id, dinero_reward)
        rewards += f"\n💰 +{dinero_reward}💰"
        
        # Info de habilidad
        emoji = MASCOTAS.get(pet_name, {}).get("emojis", "🐾")
        level = pet["xp"] // 100
        
        embed = discord.Embed(
            title=f"{emoji} Sesión de Terapia con {pet['nombre'].capitalize()}",
            description=f"¡Tu mascota está feliz contigo! Nivel: {level}",
            color=discord.Color.green()
        )
        embed.add_field(name="🎁 Recompensas", value=rewards, inline=False)
        embed.add_field(name="⚡ Habilidad Especial", value=MASCOTAS[pet_name]["habilidad"], inline=False)
        embed.set_footer(text="Vuelve mañana para otra sesión")
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(PetsCog(bot))

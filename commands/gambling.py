# commands/gambling.py
import random
import discord
from discord.ext import commands
from discord import app_commands
from db import get_user, add_money, get_inventory

class GamblingCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ==================== MONEDA AL AIRE ====================
    @app_commands.command(name="moneda", description="🪙 Moneda al Aire - Apuesta simple 50/50")
    @app_commands.describe(cantidad="Cantidad a apostar")
    async def coin_flip(self, interaction: discord.Interaction, cantidad: int):
        """Moneda al aire - 50% chance de duplicar dinero"""
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La apuesta debe ser mayor a 0.")
            return
        
        user = await get_user(interaction.user.id)
        if not user or user["dinero"] < cantidad:
            await interaction.followup.send("❌ No tienes suficiente dinero.")
            return
        
        # Cobrar apuesta
        await add_money(interaction.user.id, -cantidad)
        
        # Tirada
        result = random.choice([True, False])
        inv = await get_inventory(interaction.user.id)
        items_low = [i["item"].lower() for i in inv]
        mecha_x2 = any(it == "x2 de dinero de mecha" for it in items_low)
        
        if result:
            # Ganó - duplica dinero
            payout = cantidad * 2
            if mecha_x2:
                payout *= 2
            await add_money(interaction.user.id, payout)
            
            embed = discord.Embed(
                title="🪙 Moneda al Aire",
                description="¡**CARA!** 🎉 ¡Ganaste el doble!",
                color=discord.Color.green()
            )
            embed.add_field(name="💚 Recuperación Mental", value=f"```+{payout}💰```", inline=False)
            embed.set_footer(text="La confianza en tu intuición se fortalece..." + (" (Items aplicados)" if mecha_x2 else ""))
        else:
            # Perdió
            embed = discord.Embed(
                title="🪙 Moneda al Aire",
                description="¡**SELLO!** 😢 La suerte no está de tu lado...",
                color=discord.Color.red()
            )
            embed.add_field(name="❌ Pérdida Terapéutica", value=f"```-{cantidad}💰```", inline=False)
            embed.set_footer(text="A veces la vida nos enseña a través de pequeñas derrotas...")
        
        await interaction.followup.send(embed=embed)

    # ==================== RULETA ====================
    @app_commands.command(name="ruleta", description="🎡 Ruleta del Sanatorio - Elige un número del 1-36")
    @app_commands.describe(numero="Número a elegir (1-36)", cantidad="Cantidad a apostar")
    async def roulette(self, interaction: discord.Interaction, numero: int, cantidad: int):
        """Ruleta - Si aciertas ganas 36x tu apuesta"""
        await interaction.response.defer()
        
        if numero < 1 or numero > 36:
            await interaction.followup.send("❌ Debes elegir un número entre 1 y 36.")
            return
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La apuesta debe ser mayor a 0.")
            return
        
        user = await get_user(interaction.user.id)
        if not user or user["dinero"] < cantidad:
            await interaction.followup.send("❌ No tienes suficiente dinero.")
            return
        
        # Cobrar apuesta
        await add_money(interaction.user.id, -cantidad)
        
        # Girar ruleta
        winning_number = random.randint(1, 36)
        inv = await get_inventory(interaction.user.id)
        items_low = [i["item"].lower() for i in inv]
        mecha_x2 = any(it == "x2 de dinero de mecha" for it in items_low)
        
        if numero == winning_number:
            # ¡GANÓ GRANDE!
            payout = cantidad * 36
            if mecha_x2:
                payout *= 2
            await add_money(interaction.user.id, payout)
            
            embed = discord.Embed(
                title="🎡 Ruleta del Sanatorio",
                description=f"🏆 **¡¡¡GANADOR!!!** El número correcto es **{winning_number}** 🏆",
                color=discord.Color.gold()
            )
            embed.add_field(name="💚 Epifanía Psicológica", value=f"```+{payout}💰```", inline=False)
            embed.add_field(name="📝 Análisis", value="Tu intuición ha alcanzado su máxima claridad. Has ganado una batalla interna significativa.", inline=False)
            embed.set_footer(text="¡Eres un verdadero maestro del azar!" + (" (Items aplicados)" if mecha_x2 else ""))
        else:
            # Perdió
            embed = discord.Embed(
                title="🎡 Ruleta del Sanatorio",
                description=f"❌ Elegiste **{numero}** pero salió **{winning_number}** 😔",
                color=discord.Color.red()
            )
            embed.add_field(name="❌ Pérdida Terapéutica", value=f"```-{cantidad}💰```", inline=False)
            embed.add_field(name="📝 Reflexión", value="En la vida, como en la ruleta, no siempre podemos controlar el resultado, pero sí nuestra respuesta ante él.", inline=False)
            embed.set_footer(text="El camino de la recuperación tiene altibajos...")
        
        await interaction.followup.send(embed=embed)

    # ==================== TRAGAMONEDAS ====================
    @app_commands.command(name="tragamonedas", description="🎰 Tragamonedas del Sanatorio - Apuesta por símbolos")
    @app_commands.describe(cantidad="Cantidad a apostar")
    async def slots(self, interaction: discord.Interaction, cantidad: int):
        """Tragamonedas - Gira 3 símbolos, combina para ganar"""
        await interaction.response.defer()
        
        if cantidad <= 0:
            await interaction.followup.send("❌ La apuesta debe ser mayor a 0.")
            return
        
        user = await get_user(interaction.user.id)
        if not user or user["dinero"] < cantidad:
            await interaction.followup.send("❌ No tienes suficiente dinero.")
            return
        
        # Cobrar apuesta
        await add_money(interaction.user.id, -cantidad)
        
        # Símbolos con rareza
        symbols = {
            "⚪": 1,      # Común (1x)
            "🔵": 2,      # Raro (2x)
            "🟣": 3,      # Épico (5x)
            "🌟": 5,      # Legendario (10x)
            "💎": 10,     # Maestro (50x)
        }
        
        symbol_names = list(symbols.keys())
        
        # Girar
        spin = [random.choice(symbol_names) for _ in range(3)]
        
        # Calcular payout
        inv = await get_inventory(interaction.user.id)
        items_low = [i["item"].lower() for i in inv]
        mecha_x2 = any(it == "x2 de dinero de mecha" for it in items_low)
        
        # Comprobar coincidencias
        if spin[0] == spin[1] == spin[2]:
            # ¡JACKPOT! Todos 3 iguales
            multiplier = symbols[spin[0]]
            payout = cantidad * multiplier * 20  # Bonificador por 3 iguales
            if mecha_x2:
                payout *= 2
            await add_money(interaction.user.id, payout)
            
            emoji_name = {
                "⚪": "Común",
                "🔵": "Raro",
                "🟣": "Épico",
                "🌟": "Legendario",
                "💎": "Maestro"
            }
            
            embed = discord.Embed(
                title="🎰 Tragamonedas del Sanatorio",
                description=f"🏆 **¡¡¡JACKPOT!!!** {' '.join(spin)} ¡Tres {emoji_name.get(spin[0], 'símbolos')}! 🏆",
                color=discord.Color.gold()
            )
            embed.add_field(name="💚 Recuperación Espectacular", value=f"```+{payout}💰```", inline=False)
            embed.add_field(name="🎊 Celebración", value="Has alcanzado un estado de claridad mental excepcional. ¡Tu sanidad mental está en su pico máximo!", inline=False)
            embed.set_footer(text="¡El universo te sonríe hoy!" + (" (Items aplicados)" if mecha_x2 else ""))
        elif spin[0] == spin[1] or spin[1] == spin[2] or spin[0] == spin[2]:
            # 2 iguales - buscar el par
            pair_symbol = None
            for i in range(3):
                for j in range(i+1, 3):
                    if spin[i] == spin[j]:
                        pair_symbol = spin[i]
                        break
            
            if pair_symbol:
                multiplier = symbols[pair_symbol]
                payout = cantidad * multiplier * 5  # Bonificador por 2 iguales
                if mecha_x2:
                    payout *= 2
                await add_money(interaction.user.id, payout)
                
                embed = discord.Embed(
                    title="🎰 Tragamonedas del Sanatorio",
                    description=f"✨ Dos símbolos iguales: {' '.join(spin)}",
                    color=discord.Color.green()
                )
                embed.add_field(name="💚 Mejora Moderada", value=f"```+{payout}💰```", inline=False)
                embed.add_field(name="📝 Reflexión", value="Pequeñas victorias son el camino hacia grandes transformaciones.", inline=False)
                embed.set_footer(text="¡Buen resultado!" + (" (Items aplicados)" if mecha_x2 else ""))
            else:
                # No hay coincidencia
                embed = discord.Embed(
                    title="🎰 Tragamonedas del Sanatorio",
                    description=f"❌ Sin coincidencia: {' '.join(spin)}",
                    color=discord.Color.red()
                )
                embed.add_field(name="❌ Sin Suerte", value=f"```-{cantidad}💰```", inline=False)
                embed.add_field(name="📝 Lección", value="No todas las apuestas resultan favorables. La verdadera fuerza está en levantarse después de cada caída.", inline=False)
                embed.set_footer(text="Sigue intentando...")
        else:
            # Sin coincidencia
            embed = discord.Embed(
                title="🎰 Tragamonedas del Sanatorio",
                description=f"❌ Sin coincidencia: {' '.join(spin)}",
                color=discord.Color.red()
            )
            embed.add_field(name="❌ Sin Suerte", value=f"```-{cantidad}💰```", inline=False)
            embed.add_field(name="📝 Lección", value="No todas las apuestas resultan favorables. La verdadera fuerza está en levantarse después de cada caída.", inline=False)
            embed.set_footer(text="Sigue intentando...")
        
        await interaction.followup.send(embed=embed)

# ==================== SETUP ====================
async def setup(bot):
    await bot.add_cog(GamblingCog(bot))

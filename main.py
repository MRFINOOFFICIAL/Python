# main.py
import os
import logging
import asyncio
import discord
from discord.ext import commands
from db import init_db
from keep_alive import keep_alive

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")

print("🏥 >>> SANATORIO PSIQUIÁTRICO - Bot iniciando...")
keep_alive()

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

# para evitar sincronizar múltiples veces
_tree_synced = False

@bot.event
async def on_ready():
    global _tree_synced
    if bot.user:
        print(f"🏥 Sanatorio listo: {bot.user} (ID: {bot.user.id})")
    await init_db()
    if not _tree_synced:
        try:
            synced = await bot.tree.sync()
            print(f"✅ Sesiones terapéuticas sincronizadas: {len(synced)}")
            for cmd in synced:
                print(f"  ✓ {cmd.name}")
        except Exception as e:
            print("❌ Error al sincronizar sesiones:", e)
        _tree_synced = True

@bot.event
async def on_app_command_error(interaction: discord.Interaction, error: Exception):
    """Manejar errores de comandos slash"""
    if isinstance(error, discord.app_commands.CommandNotFound):
        await interaction.response.send_message("🧠 Esa sesión terapéutica no existe en el sanatorio.", ephemeral=True)
    elif "deprecated" in str(error).lower() or "obsoleto" in str(error).lower():
        print(f"⚠️ Protocolo terapéutico obsoleto: {interaction.command.name if interaction.command else 'unknown'}")
        print("⚠️ Resincronizando sesiones terapéuticas...")
        try:
            synced = await bot.tree.sync()
            print(f"✅ Protocolos resincronizados: {len(synced)}")
            await interaction.response.send_message("✅ Protocolos actualizados. Intenta la sesión de nuevo.", ephemeral=True)
        except Exception as e:
            print(f"Error al resincronizar: {e}")
            await interaction.response.send_message("⚠️ Error al actualizar protocolos. Intenta más tarde.", ephemeral=True)
    else:
        await interaction.response.send_message(f"🏥 Error en sesión terapéutica: {error}", ephemeral=True)

@bot.event
async def on_guild_join(guild):
    """Sincronizar comandos cuando el bot se une a un nuevo servidor"""
    try:
        synced = await bot.tree.sync(guild=guild)
        print(f"Comandos sincronizados en servidor {guild.name}: {len(synced)}")
    except Exception as e:
        print(f"Error sincronizando en {guild.name}: {e}")

@bot.event
async def on_message(message):
    """Detectar cuando el bot es mencionado y enviar guía de inicio"""
    # Evitar que el bot responda a sí mismo
    if message.author.bot:
        return
    
    # Detectar si el bot fue mencionado
    if bot.user in message.mentions and not message.content.startswith(("!", "/")):
        embed = discord.Embed(
            title="🏥 BIENVENIDO AL SANATORIO PSIQUIÁTRICO",
            description="Guía completa para comenzar tu recuperación mental",
            color=discord.Color.from_rgb(74, 222, 128)
        )
        
        embed.add_field(
            name="📖 PASO 1: Crea tu Perfil",
            value="Usa `/profile` para ver tu perfil. Se crea automáticamente al usar cualquier comando.",
            inline=False
        )
        
        embed.add_field(
            name="💼 PASO 2: Busca un Trabajo",
            value="• `/jobs` — Ve todos los trabajos disponibles\n• `/apply <trabajo>` — Aplica a un trabajo\n• `/work` — Trabaja y gana dinero (cooldown: 2 min)",
            inline=False
        )
        
        embed.add_field(
            name="🌲 PASO 3: Explora y Recolecta",
            value="• `/explore` — Busca cofres y objetos (cooldown: 25s)\n• `/minar` — Extrae minerales con minijuego de 4 botones (cooldown: 30s)\n• `/pescar` — Atrapa peces haciendo clicks (cooldown: 40s)",
            inline=False
        )
        
        embed.add_field(
            name="🛍️ PASO 4: Compra en la Tienda",
            value="• `/shop` — Ver la farmacia clínica\n• `/buy <item>` — Compra medicinas, armas, huevos de mascotas\n• `/inventory` — Ver tu inventario",
            inline=False
        )
        
        embed.add_field(
            name="⚔️ PASO 5: Pelea contra Traumas",
            value="• `/spawnboss <nombre>` — Invoca un jefe (admin only)\n• `/fight` — Pelea contra el jefe activo (cooldown: 2 min)\n• `/bossinfo` — Info del jefe actual",
            inline=False
        )
        
        embed.add_field(
            name="🎮 PASO 6: Minijuegos y Más",
            value="• `/blackjack` — Juega blackjack\n• `/coinflip` — Apuesta en moneda al aire\n• `/ruleta` — Juega ruleta\n• `/slots` — Máquinas tragamonedas",
            inline=False
        )
        
        embed.add_field(
            name="👥 PASO 7: Características Sociales",
            value="• `/leaderboard [dinero|experiencia]` — Ranking\n• `/duel @user <dinero>` — Duelo PvP\n• `/sell-item <id> <precio>` — Mercado\n• `/club <acción>` — Crear/unirse a clubs",
            inline=False
        )
        
        embed.add_field(
            name="🏅 PROGRESIÓN DE RANGO",
            value="**Novato** → **Enfermo Básico** → **Enfermo Avanzado** → **Enfermo Supremo**\n\nGana dinero y experiencia para ascender.",
            inline=False
        )
        
        embed.add_field(
            name="📚 COMANDOS ÚTILES",
            value="• `/help` — Ayuda detallada (7 secciones)\n• `/profile` — Tu perfil\n• `/pet` — Tu mascota activa\n• `/missions` — Misiones diarias\n• `/equip <weapon>` — Equipar arma\n• `/pet-interaction` — Interactúa con mascota para recompensas",
            inline=False
        )
        
        embed.add_field(
            name="💡 CONSEJOS",
            value="✅ Trabaja regularmente para ganar dinero\n✅ Explora para encontrar items raros\n✅ Compra huevos de mascotas para bonificadores\n✅ Pelea jefes para grandes recompensas\n✅ Participa en duelos y missions",
            inline=False
        )
        
        embed.set_footer(text="🏥 Tu salud mental es nuestra prioridad — Usa /ayuda para más detalles")
        
        try:
            await message.reply(embed=embed)
        except Exception as e:
            print(f"Error al enviar guía: {e}")
    
    # Permitir que otros comandos se procesen normalmente
    await bot.process_commands(message)

# manejo básico de errores de comando
@bot.event
async def on_command_error(ctx, error):
    if isinstance(error, commands.CommandNotFound):
        try:
            await ctx.send("🧠 Esa sesión terapéutica no existe en el sanatorio.")
        except Exception:
            pass
    elif isinstance(error, commands.CommandOnCooldown):
        try:
            await ctx.send(f"⏳ La sesión está en proceso. Espera {round(error.retry_after,1)}s.")
        except Exception:
            pass
    else:
        try:
            await ctx.send(f"🏥 Error en sesión terapéutica: {error}")
        except Exception:
            pass
        logger.exception("Error en sesión:")

async def main():
    async with bot:
        # Carga todos los cogs (extensiones) que tienes
        # Añade más líneas si agregas otros archivos en commands/
        await bot.load_extension("commands.explore")
        await bot.load_extension("commands.profile")
        await bot.load_extension("commands.work")
        await bot.load_extension("commands.shop")
        await bot.load_extension("commands.jobs")
        await bot.load_extension("commands.rob")
        await bot.load_extension("commands.helpme")
        await bot.load_extension("commands.admin_tools")
        await bot.load_extension("commands.blackjack")
        await bot.load_extension("commands.gambling")
        await bot.load_extension("commands.bosses")
        await bot.load_extension("commands.items")
        await bot.load_extension("commands.leaderboard")
        await bot.load_extension("commands.missions")
        await bot.load_extension("commands.trading")
        await bot.load_extension("commands.market")
        await bot.load_extension("commands.duels")
        await bot.load_extension("commands.clubs")
        await bot.load_extension("commands.pets")
        await bot.load_extension("commands.mining")
        await bot.load_extension("commands.fishing")
        await bot.load_extension("commands.forging")
        
        # Iniciar tarea de auto-spawn de bosses
        from boss_autospawn import auto_spawn_bosses
        bot.loop.create_task(auto_spawn_bosses(bot))



        # keep_alive no es un cog, es un servidor web - opcional
        try:
            import keep_alive
            keep_alive.keep_alive()
            print("keep_alive iniciado.")
        except Exception:
            pass

        TOKEN = os.environ.get("DISCORD_TOKEN")
        if not TOKEN:
            print("❌ ERROR: No hay DISCORD_TOKEN en variables de entorno.")
            return
        print("🏥 Conectando al sanatorio psiquiátrico...")
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

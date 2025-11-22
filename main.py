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

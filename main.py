# main.py
import os
import logging
import asyncio
import discord
from discord.ext import commands
from db import init_db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("discord")

print(">>> Bot iniciando...")

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# para evitar sincronizar múltiples veces
_tree_synced = False

@bot.event
async def on_ready():
    global _tree_synced
    if bot.user:
        print(f"Bot listo: {bot.user} (ID: {bot.user.id})")
    await init_db()
    from db import create_boss_tables
    await create_boss_tables()
    if not _tree_synced:
        try:
            synced = await bot.tree.sync()
            print(f"Slash commands sincronizados: {len(synced)}")
            for cmd in synced:
                print(f"  ✓ {cmd.name}")
        except Exception as e:
            print("Error al sincronizar slash commands:", e)
        _tree_synced = True

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
            await ctx.send("❌ Comando no encontrado.")
        except Exception:
            pass
    elif isinstance(error, commands.CommandOnCooldown):
        try:
            await ctx.send(f"⏳ Comando en cooldown. Espera {round(error.retry_after,1)}s.")
        except Exception:
            pass
    else:
        try:
            await ctx.send(f"❌ Ocurrió un error: {error}")
        except Exception:
            pass
        logger.exception("Error en comando:")

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



        # keep_alive no es un cog, es un servidor web - opcional
        try:
            import keep_alive
            keep_alive.keep_alive()
            print("keep_alive iniciado.")
        except Exception:
            pass

        TOKEN = os.environ.get("DISCORD_TOKEN")
        if not TOKEN:
            print("ERROR: No hay DISCORD_TOKEN en variables de entorno.")
            return
        await bot.start(TOKEN)

if __name__ == "__main__":
    asyncio.run(main())

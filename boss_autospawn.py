"""
Sistema automático de spawn de bosses.
- Mini-bosses: cada 30 minutos (reemplaza al boss actual)
- Bosses: cada 1 día (reemplaza al boss actual)
- Especiales: cada semana (solo por comando del owner)
"""
import asyncio
from datetime import datetime, timedelta
from db import get_all_active_bosses, create_boss, deactivate_boss, get_event_channels, set_boss_spawn_time, get_boss_spawn_time
from bosses import get_random_boss
import discord

async def auto_spawn_bosses(bot):
    """Tarea que checkea cada 5 minutos si debe spawnear un boss"""
    await bot.wait_until_ready()
    
    while not bot.is_closed():
        try:
            current_time = datetime.now()
            
            # Iterar sobre todos los servidores donde el bot está
            for guild in bot.guilds:
                guild_id = guild.id
                
                # Verificar mini-boss (cada 30 minutos)
                last_mini = await get_boss_spawn_time(guild_id, "mini_boss")
                if last_mini is None or (current_time - last_mini).total_seconds() >= 1800:
                    mini_boss = get_random_boss("Mini-Boss")
                    if mini_boss:
                        # Desactivar boss actual si existe
                        active_bosses = await get_all_active_bosses(guild_id)
                        if active_bosses:
                            for active_boss in active_bosses:
                                await deactivate_boss(guild_id, active_boss.get("boss_name"))
                        
                        max_hp = mini_boss.get("max_hp", mini_boss.get("hp", 50))
                        await create_boss(guild_id, mini_boss["name"], max_hp)
                        await set_boss_spawn_time(guild_id, "mini_boss")
                        
                        # Notificar en el canal configurado
                        channels = await get_event_channels(guild_id)
                        for ch_id in channels:
                            try:
                                channel = bot.get_channel(ch_id)
                                if channel:
                                    embed = discord.Embed(
                                        title=f"🚨 ¡¡NUEVO Mini-Boss apareció!!",
                                        description=f"**{mini_boss['name']}** ha reemplazado al anterior.\nUsa `/fight` para pelear.",
                                        color=discord.Color.orange()
                                    )
                                    embed.add_field(name="HP", value=f"{mini_boss['hp']} HP", inline=True)
                                    embed.add_field(name="Tipo", value="Mini-Boss", inline=True)
                                    await channel.send(embed=embed)
                            except:
                                pass
                    continue
                
                # Verificar boss normal (cada 1 día)
                last_boss = await get_boss_spawn_time(guild_id, "boss")
                if last_boss is None or (current_time - last_boss).total_seconds() >= 86400:
                    boss = get_random_boss("Boss")
                    if boss:
                        # Desactivar boss actual si existe
                        active_bosses = await get_all_active_bosses(guild_id)
                        if active_bosses:
                            for active_boss in active_bosses:
                                await deactivate_boss(guild_id, active_boss.get("boss_name"))
                        
                        max_hp = boss.get("max_hp", boss.get("hp", 100))
                        await create_boss(guild_id, boss["name"], max_hp)
                        await set_boss_spawn_time(guild_id, "boss")
                        
                        # Notificar en el canal configurado
                        channels = await get_event_channels(guild_id)
                        for ch_id in channels:
                            try:
                                channel = bot.get_channel(ch_id)
                                if channel:
                                    embed = discord.Embed(
                                        title=f"🚨 ¡¡NUEVO Boss ha aparecido!!",
                                        description=f"**{boss['name']}** ha reemplazado al anterior.\nUsa `/fight` para pelear.",
                                        color=discord.Color.red()
                                    )
                                    embed.add_field(name="HP", value=f"{boss['hp']} HP", inline=True)
                                    embed.add_field(name="Tipo", value="Boss Normal", inline=True)
                                    await channel.send(embed=embed)
                            except:
                                pass
        
        except Exception as e:
            print(f"Error en auto_spawn_bosses: {e}")
        
        # Checkear cada 5 minutos
        await asyncio.sleep(300)

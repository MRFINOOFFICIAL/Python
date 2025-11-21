# commands/bosses.py
import discord
from discord.ext import commands
from discord import app_commands
from datetime import datetime, timedelta
import random
from db import (
    get_active_boss, set_active_boss, remove_active_boss, update_boss_hp,
    add_event_channel, remove_event_channel, get_event_channels,
    set_equipped_item, get_equipped_item, set_fight_cooldown, get_fight_cooldown,
    add_money, get_user, add_item_to_user, create_boss_tables
)
from bosses import (
    get_random_boss, resolve_player_attack, resolve_boss_attack, get_boss_reward,
    get_boss_by_name, get_all_boss_names, get_available_bosses_by_type
)

class BossesCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.spawn_tasks = {}

    async def _fight_internal(self, user_id, guild_id, send_fn):
        """Internal fight logic shared by prefix and slash commands"""
        boss = await get_active_boss(guild_id)
        if not boss:
            return await send_fn("❌ No hay jefe activo en este servidor.")
        
        cooldown = await get_fight_cooldown(user_id, guild_id)
        if cooldown and datetime.fromisoformat(cooldown.isoformat()) > datetime.now() - timedelta(minutes=2):
            return await send_fn("⏳ Debes esperar 2 minutos entre peleas.")
        
        equipped = await get_equipped_item(user_id)
        weapon = equipped["item_name"] if equipped else None
        
        embed = discord.Embed(title=f"⚔️ Pelea: {boss['name']}", color=discord.Color.red())
        embed.add_field(name="Tu HP", value="100 HP", inline=False)
        embed.add_field(name=f"HP del Jefe", value=f"{boss['hp']} / {boss['max_hp']} HP", inline=False)
        
        player_hp = 100
        boss_hp = boss["hp"]
        turn = 1
        fight_log = []
        
        while player_hp > 0 and boss_hp > 0 and turn <= 30:
            player_hit, player_dmg, player_crit = resolve_player_attack(weapon)
            boss_hit, boss_dmg, boss_crit = resolve_boss_attack(boss)
            
            if player_hit:
                boss_hp -= player_dmg
                crit_text = " (¡CRÍTICO!)" if player_crit else ""
                fight_log.append(f"**Turno {turn}:** Golpeaste por {player_dmg} daño{crit_text}. Boss HP: {max(0, boss_hp)}")
            else:
                fight_log.append(f"**Turno {turn}:** ¡Fallaste!")
            
            if boss_hp <= 0:
                break
            
            if boss_hit:
                player_hp -= boss_dmg
                crit_text = " (¡CRÍTICO!)" if boss_crit else ""
                fight_log.append(f"El jefe golpeó por {boss_dmg}{crit_text}. Tu HP: {max(0, player_hp)}")
            else:
                fight_log.append(f"¡El jefe falló!")
            
            turn += 1
        
        await update_boss_hp(guild_id, max(0, boss_hp))
        await set_fight_cooldown(user_id, guild_id)
        
        log_text = "\n".join(fight_log[-10:])
        
        if boss_hp <= 0:
            reward = await get_boss_reward(boss)
            await add_money(user_id, reward["dinero"])
            
            embed.title = "✅ ¡Victoria!"
            embed.color = discord.Color.green()
            embed.add_field(name="Resultado", value=f"Derrotaste a {boss['name']}", inline=False)
            embed.add_field(name="Recompensas", value=f"💰 {reward['dinero']} dinero", inline=False)
            if reward["item"]:
                await add_item_to_user(user_id, reward["item"], rareza=boss["rareza"], usos=1, durabilidad=100, categoria="arma", poder=15)
                embed.add_field(name="Item", value=f"📦 {reward['item']}", inline=False)
            
            await remove_active_boss(guild_id)
            channels = await get_event_channels(guild_id)
            for ch_id in channels:
                try:
                    ch = self.bot.get_channel(ch_id)
                    if ch:
                        user = await get_user(user_id)
                        mention = f"<@{user_id}>"
                        await ch.send(f"🏆 {mention} derrotó a **{boss['name']}**!")
                except:
                    pass
        else:
            embed.title = "❌ Derrota"
            embed.color = discord.Color.greyple()
            embed.add_field(name="Resultado", value=f"{boss['name']} te derrotó", inline=False)
            lost_money = random.randint(10, 50)
            user = await get_user(user_id)
            new_balance = max(0, user["dinero"] - lost_money)
            embed.add_field(name="Castigo", value=f"Perdiste 💰 {lost_money}", inline=False)
            embed.add_field(name="Balance", value=f"💰 {new_balance}", inline=False)
        
        embed.add_field(name="Registro de Combate", value=log_text or "Sin registros", inline=False)
        await send_fn(embed=embed)

    @commands.command(name="fight")
    async def fight_prefix(self, ctx):
        """!fight - Pelea contra el jefe activo"""
        async def send_fn(*args, **kwargs):
            await ctx.send(*args, **kwargs)
        await self._fight_internal(ctx.author.id, ctx.guild.id, send_fn)

    @app_commands.command(name="fight", description="Pelea contra el jefe activo")
    async def fight_slash(self, interaction: discord.Interaction):
        """Fight the active boss"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            await interaction.followup.send(*args, **kwargs)
        await self._fight_internal(interaction.user.id, interaction.guild_id, send_fn)

    @commands.command(name="bossinfo")
    async def bossinfo_prefix(self, ctx):
        """!bossinfo - Ver información del jefe activo"""
        guild_id = ctx.guild.id
        boss = await get_active_boss(guild_id)
        
        if not boss:
            return await ctx.send("❌ No hay jefe activo.")
        
        embed = discord.Embed(title=f"📊 {boss['name']}", color=discord.Color.yellow())
        embed.add_field(name="Tipo", value=boss["type"], inline=True)
        embed.add_field(name="HP", value=f"{boss['hp']} / {boss['max_hp']}", inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Usa !fight o /fight para atacar", value="⚔️", inline=False)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="bossinfo", description="Ver información del jefe activo")
    async def bossinfo_slash(self, interaction: discord.Interaction):
        """Get info about the active boss"""
        guild_id = interaction.guild_id
        boss = await get_active_boss(guild_id)
        
        if not boss:
            return await interaction.response.send_message("❌ No hay jefe activo.", ephemeral=True)
        
        embed = discord.Embed(title=f"📊 {boss['name']}", color=discord.Color.yellow())
        embed.add_field(name="Tipo", value=boss["type"], inline=True)
        embed.add_field(name="HP", value=f"{boss['hp']} / {boss['max_hp']}", inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Usa !fight o /fight para atacar", value="⚔️", inline=False)
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @commands.command(name="equip")
    async def equip_prefix(self, ctx, *, item_name: str):
        """!equip <item> - Equipar un arma"""
        user_id = ctx.author.id
        
        await set_equipped_item(user_id, 0, item_name)
        
        embed = discord.Embed(title="✅ Item Equipado", color=discord.Color.blue())
        embed.add_field(name="Arma", value=item_name, inline=False)
        embed.add_field(name="Beneficio", value="Mejora tu probabilidad de golpe, daño y crítico", inline=False)
        
        await ctx.send(embed=embed)

    @app_commands.command(name="equip", description="Equipar un arma")
    @app_commands.describe(item_name="Nombre del item a equipar")
    async def equip_slash(self, interaction: discord.Interaction, item_name: str):
        """Equip a weapon"""
        await interaction.response.defer()
        user_id = interaction.user.id
        
        await set_equipped_item(user_id, 0, item_name)
        
        embed = discord.Embed(title="✅ Item Equipado", color=discord.Color.blue())
        embed.add_field(name="Arma", value=item_name, inline=False)
        embed.add_field(name="Beneficio", value="Mejora tu probabilidad de golpe, daño y crítico", inline=False)
        
        await interaction.followup.send(embed=embed)

    @commands.command(name="event")
    @commands.has_guild_permissions(administrator=True)
    async def event_prefix(self, ctx, action: str, channel: discord.TextChannel = None):
        """!event enable/disable #channel - Habilitar/deshabilitar canal de eventos"""
        guild_id = ctx.guild.id
        
        if action.lower() == "enable":
            if not channel:
                return await ctx.send("❌ Debes especificar un canal: `!event enable #canal`")
            await add_event_channel(guild_id, channel.id)
            embed = discord.Embed(title="✅ Canal Habilitado", color=discord.Color.green())
            embed.add_field(name="Canal", value=channel.mention, inline=False)
        elif action.lower() == "disable":
            if not channel:
                return await ctx.send("❌ Debes especificar un canal: `!event disable #canal`")
            await remove_event_channel(guild_id, channel.id)
            embed = discord.Embed(title="✅ Canal Deshabilitado", color=discord.Color.orange())
            embed.add_field(name="Canal", value=channel.mention, inline=False)
        else:
            return await ctx.send("❌ Usa `!event enable #canal` o `!event disable #canal`")
        
        await ctx.send(embed=embed)

    @app_commands.command(name="event", description="Habilitar/deshabilitar canal de eventos")
    @app_commands.describe(action="enable o disable", channel="Canal para eventos")
    async def event_slash(self, interaction: discord.Interaction, action: str, channel: discord.TextChannel = None):
        """Enable/disable event channel"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins", ephemeral=True)
        
        guild_id = interaction.guild_id
        
        if action.lower() == "enable":
            if not channel:
                return await interaction.response.send_message("❌ Debes especificar un canal", ephemeral=True)
            await add_event_channel(guild_id, channel.id)
            embed = discord.Embed(title="✅ Canal Habilitado", color=discord.Color.green())
            embed.add_field(name="Canal", value=channel.mention, inline=False)
        elif action.lower() == "disable":
            if not channel:
                return await interaction.response.send_message("❌ Debes especificar un canal", ephemeral=True)
            await remove_event_channel(guild_id, channel.id)
            embed = discord.Embed(title="✅ Canal Deshabilitado", color=discord.Color.orange())
            embed.add_field(name="Canal", value=channel.mention, inline=False)
        else:
            return await interaction.response.send_message("❌ Usa 'enable' o 'disable'", ephemeral=True)
        
        await interaction.response.send_message(embed=embed)

    @commands.command(name="spawnboss")
    @commands.has_guild_permissions(administrator=True)
    async def spawnboss_prefix(self, ctx, boss_type: str):
        """!spawnboss Mini-Boss/Boss - Forzar spawn de jefe (Admin)"""
        guild_id = ctx.guild.id
        
        if boss_type not in ["Mini-Boss", "Boss"]:
            return await ctx.send("❌ Tipo debe ser 'Mini-Boss' o 'Boss'")
        
        boss = get_random_boss(boss_type)
        if not boss:
            return await ctx.send("❌ Error al generar jefe")
        
        await set_active_boss(guild_id, boss)
        
        channels = await get_event_channels(guild_id)
        embed = discord.Embed(title="🚨 ¡JEFE APARECE!", color=discord.Color.red())
        embed.add_field(name="Nombre", value=boss["name"], inline=True)
        embed.add_field(name="Tipo", value=boss_type, inline=True)
        embed.add_field(name="HP", value=boss["hp"], inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Rareza", value=boss["rareza"], inline=True)
        embed.add_field(name="Usa !fight o /fight para pelear", value="⚔️", inline=False)
        
        for ch_id in channels:
            try:
                ch = self.bot.get_channel(ch_id)
                if ch:
                    await ch.send(embed=embed)
            except:
                pass
        
        await ctx.send("✅ Jefe spawneado")

    async def boss_autocomplete(self, interaction: discord.Interaction, current: str) -> list:
        """Autocomplete for boss names"""
        all_bosses = get_all_boss_names()
        return [name for name in all_bosses if current.lower() in name.lower()][:25]

    @app_commands.command(name="spawnboss", description="Forzar spawn de jefe (Admin)")
    @app_commands.describe(boss_type="Mini-Boss, Boss o nombre específico", boss_name="Nombre específico del jefe (opcional)")
    @app_commands.autocomplete(boss_name=boss_autocomplete)
    async def spawnboss_slash(self, interaction: discord.Interaction, boss_type: str, boss_name: str = None):
        """Force spawn a boss"""
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins", ephemeral=True)
        
        guild_id = interaction.guild_id
        boss = None
        
        if boss_name:
            boss = get_boss_by_name(boss_name)
            if not boss:
                return await interaction.response.send_message(f"❌ Jefe '{boss_name}' no encontrado", ephemeral=True)
        elif boss_type in ["Mini-Boss", "Boss", "Especial"]:
            boss = get_random_boss(boss_type)
            if not boss:
                return await interaction.response.send_message(f"❌ Error al generar jefe de tipo {boss_type}", ephemeral=True)
        else:
            return await interaction.response.send_message("❌ Tipo debe ser 'Mini-Boss', 'Boss' o 'Especial', o especifica un nombre de jefe", ephemeral=True)
        
        await set_active_boss(guild_id, boss)
        
        channels = await get_event_channels(guild_id)
        embed = discord.Embed(title="🚨 ¡JEFE APARECE!", color=discord.Color.red())
        embed.add_field(name="Nombre", value=boss["name"], inline=True)
        embed.add_field(name="Rareza", value=boss["rareza"], inline=True)
        embed.add_field(name="HP", value=boss["hp"], inline=True)
        embed.add_field(name="Ataque", value=boss["ataque"], inline=True)
        embed.add_field(name="Dinero", value=f"{boss['rewards']['dinero'][0]}-{boss['rewards']['dinero'][1]}", inline=True)
        embed.add_field(name="Usa !fight o /fight para pelear", value="⚔️", inline=False)
        
        for ch_id in channels:
            try:
                ch = self.bot.get_channel(ch_id)
                if ch:
                    await ch.send(embed=embed)
            except:
                pass
        
        await interaction.response.send_message("✅ Jefe spawneado", ephemeral=True)

async def setup(bot):
    await bot.add_cog(BossesCog(bot))

import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from db import add_money, set_job, get_user, DB, set_allowed_channel, get_allowed_channel, set_allowed_channel, get_allowed_channel

class AdminCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ================================
    #        PREFIX COMMANDS
    # ================================

    @commands.command(name="addmoney")
    @commands.has_guild_permissions(administrator=True)
    async def addmoney_prefix(self, ctx, member: discord.Member, amount: int):
        """!addmoney @user 500"""
        try:
            await add_money(member.id, amount)
            user = await get_user(member.id)
            await ctx.send(f"✅ {member.mention} recibió `{amount}💰`. Balance: **{user['dinero']}💰**.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="setjob")
    @commands.has_guild_permissions(administrator=True)
    async def setjob_prefix(self, ctx, member: discord.Member, *, job_name: str):
        """!setjob @user Trabajo"""
        try:
            await set_job(member.id, job_name)
            await ctx.send(f"✅ Trabajo de {member.mention} cambiado a **{job_name}**.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="resetcooldown")
    @commands.has_guild_permissions(administrator=True)
    async def resetcooldown_prefix(self, ctx, member: discord.Member, *, job_name: str = None):
        """!resetcooldown @user [Trabajo]"""
        try:
            async with aiosqlite.connect(DB) as db:
                if job_name:
                    await db.execute(
                        "DELETE FROM work_cooldowns WHERE user_id = ? AND job_name = ?",
                        (str(member.id), job_name)
                    )
                else:
                    await db.execute(
                        "DELETE FROM work_cooldowns WHERE user_id = ?",
                        (str(member.id),)
                    )
                await db.commit()

            await ctx.send(
                f"✅ Cooldown reiniciado para {member.mention} "
                f"{f'del trabajo **{job_name}**' if job_name else 'de todos los trabajos'}."
            )
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    # ================================
    #        SLASH COMMANDS
    # ================================

    @app_commands.command(name="addmoney", description="Añadir dinero a un usuario (Admin)")
    @app_commands.describe(member="Usuario", amount="Cantidad a añadir")
    async def addmoney_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        await add_money(member.id, amount)
        user = await get_user(member.id)
        await interaction.response.send_message(
            f"💰 {member.mention} recibió `{amount}`. Nuevo balance: **{user['dinero']}💰**."
        )

    @app_commands.command(name="setjob", description="Cambiar el trabajo de un usuario (Admin)")
    @app_commands.describe(member="Usuario", job_name="Nuevo trabajo")
    async def setjob_slash(self, interaction: discord.Interaction, member: discord.Member, job_name: str):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        await set_job(member.id, job_name)
        await interaction.response.send_message(
            f"🛠️ Trabajo de {member.mention} cambiado a **{job_name}**."
        )

    @app_commands.command(name="resetcooldown", description="Resetear cooldowns de trabajo (Admin)")
    @app_commands.describe(member="Usuario", job_name="Trabajo específico (opcional)")
    async def resetcooldown_slash(self, interaction: discord.Interaction, member: discord.Member, job_name: str = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        async with aiosqlite.connect(DB) as db:
            if job_name:
                await db.execute(
                    "DELETE FROM work_cooldowns WHERE user_id = ? AND job_name = ?",
                    (str(member.id), job_name)
                )
            else:
                await db.execute(
                    "DELETE FROM work_cooldowns WHERE user_id = ?",
                    (str(member.id),)
                )
            await db.commit()

        await interaction.response.send_message(
            f"🔁 Cooldown reiniciado para {member.mention} "
            f"{f'del trabajo **{job_name}**' if job_name else 'de todos los trabajos'}."
        )

    @app_commands.command(name="setchannel", description="Establecer canal donde funciona el bot (Admin)")
    @app_commands.describe(channel="Canal permitido (dejar vacío para permitir todos)")
    async def setchannel_slash(self, interaction: discord.Interaction, channel: discord.TextChannel = None):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        guild_id = interaction.guild_id
        if channel:
            await set_allowed_channel(guild_id, channel.id)
            embed = discord.Embed(
                title="✅ Canal Configurado",
                description=f"El bot ahora solo funciona en {channel.mention}",
                color=discord.Color.green()
            )
            embed.add_field(name="Canal", value=f"{channel.name} (ID: {channel.id})")
        else:
            await set_allowed_channel(guild_id, None)
            embed = discord.Embed(
                title="✅ Restricción Eliminada",
                description="El bot ahora funciona en todos los canales",
                color=discord.Color.green()
            )
        
        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="getchannel", description="Ver canal configurado (Admin)")
    async def getchannel_slash(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        guild_id = interaction.guild_id
        channel_id = await get_allowed_channel(guild_id)
        
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            if channel:
                embed = discord.Embed(
                    title="📍 Canal Configurado",
                    description=f"El bot solo funciona en {channel.mention}",
                    color=discord.Color.blue()
                )
                embed.add_field(name="Canal", value=f"{channel.name}")
            else:
                embed = discord.Embed(
                    title="❌ Canal Inválido",
                    description=f"El canal ID {channel_id} no existe o fue eliminado",
                    color=discord.Color.red()
                )
        else:
            embed = discord.Embed(
                title="🌍 Sin Restricción",
                description="El bot funciona en todos los canales",
                color=discord.Color.blue()
            )
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

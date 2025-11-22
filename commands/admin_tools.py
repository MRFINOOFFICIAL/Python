import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from db import add_money, set_job, get_user, DB

async def set_event_channel(guild_id, channel_id):
    """Configurar canal para anuncios de bosses"""
    async with aiosqlite.connect(DB) as db:
        await db.execute(
            "INSERT OR REPLACE INTO event_channels (guild_id, channel_id) VALUES (?, ?)",
            (str(guild_id), str(channel_id))
        )
        await db.commit()

async def get_event_channel(guild_id):
    """Obtener canal configurado para anuncios"""
    async with aiosqlite.connect(DB) as db:
        cursor = await db.execute(
            "SELECT channel_id FROM event_channels WHERE guild_id = ?",
            (str(guild_id),)
        )
        row = await cursor.fetchone()
        return int(row[0]) if row else None

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
            await add_money(str(member.id), amount)
            user = await get_user(str(member.id))
            await ctx.send(f"✅ {member.mention} recibió `{amount}💰`. Balance: **{user['dinero']}💰**.")
        except Exception as e:
            await ctx.send(f"❌ Error: {e}")

    @commands.command(name="setjob")
    @commands.has_guild_permissions(administrator=True)
    async def setjob_prefix(self, ctx, member: discord.Member, *, job_name: str):
        """!setjob @user Trabajo"""
        try:
            await set_job(str(member.id), job_name)
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
    #         SLASH COMMANDS
    # ================================

    def _member_from_interaction(self, interaction):
        """Devuelve siempre un Member aunque interaction.user sea User."""
        if isinstance(interaction.user, discord.Member):
            return interaction.user
        return interaction.guild.get_member(interaction.user.id)

    @app_commands.command(name="addmoney", description="Añadir dinero a un usuario (Admin)")
    async def addmoney_slash(self, interaction: discord.Interaction, member: discord.Member, amount: int):
        user = self._member_from_interaction(interaction)
        if not user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        await add_money(str(member.id), amount)
        user_data = await get_user(str(member.id))

        await interaction.response.send_message(
            f"💰 {member.mention} recibió `{amount}`. Nuevo balance: **{user_data['dinero']}💰**."
        )

    @app_commands.command(name="setjob", description="Cambiar el trabajo de un usuario (Admin)")
    async def setjob_slash(self, interaction: discord.Interaction, member: discord.Member, job_name: str):
        user = self._member_from_interaction(interaction)
        if not user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)

        await set_job(str(member.id), job_name)
        await interaction.response.send_message(
            f"🛠️ Trabajo de {member.mention} cambiado a **{job_name}**."
        )

    @app_commands.command(name="resetcooldown", description="Resetear cooldowns de trabajo (Admin)")
    async def resetcooldown_slash(self, interaction: discord.Interaction, member: discord.Member, job_name: str = None):
        user = self._member_from_interaction(interaction)
        if not user.guild_permissions.administrator:
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

    @commands.command(name="setchannel")
    @commands.has_guild_permissions(administrator=True)
    async def setchannel_prefix(self, ctx, channel: discord.TextChannel):
        """!setchannel #canal — Configurar canal para anuncios de bosses"""
        await set_event_channel(ctx.guild.id, channel.id)
        await ctx.send(f"✅ Canal de anuncios configurado a {channel.mention}")

    @app_commands.command(name="setchannel", description="Configurar canal para anuncios de bosses")
    async def setchannel_slash(self, interaction: discord.Interaction, canal: discord.TextChannel):
        user = self._member_from_interaction(interaction)
        if not user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        
        await set_event_channel(interaction.guild_id, canal.id)
        await interaction.response.send_message(f"✅ Canal de anuncios configurado a {canal.mention}")

    @commands.command(name="getchannel")
    @commands.has_guild_permissions(administrator=True)
    async def getchannel_prefix(self, ctx):
        """!getchannel — Ver canal configurado para anuncios"""
        channel_id = await get_event_channel(ctx.guild.id)
        if channel_id:
            channel = ctx.guild.get_channel(channel_id)
            await ctx.send(f"📢 Canal configurado: {channel.mention if channel else f'<#{channel_id}>'}")
        else:
            await ctx.send("❌ No hay canal configurado. Usa `/setchannel #canal`")

    @app_commands.command(name="getchannel", description="Ver canal configurado para anuncios")
    async def getchannel_slash(self, interaction: discord.Interaction):
        user = self._member_from_interaction(interaction)
        if not user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ Solo admins.", ephemeral=True)
        
        channel_id = await get_event_channel(interaction.guild_id)
        if channel_id:
            channel = interaction.guild.get_channel(channel_id)
            await interaction.response.send_message(f"📢 Canal configurado: {channel.mention if channel else f'<#{channel_id}>'}")
        else:
            await interaction.response.send_message("❌ No hay canal configurado. Usa `/setchannel #canal`")


async def setup(bot):
    await bot.add_cog(AdminCog(bot))

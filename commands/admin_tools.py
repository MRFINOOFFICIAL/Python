import discord
from discord.ext import commands
from discord import app_commands
import aiosqlite
from db import add_money, set_job, get_user, DB

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

async def setup(bot):
    await bot.add_cog(AdminCog(bot))

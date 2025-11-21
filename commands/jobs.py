# commands/jobs.py
import discord
from discord.ext import commands
from discord import app_commands
from db import get_user, set_job
from jobs import JOBS

class JobsCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="jobs")
    async def jobs_prefix(self, ctx):
        await self._send_jobs(ctx, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="jobs", description="Ver trabajos disponibles para tu rango")
    async def jobs_slash(self, interaction: discord.Interaction):
        await interaction.response.defer()
        await self._send_jobs(interaction, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _send_jobs(self, ctx_or_interaction, send_fn):
        if hasattr(ctx_or_interaction, "author"):
            user_id = ctx_or_interaction.author.id
        else:
            user_id = ctx_or_interaction.user.id

        user = await get_user(user_id)
        rango = user.get("rango", "Novato")
        trabajos = JOBS.get(rango, [])

        embed = discord.Embed(
            title=f"Trabajos disponibles — Rango {rango}",
            color=discord.Color.dark_purple()
        )

        if not trabajos:
            embed.description = "No tienes trabajos disponibles todavía."
            await send_fn(embed=embed)
            return

        for t in trabajos:
            embed.add_field(
                name=f"{t['name']} — {t['salary']}💰",
                value=t.get("desc", "Sin descripción."),
                inline=False
            )

        await send_fn(embed=embed)

    @commands.command(name="apply")
    async def apply_prefix(self, ctx, *, trabajo_nombre: str):
        await self._apply(ctx.author.id, trabajo_nombre, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="apply", description="Aplica a un trabajo (uso: /apply trabajo)")
    @app_commands.describe(trabajo_nombre="Nombre exacto del trabajo")
    async def apply_slash(self, interaction: discord.Interaction, trabajo_nombre: str):
        await interaction.response.defer()
        await self._apply(interaction.user.id, trabajo_nombre, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _apply(self, user_id, trabajo_nombre, send_fn):
        user = await get_user(user_id)
        rango = user.get("rango", "Novato")
        trabajos = JOBS.get(rango, [])
        t = next((x for x in trabajos if x["name"].lower() == trabajo_nombre.lower()), None)
        if not t:
            await send_fn(content="❌ Ese trabajo no existe o no es parte de tu rango.")
            return
        await set_job(user_id, t["name"])
        await send_fn(content=f"✅ Ahora trabajas como **{t['name']}**.")

async def setup(bot):
    await bot.add_cog(JobsCog(bot))

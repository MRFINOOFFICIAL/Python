# commands/jobs.py
import discord
from discord.ext import commands
from discord import app_commands
from db import get_user, set_job
from commands.work import JOBS_BY_RANK


# ==================== AUTOCOMPLETE ====================

async def apply_jobs_autocomplete(interaction: discord.Interaction, current: str):
    """Autocomplete para mostrar trabajos disponibles según rango"""
    try:
        user = await get_user(interaction.user.id)
        rango = user.get("rango", "Novato")
        trabajos_dict = JOBS_BY_RANK.get(rango, {})
        
        if not trabajos_dict:
            return []
        
        job_names = list(trabajos_dict.keys())
        filtered = [name for name in job_names if current.lower() in name.lower()] if current else job_names
        
        return [app_commands.Choice(name=name, value=name) for name in filtered[:25]]
    except Exception:
        return []


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
        trabajos_dict = JOBS_BY_RANK.get(rango, {})

        embed = discord.Embed(
            title=f"🏥 Trabajos Disponibles — Rango {rango}",
            description="Usa `/apply <nombre_trabajo>` para aplicar a un trabajo",
            color=discord.Color.from_rgb(74, 222, 128)
        )

        if not trabajos_dict:
            embed.description = "❌ No tienes trabajos disponibles en tu rango actual."
            await send_fn(embed=embed)
            return

        # JOBS_BY_RANK es: JOBS_BY_RANK[rango] = {"NombreTrabajo": {"pay": 150, "games": [...]}, ...}
        for job_name, job_data in sorted(trabajos_dict.items(), key=lambda x: x[1].get("pay", 0)):
            pay = job_data.get("pay", 0)
            games = ", ".join(job_data.get("games", []))
            embed.add_field(
                name=f"💼 {job_name}",
                value=f"💰 **{pay}** recuperación mental\n🎮 Minijuegos: {games}",
                inline=False
            )

        await send_fn(embed=embed)

    @commands.command(name="apply")
    async def apply_prefix(self, ctx, *, trabajo_nombre: str):
        await self._apply(ctx.author.id, trabajo_nombre, send_fn=lambda **kw: ctx.send(**kw))

    @app_commands.command(name="apply", description="Aplica a un trabajo")
    @app_commands.autocomplete(trabajo_nombre=apply_jobs_autocomplete)
    async def apply_slash(self, interaction: discord.Interaction, trabajo_nombre: str):
        await interaction.response.defer()
        await self._apply(interaction.user.id, trabajo_nombre, send_fn=lambda **kw: interaction.followup.send(**kw))

    async def _apply(self, user_id, trabajo_nombre, send_fn):
        user = await get_user(user_id)
        rango = user.get("rango", "Novato")
        trabajos_dict = JOBS_BY_RANK.get(rango, {})
        
        # Buscar el trabajo (case-insensitive)
        job_name = next((name for name in trabajos_dict.keys() if name.lower() == trabajo_nombre.lower()), None)
        
        if not job_name:
            await send_fn(content=f"❌ Ese trabajo no existe o no es parte de tu rango ({rango}).\nUsa `/jobs` para ver tus trabajos disponibles.")
            return
        
        await set_job(user_id, job_name)
        await send_fn(content=f"✅ Ahora trabajas como **{job_name}** 🏥\n💰 Ganancia: {trabajos_dict[job_name]['pay']} recuperación mental")

async def setup(bot):
    await bot.add_cog(JobsCog(bot))

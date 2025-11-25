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
        rango = user.get("rango", "Novato") if user else "Novato"
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
        rango = user.get("rango", "Novato") if user else "Novato"

        embed = discord.Embed(
            title=f"🏥 Todos los Trabajos — Tu Rango: {rango}",
            description="Usa `/apply <nombre_trabajo>` para aplicar a un trabajo.\n✅ = Disponible para tu rango | 🔒 = Rango requerido",
            color=discord.Color.from_rgb(74, 222, 128)
        )

        # Mostrar TODOS los trabajos de todos los rangos
        for rank_name in ["Novato", "Enfermo Básico", "Enfermo Avanzado", "Enfermo Supremo"]:
            trabajos_dict = JOBS_BY_RANK.get(rank_name, {})
            if not trabajos_dict:
                continue
            
            # Ordenar por salario
            sorted_jobs = sorted(trabajos_dict.items(), key=lambda x: x[1].get("pay", 0))
            
            field_value = ""
            for job_name, job_data in sorted_jobs:
                pay = job_data.get("pay", 0)
                # Verificar si el usuario puede acceder a este rango
                is_available = rank_name == rango
                status_icon = "✅" if is_available else "🔒"
                field_value += f"{status_icon} **{job_name}** — 💰 {pay}\n"
            
            embed.add_field(
                name=f"🏆 Rango: {rank_name}",
                value=field_value.strip(),
                inline=False
            )

        embed.set_footer(text="🔒 Necesitas ascender de rango para desbloquear más trabajos")
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
        rango = user.get("rango", "Novato") if user else "Novato"
        
        # Buscar en TODOS los rangos primero
        found_job = None
        found_rank = None
        for rank_name, trabajos_dict in JOBS_BY_RANK.items():
            job_name = next((name for name in trabajos_dict.keys() if name.lower() == trabajo_nombre.lower()), None)
            if job_name:
                found_job = job_name
                found_rank = rank_name
                break
        
        if not found_job:
            await send_fn(content=f"❌ Ese trabajo no existe.\nUsa `/jobs` para ver todos los trabajos disponibles.")
            return
        
        # Verificar si el usuario tiene el rango requerido
        if found_rank != rango:
            await send_fn(content=f"🔒 **{found_job}** requiere rango **{found_rank}**, pero tu rango actual es **{rango}**.\n\n¡Sigue progresando para desbloquear este trabajo!")
            return
        
        # Aplicar al trabajo
        await set_job(user_id, found_job)
        await send_fn(content=f"✅ Ahora trabajas como **{found_job}** 🏥\n💰 Ganancia: {JOBS_BY_RANK[rango][found_job]['pay']} recuperación mental")

async def setup(bot):
    await bot.add_cog(JobsCog(bot))

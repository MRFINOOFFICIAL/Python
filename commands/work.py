# commands/work.py
import discord
from discord.ext import commands
from discord import app_commands
import random
import asyncio
from datetime import datetime, timedelta
from db import add_money, get_user, set_work_cooldown, get_work_cooldown, get_inventory, club_has_upgrade, add_experiencia, update_mission_progress, add_pet_xp, get_pet_bonus_multiplier
from cache import set_buff, get_buff
import time

# ---------------- Tabla de salarios y minijuegos ----------------
JOBS = {
    "Camillero": {"pay": 150, "games": ["dados", "pregunta"]},
    "Asistente del Psiquiatra": {"pay": 250, "games": ["dados", "pregunta"]},
    "Analista de Crisis": {"pay": 600, "games": ["pregunta", "dados"]},
    "Guardia Sedante": {"pay": 900, "games": ["dados", "pregunta"]},
    "Supervisor Psiquiátrico": {"pay": 1800, "games": ["dados", "pregunta"]},
    "Jefe de Terapia de Choque": {"pay": 3500, "games": ["dados", "pregunta"]},
    "Jefe del Distrito del Psicólogo": {"pay": 8000, "games": ["dados", "pregunta"]},
    "Director del Sanatorio": {"pay": 15000, "games": ["dados", "pregunta"]}
}

# ---------------- Preguntas ----------------
QUESTION_BANK = {
    "matematicas": {
        "easy": [
            {"p":"¿Cuánto es 2 + 2?","r":["4","cuatro"]},
            {"p":"¿Cuánto es 5 - 3?","r":["2","dos"]},
            {"p":"¿Cuánto es 3 × 3?","r":["9","nueve"]}
        ],
        "normal": [
            {"p":"¿Cuánto es 12 ÷ 3?","r":["4","cuatro"]},
            {"p":"Si x=5, ¿qué es x+7?","r":["12","doce"]},
            {"p":"Resuelve: 7+8","r":["15","quince"]}
        ],
        "hard": [
            {"p":"¿Cuánto es 13 × 7?","r":["91","noventa y uno","noventa y uno"]},
            {"p":"¿Cuál es la raíz cuadrada de 144?","r":["12","doce"]}
        ],
        "expert": [
            {"p":"Resuelve: 17 × 13","r":["221","doscientos veintiuno"]},
            {"p":"¿Cuánto es 2^6?","r":["64","sesenta y cuatro"]}
        ]
    },
    "cultura": {
        "easy":[
            {"p":"¿Capital de España?","r":["madrid"]},
            {"p":"¿Cuál es el idioma principal de Brasil?","r":["portugues","portugués"]}
        ],
        "normal":[
            {"p":"¿Capital de Italia?","r":["roma"]},
            {"p":"¿En qué continente está Egipto?","r":["asia","africa"]}
        ],
        "hard":[
            {"p":"¿En qué año terminó la Segunda Guerra Mundial?","r":["1945"]},
            {"p":"¿Autor de 'Cien años de soledad'?","r":["gabriel garcia marquez","garcia marquez","gabo","gabriel garcía márquez"]}
        ],
        "expert":[
            {"p":"¿Quién pintó 'La persistencia de la memoria'?","r":["salvador dali","dali"]},
            {"p":"¿En qué año fue la Revolución Francesa (inicio)?","r":["1789"]}
        ]
    },
    "ciencia": {
        "easy":[
            {"p":"¿El agua hierve a 100 en qué unidad?","r":["c","celsius","grados celsius"]},
            {"p":"¿Cuál es el gas que respiramos principalmente?","r":["oxigeno","oxígeno"]}
        ],
        "normal":[
            {"p":"¿Qué planeta es conocido como el 'Planeta Rojo'?","r":["marte"]},
            {"p":"¿Unidad básica de los seres vivos?","r":["celula","célula"]}
        ],
        "hard":[
            {"p":"¿Qué partícula tiene carga negativa dentro del átomo?","r":["electron","electrón"]},
            {"p":"¿Qué órgano produce la insulina?","r":["pancreas","páncreas"]}
        ],
        "expert":[
            {"p":"¿Qué ley relaciona fuerza, masa y aceleración?","r":["segunda ley de newton","f=ma","f = m a"]},
            {"p":"¿Qué molécula lleva la información genética?","r":["dna","adn","ácido desoxirribonucleico"]}
        ]
    },
    "videojuegos": {
        "easy":[
            {"p":"¿En Minecraft, cuál es el nombre del material obtenido al minar diamantes?","r":["diamante","diamantes"]},
            {"p":"¿En qué consola salió originalmente 'Super Mario'?","r":["nes","nintendo","nintendo entertainment system"]}
        ],
        "normal":[
            {"p":"¿Cómo se llama el creador de Minecraft?","r":["notch","markus persson","marcus persson"]},
            {"p":"¿Qué franquicia tiene un famoso personaje llamado 'Master Chief'?","r":["halo"]}
        ],
        "hard":[
            {"p":"¿En qué año se lanzó el primer 'The Legend of Zelda'?","r":["1986"]},
            {"p":"¿Cuál es el género principal de 'Dark Souls'?","r":["rpg","acción rpg","action rpg"]}
        ],
        "expert":[
            {"p":"¿Cuál es el motor gráfico de 'Doom (1993)'?","r":["doom engine"]},
            {"p":"¿Quién dirigió 'The Last of Us' juego original?","r":["neil druckmann","neil"]}
        ]
    },
    "sanatorio": {
        "easy":[
            {"p":"¿Qué profesional trabaja con la salud mental?","r":["psiquiatra","psicologo","psicóloga","psicologo"]},
            {"p":"¿Qué palabra describe atención a la salud mental?","r":["terapia","psicoterapia"]}
        ],
        "normal":[
            {"p":"¿Qué se usa para sedar a un paciente en emergencias (término general)?","r":["sedante","anestesico","anestésico"]},
            {"p":"¿Terapia breve o terapia de larga duración: cuál es más corta?","r":["breve","corta"]}
        ],
        "hard":[
            {"p":"¿Qué profesional diagnostica trastornos mentales médicamente?","r":["psiquiatra"]},
            {"p":"¿Terapia cognitiva conductual abreviada como?","r":["tcc","tcc."]}
        ],
        "expert":[
            {"p":"¿Qué fármaco es un antidepresivo ISRS? (ejemplo)","r":["fluoxetina","sertralina","paroxetina"]},
            {"p":"¿Qué escala evalúa la gravedad de la depresión (iniciales)?: PHQ-?","r":["9","phq-9"]}
        ]
    }
}

# ---------------- Dificultad ----------------
DIFFICULTY_MULT = {"easy":0.6, "normal":1.0, "hard":1.8, "expert":3.0}
BASE_DIFFICULTY_WEIGHTS = [50, 30, 15, 5]

def choose_difficulty_for_pay(pay: int):
    w = BASE_DIFFICULTY_WEIGHTS.copy()
    if pay >= 3000:
        w[2] = int(w[2]*1.6)
        w[3] = int(w[3]*2.0)
    elif pay >= 1000:
        w[2] = int(w[2]*1.2)
        w[3] = int(w[3]*1.3)
    return random.choices(["easy","normal","hard","expert"], weights=w, k=1)[0]

# ---------------- Minijuegos ----------------
async def play_dados(ctx, pay, bonus_time=0, book_bonus=False):
    dado = random.randint(1, 6)
    success_threshold = 4
    if book_bonus:
        success_threshold = 3  # Biblioteca Antigua: +20% éxito (menor umbral)
    if dado >= success_threshold:
        bonus = random.randint(0, max(1, pay//6))
        return pay + bonus, f"🎲 Sacaste un {dado}, ganaste {pay + bonus}💰"
    else:
        loss = max(10, pay//6)
        return -loss, f"🎲 Sacaste un {dado}, fallaste y perdiste {loss}💰"

async def play_pregunta(send_fn, pay, bonus_time=0, forced_difficulty: str | None = None, user_id=None, bot=None, book_bonus=False):
    """
    Si forced_difficulty viene (easy/normal/hard/expert) se fuerza esa dificultad.
    bonus_time añade segundos extra para responder.
    """
    if forced_difficulty and forced_difficulty not in ("easy","normal","hard","expert"):
        forced_difficulty = None

    category = random.choice(list(QUESTION_BANK.keys()))
    difficulty = forced_difficulty or choose_difficulty_for_pay(pay)
    bank = QUESTION_BANK.get(category, {})
    bucket = bank.get(difficulty, []) or bank.get("normal", [])
    q = random.choice(bucket)
    pregunta = q["p"]
    respuestas = [r.lower().strip() for r in q["r"]]

    total_time = 12 + max(0, int(bonus_time))
    embed = discord.Embed(
        title="🧠 Pregunta de trabajo",
        description=(f"**Categoría:** {category.capitalize()} — **Dificultad:** {difficulty.capitalize()}\n\n"
                     f"{pregunta}\n\nTienes {total_time}s para responder."),
        color=discord.Color.blurple()
    )
    await send_fn(embed=embed)

    def check(msg):
        return msg.author.id == user_id

    try:
        if not bot:
            penalty = max(5, int(pay*0.12))
            return -penalty, f"⏱️ Bot no disponible. Perdiste {penalty}💰"
        msg = await bot.wait_for("message", timeout=total_time, check=check)
        answer = msg.content.lower().strip()
    except asyncio.TimeoutError:
        penalty = max(5, int(pay*0.12))
        timeout_msg = f"⏱️ ¡Tiempo agotado! Perdiste {penalty}💰"
        await send_fn(f"❌ {timeout_msg}")
        return -penalty, timeout_msg
    except Exception:
        penalty = max(5, int(pay*0.12))
        return -penalty, f"⏱️ Error al esperar respuesta. Perdiste {penalty}💰"

    if answer in respuestas:
        reward = int(pay * DIFFICULTY_MULT[difficulty]) + random.randint(0, int(pay*0.15))
        return reward, f"✅ ¡Correcto! (+{reward}💰) — Categoria: {category.capitalize()} ({difficulty})"
    else:
        # Biblioteca Antigua: +20% chance de acertar una pregunta incorrecta
        if book_bonus and random.random() < 0.20:
            reward = int(pay * DIFFICULTY_MULT[difficulty] * 0.5)
            return reward, f"📚 ¡La Biblioteca te ayudó! Respuesta parcial. (+{reward}💰)"
        penalty = max(5, int(pay*0.08 * DIFFICULTY_MULT[difficulty]))
        return -penalty, f"❌ Incorrecto. (Respuesta esperada: {respuestas[0]}) Perdistes {penalty}💰"

GAME_FUNCTIONS = {"dados": play_dados, "pregunta": play_pregunta}

# ---------------- Vista para elegir dificultad ----------------
class ChooseDifficultyView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 18):
        super().__init__(timeout=timeout)
        self.user_id = int(user_id)
        self.result = None  # "easy"/"normal"/"hard"/"expert"/"random"
        self.message: discord.Message | None = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def on_timeout(self):
        # disable buttons (so user sees it's expired)
        try:
            for child in self.children:
                if hasattr(child, 'disabled'):
                    setattr(child, 'disabled', True)
        except Exception:
            pass
        # try to edit original message if available
        try:
            msg = self.message if hasattr(self, "message") else None
            if msg:
                await msg.edit(content="⌛ Tiempo para elegir dificultad agotado. Se escogerá aleatoria.", view=self)
        except Exception:
            pass

    @discord.ui.button(label="Fácil", style=discord.ButtonStyle.success)
    async def easy_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "easy"
        await interaction.response.edit_message(content="Dificultad seleccionada: **Fácil**. Procesando...", view=None)
        self.stop()

    @discord.ui.button(label="Normal", style=discord.ButtonStyle.primary)
    async def normal_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "normal"
        await interaction.response.edit_message(content="Dificultad seleccionada: **Normal**. Procesando...", view=None)
        self.stop()

    @discord.ui.button(label="Difícil", style=discord.ButtonStyle.secondary)
    async def hard_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "hard"
        await interaction.response.edit_message(content="Dificultad seleccionada: **Difícil**. Procesando...", view=None)
        self.stop()

    @discord.ui.button(label="Experto", style=discord.ButtonStyle.danger)
    async def expert_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "expert"
        await interaction.response.edit_message(content="Dificultad seleccionada: **Experto**. Procesando...", view=None)
        self.stop()

    @discord.ui.button(label="Aleatoria", style=discord.ButtonStyle.grey)
    async def random_btn(self, interaction: discord.Interaction, button: discord.ui.Button):
        self.result = "random"
        await interaction.response.edit_message(content="Dificultad seleccionada: **Aleatoria**. Procesando...", view=None)
        self.stop()

# ---------------- Cog y comando ----------------
class WorkCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def _work_internal(self, user_id, guild_id, send_fn, bot):
        """Internal work logic shared by prefix and slash commands"""
        user = await get_user(user_id)
        if not user:
            return await send_fn("❌ Usuario no encontrado en la base de datos.")
        job = user.get("trabajo", "Desempleado")
        if job not in JOBS:
            return await send_fn("❌ No tienes un trabajo asignado o tu trabajo no está en la lista.")

        pay = JOBS[job]["pay"]

        # cooldown
        last = await get_work_cooldown(user_id, job)
        if last and datetime.now() < last:
            remaining = last - datetime.now()
            secs = int(remaining.total_seconds())
            m, s = divmod(secs, 60)
            return await send_fn(f"⌛ Ya trabajaste. Próximo intento en {m}m {s}s")

        # bonus por items
        bonus_time = 0
        money_multiplier = 1.0
        inventory = await get_inventory(user_id)
        for it in inventory:
            if it["item"].lower() == "teléfono":
                bonus_time += 5  # +5s extra
            elif it["item"].lower() == "x2 de dinero de mecha":
                # Verificar si el buff está activo (menos de 1 hora)
                mecha_expiration = get_buff(user_id, "mecha_money_x2_until")
                if mecha_expiration and time.time() < mecha_expiration:
                    money_multiplier = 2.0
                else:
                    # Activar buff por 1 hora
                    set_buff(user_id, "mecha_money_x2_until", time.time() + 3600)
                    money_multiplier = 2.0
        
        # bonus por upgrade de club "Aula de Entrenamiento"
        if await club_has_upgrade(user_id, "Aula de Entrenamiento"):
            money_multiplier *= 1.25  # +25% dinero
        
        # bonus por upgrade de club "Biblioteca Antigua"
        book_bonus = await club_has_upgrade(user_id, "Biblioteca Antigua")

        # elegir minijuego
        game_name = random.choice(JOBS[job]["games"])
        game_func = GAME_FUNCTIONS.get(game_name)
        if not game_func:
            return await send_fn("❌ El minijuego seleccionado no está implementado.")

        # Si es pregunta, ofrecemos elegir dificultad con botones
        forced_difficulty = None
        if game_name == "pregunta":
            embed = discord.Embed(
                title="🧠 Elegir dificultad",
                description=("Elige la dificultad de la pregunta para este trabajo. "
                             "Más difícil → más recompensa. Si no eliges, se seleccionará aleatoria."),
                color=discord.Color.gold()
            )
            view = ChooseDifficultyView(user_id, timeout=18)
            msg = await send_fn(embed=embed, view=view)
            # guardar mensaje en view para que on_timeout pueda editarlo
            view.message = msg
            # esperar a que el usuario elija o timeout
            await view.wait()
            choice = view.result
            if choice == "random" or choice is None:
                forced_difficulty = None  # dejar que la función seleccione según pay
            else:
                forced_difficulty = choice

        try:
            if game_name == "pregunta":
                result, msg_text = await play_pregunta(send_fn, pay, bonus_time=bonus_time, forced_difficulty=forced_difficulty or "normal", user_id=user_id, bot=bot, book_bonus=book_bonus)
            else:
                result, msg_text = await game_func(send_fn, pay, bonus_time=bonus_time, book_bonus=book_bonus)
        except Exception as e:
            return await send_fn(f"❌ Error al ejecutar el minijuego: {e}")

        if result != 0:
            result = int(result * money_multiplier)
            # Aplicar bonificador de mascota
            pet_bonus = await get_pet_bonus_multiplier(user_id)
            result = int(result * pet_bonus)
            await add_money(user_id, result)
            # Dar XP a mascota
            await add_pet_xp(user_id, 15)
            # Actualizar progreso de misión "trabajar"
            await update_mission_progress(user_id)

        # cooldown 2 min
        await set_work_cooldown(user_id, job)

        # Mejorar embed visual
        color = discord.Color.green() if result > 0 else discord.Color.red()
        embed = discord.Embed(
            title=f"🏥 {job}",
            description=f"**Resultado Terapéutico:** {msg_text}",
            color=color
        )
        
        if result > 0:
            embed.add_field(name="💚 Mejora Psicológica", value=f"```+{result:,} recuperación```", inline=False)
        else:
            embed.add_field(name="❌ Sesión No Completada", value="```Fallaste el ejercicio terapéutico```", inline=False)
        
        embed.set_footer(text=f"⏳ Próxima terapia en 10 minutos")
        await send_fn(embed=embed)

    @commands.command(name="work")
    async def work_prefix(self, ctx):
        """!work - 🏥 Terapia Ocupacional"""
        async def send_fn(*args, **kwargs):
            return await ctx.send(*args, **kwargs)
        await self._work_internal(ctx.author.id, ctx.guild.id, send_fn, self.bot)

    @app_commands.command(name="work", description="🏥 Terapia Ocupacional - Trabaja en tu rol actual")
    async def work_slash(self, interaction: discord.Interaction):
        """Participa en terapia ocupacional"""
        await interaction.response.defer()
        async def send_fn(*args, **kwargs):
            return await interaction.followup.send(*args, **kwargs)
        await self._work_internal(interaction.user.id, interaction.guild_id, send_fn, self.bot)

# ---------------- Setup ----------------
async def setup(bot):
    await bot.add_cog(WorkCog(bot))





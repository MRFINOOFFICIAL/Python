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
# Estructura: RANGOS y TRABAJOS por rango
JOBS_BY_RANK = {
    "Novato": {
        "Camillero": {"pay": 150, "games": ["dados", "pregunta"]},
        "Limpiador de Traumas": {"pay": 100, "games": ["dados", "pregunta"]},
        "Asistente de Cocina Terapéutica": {"pay": 120, "games": ["dados", "pregunta"]},
        "Repartidor de Medicinas": {"pay": 130, "games": ["dados", "pregunta"]},
    },
    "Enfermo Básico": {
        "Asistente del Psiquiatra": {"pay": 250, "games": ["dados", "pregunta"]},
        "Camillero": {"pay": 150, "games": ["dados", "pregunta"]},
        "Auxiliar de Enfermería Mental": {"pay": 200, "games": ["dados", "pregunta"]},
        "Facilitador de Actividades Terapéuticas": {"pay": 220, "games": ["pregunta", "dados"]},
        "Archivero de Historias Clínicas": {"pay": 180, "games": ["dados", "pregunta"]},
    },
    "Enfermo Avanzado": {
        "Analista de Crisis": {"pay": 600, "games": ["pregunta", "dados"]},
        "Guardia Sedante": {"pay": 900, "games": ["dados", "pregunta"]},
        "Asistente del Psiquiatra": {"pay": 250, "games": ["dados", "pregunta"]},
        "Coordinador de Terapias de Grupo": {"pay": 750, "games": ["pregunta", "dados"]},
        "Inspector de Seguridad Psicológica": {"pay": 850, "games": ["dados", "pregunta"]},
        "Especialista en Técnicas de Relajación": {"pay": 700, "games": ["pregunta", "dados"]},
    },
    "Enfermo Supremo": {
        "Supervisor Psiquiátrico": {"pay": 1800, "games": ["dados", "pregunta"]},
        "Jefe de Terapia de Choque": {"pay": 3500, "games": ["dados", "pregunta"]},
        "Jefe del Distrito del Psicólogo": {"pay": 8000, "games": ["dados", "pregunta"]},
        "Director del Sanatorio": {"pay": 15000, "games": ["dados", "pregunta"]},
        "Maestro de Meditación Zen": {"pay": 2000, "games": ["pregunta", "dados"]},
        "Investigador de Traumas": {"pay": 4000, "games": ["pregunta", "dados"]},
        "Consejero Supremo del Bienestar Mental": {"pay": 10000, "games": ["pregunta", "dados"]},
        "Guardián de la Paz Mental": {"pay": 12000, "games": ["dados", "pregunta"]},
    }
}

# Estructura plana para compatibilidad con código existente
JOBS = {}
for rank_jobs in JOBS_BY_RANK.values():
    JOBS.update(rank_jobs)

# ---------------- Preguntas ----------------
QUESTION_BANK = {
    "matematicas": {
        "easy": [
            {"p":"¿Cuánto es (12 + 8) × 2?","r":["40"]},
            {"p":"¿Cuánto es 150 - 65?","r":["85"]},
            {"p":"¿Cuánto es 12 × 4?","r":["48"]},
            {"p":"¿Cuánto es 81 ÷ 9?","r":["9"]}
        ],
        "normal": [
            {"p":"¿Cuál es el valor de x en: 2x + 5 = 17?","r":["6"]},
            {"p":"¿Cuánto es 15 × 15?","r":["225"]},
            {"p":"¿Cuál es el 15% de 200?","r":["30"]},
            {"p":"Resuelve: (4^2) + (3^2)","r":["25"]}
        ],
        "hard": [
            {"p":"¿Cuánto es 17 × 14?","r":["238"]},
            {"p":"¿Cuál es el área de un círculo con radio 5? (Usa π=3.14)","r":["78.5"]},
            {"p":"¿Cuánto es 1024 ÷ 32?","r":["32"]},
            {"p":"Si x^2 = 225, ¿cuál es el valor positivo de x?","r":["15"]}
        ],
        "expert": [
            {"p":"¿Cuál es el logaritmo en base 10 de 1000?","r":["3"]},
            {"p":"¿Cuánto es 2^10?","r":["1024"]},
            {"p":"Resuelve: 13^2 + 14^2","r":["365"]},
            {"p":"¿Cuál es la raíz cúbica de 729?","r":["9"]}
        ]
    },
    "cultura": {
        "easy":[
            {"p":"¿Capital de España?","r":["madrid"]},
            {"p":"¿Cuál es el idioma principal de Brasil?","r":["portugues","portugués"]},
            {"p":"¿Capital de Francia?","r":["paris"]},
            {"p":"¿En qué país está la Torre Eiffel?","r":["francia"]},
            {"p":"¿Capital de Alemania?","r":["berlin"]},
            {"p":"¿Capital de Japón?","r":["tokio","tokyo"]}
        ],
        "normal":[
            {"p":"¿Capital de Italia?","r":["roma"]},
            {"p":"¿En qué continente está Egipto?","r":["africa"]},
            {"p":"¿Capital de México?","r":["cdmx","ciudad de méxico","méxico"]},
            {"p":"¿Capital de Canadá?","r":["ottawa"]},
            {"p":"¿Cuál es el río más largo del mundo?","r":["nilo"]},
            {"p":"¿Cuál es el continente más grande?","r":["asia"]}
        ],
        "hard":[
            {"p":"¿En qué año terminó la Segunda Guerra Mundial?","r":["1945"]},
            {"p":"¿Autor de 'Cien años de soledad'?","r":["gabriel garcia marquez","garcia marquez","gabo"]},
            {"p":"¿Quién fue el primer presidente de los EE.UU.?","r":["george washington","washington"]},
            {"p":"¿En qué año cayó el muro de Berlín?","r":["1989"]},
            {"p":"¿Capital de Rusia?","r":["moscú","moscu"]}
        ],
        "expert":[
            {"p":"¿Quién pintó 'La persistencia de la memoria'?","r":["salvador dali","dali"]},
            {"p":"¿En qué año fue la Revolución Francesa (inicio)?","r":["1789"]},
            {"p":"¿Cuál es la novela de John Steinbeck sobre la Gran Depresión?","r":["the grapes of wrath","las uvas de la ira"]},
            {"p":"¿Quién escribió 'Don Quijote'?","r":["miguel de cervantes","cervantes"]},
            {"p":"¿En qué año se firmó la Declaración de Independencia de EE.UU.?","r":["1776"]}
        ]
    },
    "ciencia": {
        "easy":[
            {"p":"¿El agua hierve a 100 en qué unidad?","r":["c","celsius","grados celsius"]},
            {"p":"¿Cuál es el gas que respiramos principalmente?","r":["oxigeno","oxígeno"]},
            {"p":"¿Cuántas patas tiene un insecto?","r":["6","seis"]},
            {"p":"¿Cuál es el animal más grande del mundo?","r":["ballena azul","ballena"]},
            {"p":"¿A qué temperatura se congela el agua?","r":["0","cero celsius"]}
        ],
        "normal":[
            {"p":"¿Qué planeta es conocido como el 'Planeta Rojo'?","r":["marte"]},
            {"p":"¿Unidad básica de los seres vivos?","r":["celula","célula"]},
            {"p":"¿Cuántos huesos tiene el esqueleto humano adulto?","r":["206","doscientos seis"]},
            {"p":"¿Qué elemento químico tiene el símbolo Au?","r":["oro"]},
            {"p":"¿Cuál es el planeta más cercano al Sol?","r":["mercurio"]}
        ],
        "hard":[
            {"p":"¿Qué partícula tiene carga negativa dentro del átomo?","r":["electron","electrón"]},
            {"p":"¿Qué órgano produce la insulina?","r":["pancreas","páncreas"]},
            {"p":"¿Cuántas capas tiene la atmósfera?","r":["5","cinco"]},
            {"p":"¿Qué científico desarrolló la teoría de la relatividad?","r":["albert einstein","einstein"]},
            {"p":"¿Cuál es la velocidad de la luz?","r":["300000 km/s","300000","3×10^8"]}
        ],
        "expert":[
            {"p":"¿Qué ley relaciona fuerza, masa y aceleración?","r":["segunda ley de newton","f=ma","f = m a"]},
            {"p":"¿Qué molécula lleva la información genética?","r":["dna","adn","ácido desoxirribonucleico"]},
            {"p":"¿Cuál es la partícula fundamental más pequeña que forma toda la materia?","r":["quark"]},
            {"p":"¿Quién fue el primer ganador del Premio Nobel en Física?","r":["wilhelm röntgen","rontgen"]},
            {"p":"¿En qué año descubrió Fleming la penicilina?","r":["1928"]}
        ]
    },
    "videojuegos": {
        "easy":[
            {"p":"¿En Minecraft, cuál es el nombre del material obtenido al minar diamantes?","r":["diamante","diamantes"]},
            {"p":"¿En qué consola salió originalmente 'Super Mario'?","r":["nes","nintendo"]},
            {"p":"¿Cómo se llama el personaje principal de Zelda?","r":["link"]},
            {"p":"¿Cuál es el juego más vendido de todos los tiempos?","r":["tetris"]},
            {"p":"¿Qué personaje es el icono de Nintendo?","r":["mario"]}
        ],
        "normal":[
            {"p":"¿Cómo se llama el creador de Minecraft?","r":["notch","markus persson","marcus persson"]},
            {"p":"¿Qué franquicia tiene un famoso personaje llamado 'Master Chief'?","r":["halo"]},
            {"p":"¿En qué año se lanzó el primer 'Pokémon'?","r":["1996"]},
            {"p":"¿Cuál es el nombre del protagonista de Final Fantasy VII?","r":["cloud","cloud strife"]},
            {"p":"¿Qué juego es famoso por decir 'All your base are belong to us'?","r":["zero wing"]}
        ],
        "hard":[
            {"p":"¿En qué año se lanzó el primer 'The Legend of Zelda'?","r":["1986"]},
            {"p":"¿Cuál es el género principal de 'Dark Souls'?","r":["rpg","acción rpg","souls-like"]},
            {"p":"¿Quién es el creador de la serie 'Metal Gear'?","r":["hideo kojima","kojima"]},
            {"p":"¿En qué año se lanzó Fortnite?","r":["2017"]},
            {"p":"¿Cuál es el famoso juego de disparos 2D de los 90s?","r":["doom"]}
        ],
        "expert":[
            {"p":"¿Cuál es el motor gráfico de 'Doom (1993)'?","r":["doom engine"]},
            {"p":"¿Quién dirigió 'The Last of Us' juego original?","r":["neil druckmann","neil"]},
            {"p":"¿En qué año fue la primera competencia de eSports profesional?","r":["1972"]},
            {"p":"¿Cuál fue el primer juego MMORPG masivo?","r":["ultima online","everquest"]},
            {"p":"¿Cuál es el juego de culto de 1999 que revolucionó los juegos de rol?","r":["planescape torment"]}
        ]
    },
    "sanatorio": {
        "easy":[
            {"p":"¿Qué profesional trabaja con la salud mental?","r":["psiquiatra","psicologo","psicóloga"]},
            {"p":"¿Qué palabra describe atención a la salud mental?","r":["terapia","psicoterapia"]},
            {"p":"¿Cuál es el número de emergencia psicológica en crisis?","r":["sos","teléfono de la esperanza"]},
            {"p":"¿Qué es la depresión?","r":["un trastorno mental","un desorden del ánimo"]},
            {"p":"¿Cuál es el objetivo principal de la terapia?","r":["sanar","recuperarse","mejorar"]}
        ],
        "normal":[
            {"p":"¿Qué se usa para sedar a un paciente en emergencias (término general)?","r":["sedante","anestesico"]},
            {"p":"¿Terapia breve o terapia de larga duración: cuál es más corta?","r":["breve","corta"]},
            {"p":"¿Cuál es el trastorno de ansiedad más común?","r":["trastorno de ansiedad generalizada","tag"]},
            {"p":"¿Qué técnica de respiración se usa para calmar la ansiedad?","r":["respiración profunda","box breathing"]},
            {"p":"¿Cuántos tipos principales de terapia existen?","r":["varios","múltiples","muchos"]}
        ],
        "hard":[
            {"p":"¿Qué profesional diagnostica trastornos mentales médicamente?","r":["psiquiatra"]},
            {"p":"¿Terapia cognitiva conductual abreviada como?","r":["tcc"]},
            {"p":"¿En qué año Freud publicó 'La Interpretación de los Sueños'?","r":["1900"]},
            {"p":"¿Cuál es el trastorno bipolar?","r":["una enfermedad mental con cambios de ánimo extremos"]},
            {"p":"¿Qué es el mindfulness?","r":["meditación","conciencia plena"]}
        ],
        "expert":[
            {"p":"¿Qué fármaco es un antidepresivo ISRS? (ejemplo)","r":["fluoxetina","sertralina","paroxetina"]},
            {"p":"¿Qué escala evalúa la gravedad de la depresión (iniciales)?: PHQ-?","r":["9"]},
            {"p":"¿Quién fue el fundador del psicoanálisis?","r":["sigmund freud","freud"]},
            {"p":"¿Qué es la resiliencia psicológica?","r":["la capacidad de recuperarse","adaptarse"]},
            {"p":"¿Cuál es el trastorno neurológico más relacionado con traumas?","r":["ptsd","trastorno de estrés postraumático"]}
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

def generate_false_options(correct_answer: str, num_options: int = 3) -> list:
    """Genera opciones falsas similares pero distintas a la respuesta correcta."""
    false_options = []
    
    # Lista de opciones falsas genéricas por categoría
    generic_false = [
        "Inexistente", "Variable dependiente", "Hipótesis nula", "Efecto placebo", 
        "Desviación estándar", "Error sistemático", "Análisis de regresión",
        "Correlación espuria", "Paradoja de Simpson", "Entropía negativa", 
        "Sinergia disruptiva", "Homeostasis", "Sesgo cognitivo", "Disonancia"
    ]
    
    # Adicionar opciones basadas en el tipo de respuesta
    try:
        if correct_answer.isdigit():
            num = int(correct_answer)
            # Generar números cercanos pero creíbles
            if num > 1000:
                false_options.extend([str(num + random.randint(1, 50)), str(num - random.randint(1, 50))])
            elif num > 100:
                false_options.extend([str(num + random.randint(1, 10)), str(num - random.randint(1, 10))])
            else:
                false_options.extend([str(num + 2), str(num - 2), str(num + 5)])
    except:
        pass
    
    # Agregar opciones genéricas
    false_options.extend(generic_false)
    
    # Remover duplicados y asegurar que no incluya la respuesta correcta
    false_options = list(set(false_options))
    false_options = [opt for opt in false_options if opt.lower() != correct_answer.lower()]
    
    # Garantizar que siempre hay al menos num_options opciones falsas
    if len(false_options) < num_options:
        # Si faltan opciones, agregar más genéricas
        extra = ["Quizás", "Tal vez", "Otro", "Distinto", "Diferente", "Opuesto"]
        false_options.extend([opt for opt in extra if opt.lower() != correct_answer.lower()])
        false_options = list(set(false_options))
    
    # Retornar exactamente N opciones (garantizado)
    if len(false_options) >= num_options:
        return random.sample(false_options, num_options)
    else:
        # Última línea de defensa: llenar con genéricas si aún falta
        return (false_options + ["Equivocado", "Nope", "No"])[:num_options]

async def play_pregunta(send_fn, pay, bonus_time=0, forced_difficulty: str | None = None, user_id=None, bot=None, book_bonus=False):
    """
    Sistema de múltiple choice (a, b, c, d).
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
    respuesta_correcta = q["r"][0].lower().strip()  # Primera respuesta es la correcta

    # Generar 4 opciones (1 correcta + 3 falsas)
    opciones_falsas = generate_false_options(respuesta_correcta, 3)
    todas_opciones = [respuesta_correcta] + opciones_falsas
    random.shuffle(todas_opciones)
    
    # Encontrar la letra correcta (a, b, c, d)
    indice_correcto = todas_opciones.index(respuesta_correcta)
    letra_correcta = chr(97 + indice_correcto)  # 'a', 'b', 'c', 'd'

    # Crear el texto de opciones
    opciones_texto = "\n".join([f"**{chr(97 + i)})** {todas_opciones[i]}" for i in range(4)])

    total_time = 12 + max(0, int(bonus_time))
    embed = discord.Embed(
        title="🧠 Pregunta de trabajo (Múltiple Choice)",
        description=(f"**Categoría:** {category.capitalize()} — **Dificultad:** {difficulty.capitalize()}\n\n"
                     f"**Pregunta:** {pregunta}\n\n"
                     f"**Opciones:**\n{opciones_texto}\n\n"
                     f"Responde con **a**, **b**, **c** o **d** ({total_time}s)"),
        color=discord.Color.blurple()
    )
    await send_fn(embed=embed)

    def check(msg):
        return msg.author.id == user_id and msg.content.lower().strip() in ['a', 'b', 'c', 'd']

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

    if answer == letra_correcta:
        reward = int(pay * DIFFICULTY_MULT[difficulty]) + random.randint(0, int(pay*0.15))
        return reward, f"✅ ¡Correcto! (+{reward}💰) — Respuesta: **{letra_correcta.upper()}) {respuesta_correcta}**"
    else:
        # Biblioteca Antigua: +20% chance de acertar una pregunta incorrecta
        if book_bonus and random.random() < 0.20:
            reward = int(pay * DIFFICULTY_MULT[difficulty] * 0.5)
            return reward, f"📚 ¡La Biblioteca te ayudó! Respuesta parcial. (+{reward}💰)"
        penalty = max(5, int(pay*0.08 * DIFFICULTY_MULT[difficulty]))
        return -penalty, f"❌ Incorrecto. (Respuesta correcta: **{letra_correcta.upper()}) {respuesta_correcta}**) Perdiste {penalty}💰"

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
        
        embed.set_footer(text=f"⏳ Próxima terapia en 2 minutos")
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





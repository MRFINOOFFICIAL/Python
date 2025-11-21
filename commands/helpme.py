# commands/ayuda.py
import discord
from discord.ext import commands
from discord import app_commands

# ====== Datos del almanaque (edítalos si agregas nuevos items) ======
ALMANAC_ITEMS = {
    "Cinta adhesiva":         {"rarity": "comun",  "desc": "Herramienta básica. Poco poder pero barata."},
    "Botella de sedante":     {"rarity": "comun",  "desc": "Consumible que puede ayudar en minijuegos relacionados con calma."},
    "Cuchillo oxidado":       {"rarity": "raro",   "desc": "Arma de contacto — buen poder en robos físicos."},
    "Pistola vieja":          {"rarity": "epico",  "desc": "Arma de fuego antigua — alto poder en robos."},
    "Botiquín":               {"rarity": "comun",  "desc": "Consumible que restaura durabilidad/usos o evita pequeñas penalizaciones."},
    "Arma blanca artesanal":  {"rarity": "raro",   "desc": "Arma hecha a mano — buen balance entre poder y durabilidad."},
    "Palo golpeador de parejas felices": {"rarity":"epico","desc":"Arma contundente con alto poder."},
    "Savi peluche":           {"rarity": "epico",  "desc": "Objeto engañoso — puede aumentar probabilidades en minijuegos de engaño."},
    "Hélice de ventilador":   {"rarity": "comun",  "desc": "Herramienta — aumenta pequeñas probabilidades al explorar zonas oscuras."},
    "Aconsejante Fantasma":   {"rarity": "epico",  "desc": "Objeto raro que otorga bonificaciones en ciertos minijuegos de mente."},
    "ID falso":               {"rarity": "raro",   "desc": "Usable para engañar en robos o interacciones (mejora chance de éxito en algunos intentos)."},
    "Máscara de Xfi":         {"rarity": "epico",  "desc": "Objeto de engaño con alto valor para ocultamiento en atracos."},
    "Bastón de Staff":        {"rarity": "raro",   "desc": "Herramienta/arma que aumenta poder en robos y minijuegos."},
    "Teléfono":               {"rarity": "comun",  "desc": "Herramienta que activa ciertas opciones en minijuegos (pequeña ventaja)."},
    "Chihuahua":              {"rarity": "raro",   "desc": "Mascota con bonificaciones pasivas pequeñas (p. ej. detecta cofres comunes)."},
    "Mecha Enojado":          {"rarity": "epico",  "desc": "Arma potente; mejora significativamente chance en robos."},
    "Linterna":               {"rarity": "comun",  "desc": "Aumenta la probabilidad de encontrar objetos raros al explorar."},
    "Llave Maestra":         {"rarity": "epico",   "desc": "Herramienta que permite desbloquear cofres y aumenta loot de cofres."},
    # Items de tienda / boosts
    "Paquete de peluches fino": {"rarity":"raro", "desc":"Consumible que contiene varios peluches (se pueden vender o usar)."},
    "x2 de dinero de mecha":     {"rarity":"epico","desc":"Boost: duplica ganancias relacionadas con 'Mecha' en 1 uso / mano de blackjack."},
    "Danza de Saviteto":         {"rarity":"raro", "desc":"Boost: aumenta ligeramente las probabilidades en blackjack mientras lo poseas."},
    "Kit de reparación":        {"rarity":"comun","desc":"Consumible que repara durabilidad de un item."}
}

# ====== Cofres y probabilidades (información explicativa del almanaque) ======
CHEST_INFO = {
    "Cofre Común": {
        "spawn_hint": "Frecuencia alta (lo más probable que aparezca).",
        "contains": "Objetos comunes y a veces raros en pequeña proporción.",
        "example_chance": "aprox. 60% de aparecer entre cofres"
    },
    "Cofre Raro": {
        "spawn_hint": "Menos frecuente; mayor recompensa.",
        "contains": "Objetos raros y consumibles útiles.",
        "example_chance": "aprox. 25% de aparecer entre cofres"
    },
    "Cofre Épico": {
        "spawn_hint": "Baja probabilidad; buen loot.",
        "contains": "Armas épicas o herramientas de gran valor.",
        "example_chance": "aprox. 10% de aparecer entre cofres"
    },
    "Cofre Legendario": {
        "spawn_hint": "Muy raro; excelente loot.",
        "contains": "Objetos legendarios (capaces de cambiar jugadas).",
        "example_chance": "aprox. 4% de aparecer entre cofres"
    },
    "Cofre Maestro": {
        "spawn_hint": "Extremadamente raro; 'drop' muy difícil.",
        "contains": "Objetos únicos o boosts muy potentes (ej.: duplicadores, llaves maestras).",
        "example_chance": "aprox. 1% de aparecer entre cofres"
    }
}

# ====== Vista interactiva ======
class HelpAlmanacView(discord.ui.View):
    def __init__(self, author_id: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)

        options = [
            discord.SelectOption(label="General", description="Ver la ayuda general de comandos", emoji="📜"),
            discord.SelectOption(label="Almanaque — Objetos", description="Descripción y efectos de cada objeto", emoji="📦"),
            discord.SelectOption(label="Almanaque — Cofres & Probabilidades", description="Qué contienen los cofres y su probabilidad", emoji="🗝️"),
            discord.SelectOption(label="Comandos Admin", description="Comandos que solo pueden usar administradores", emoji="🔒"),
        ]
        self.select = discord.ui.Select(placeholder="Elige una sección...", options=options, min_values=1, max_values=1)
        self.select.callback = self.on_select
        self.add_item(self.select)

        # botón cerrar
        btn = discord.ui.Button(label="Cerrar", style=discord.ButtonStyle.danger)
        btn.callback = self.on_close
        self.add_item(btn)

    async def on_select(self, interaction: discord.Interaction):
        # solo el autor puede interactuar
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Solo quien abrió la ayuda puede usar este menú.", ephemeral=True)

        choice = self.select.values[0]
        if choice == "General":
            embed = self._build_general()
        elif choice == "Almanaque — Objetos":
            embed = self._build_almanac_items()
        elif choice == "Almanaque — Cofres & Probabilidades":
            embed = self._build_chests()
        elif choice == "Comandos Admin":
            embed = self._build_admins()
        else:
            embed = discord.Embed(title="Error", description="Opción no reconocida.", color=discord.Color.red())

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            # si no se puede editar (fallback)
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_close(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Solo quien abrió la ayuda puede cerrar esto.", ephemeral=True)
        # desactivar controles y editar
        for child in list(self.children):
            try:
                if isinstance(child, discord.ui.Item):
                    child.disabled = True
            except Exception:
                pass
        try:
            await interaction.response.edit_message(content="— Vista cerrada —", view=self, embed=None)
        except Exception:
            try:
                await interaction.response.send_message("Vista cerrada.", ephemeral=True)
            except Exception:
                pass
        self.stop()

    def _build_general(self) -> discord.Embed:
        embed = discord.Embed(
            title="📜 Menú de Ayuda — Los Ezquisos",
            description="Guía rápida de comandos. Usa el **prefijo `!`** delante de cada comando (ej.: `!profile`).",
            color=discord.Color.dark_teal()
        )
        embed.add_field(name="Economía & Perfil",
                        value="`!profile` — Ver perfil\n`!shop` — Ver tienda\n`!buy <item>` — Comprar\n`!work` — Trabajar (minijuegos)\n`!jobs` — Trabajos\n`!apply <trabajo>` — Aplicarte",
                        inline=False)
        embed.add_field(name="Exploración & Objetos",
                        value="`!explore` — Buscar objetos\n`!inventory` — Ver inventario\n`!use <id>` — Usar item\n`!repair <id>` — Reparar item",
                        inline=False)
        embed.add_field(name="Minijuegos",
                        value="Al trabajar recibirás minijuegos. Responde rápido cuando aparezcan preguntas para ganar más.",
                        inline=False)
        embed.set_footer(text="Pulsa el menú para ver el Almanaque de objetos o cofres.")
        return embed

    def _build_almanac_items(self) -> discord.Embed:
        embed = discord.Embed(title="📚 Almanaque — Objetos", color=discord.Color.gold())
        embed.set_thumbnail(url="https://i.imgur.com/4M7IWwP.png")
        # agrupamos por rareza para mantener orden
        rarities = {}
        for name, info in ALMANAC_ITEMS.items():
            rar = info.get("rarity", "comun").capitalize()
            rarities.setdefault(rar, []).append((name, info["desc"]))

        for rar in sorted(rarities.keys(), key=lambda r: ["Comun","Raro","Epico","Legendario","Maestro"].index(r) if r in ["Comun","Raro","Epico","Legendario","Maestro"] else 0):
            lines = []
            for n, desc in rarities[rar]:
                lines.append(f"**{n}** — {desc}")
            embed.add_field(name=f"{rar} ({len(lines)})", value="\n".join(lines)[:1024], inline=False)

        embed.set_footer(text="Si agregas nuevos objetos al juego, actualiza ALMANAC_ITEMS en commands/ayuda.py")
        return embed

    def _build_chests(self) -> discord.Embed:
        embed = discord.Embed(title="🗝️ Almanaque — Cofres y probabilidades", color=discord.Color.purple())
        embed.add_field(name="Qué es un cofre", value="Al explorar, de vez en cuando puedes encontrar cofres en lugar de objetos. Cada cofre tiene un nivel y mejores cofres dan mejores objetos.", inline=False)
        for k, v in CHEST_INFO.items():
            embed.add_field(name=f"{k}", value=f"{v['spawn_hint']}\n**Contiene:** {v['contains']}\n**Ejemplo probabilidad (entre cofres):** {v['example_chance']}", inline=False)
        embed.add_field(name="Consejos",
                        value="- Tener llaves maestras o linternas aumenta la probabilidad de recibir mejores cofres.\n- Cofre Maestro: extremadamente raro; consérvalo o abre con todo preparado.",
                        inline=False)
        return embed

    def _build_admins(self) -> discord.Embed:
        embed = discord.Embed(title="🔒 Comandos de Administrador", color=discord.Color.dark_red())
        embed.add_field(name="Comandos clave",
                        value="`!addmoney @user <cantidad>` — Añadir dinero.\n`!setjob @user <trabajo>` — Asignar trabajo.\n`!resetcooldown @user [trabajo]` — Reiniciar cooldowns de work.",
                        inline=False)
        embed.set_footer(text="Estos comandos requieren permisos de administrador en el servidor.")
        return embed

    async def on_timeout(self):
        # desactivar controles
        for child in list(self.children):
            try:
                if isinstance(child, discord.ui.Item):
                    child.disabled = True
            except Exception:
                pass

# ====== Cog principal ======
class HelpCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ayuda")
    async def ayuda_prefix(self, ctx):
        """Comando de prefijo: !ayuda"""
        embed = discord.Embed(title="📜 Menú de Ayuda — Los Ezquisos",
                              description="Pulsa el menú para expandir secciones (Almanaque: objetos y cofres).",
                              color=discord.Color.dark_teal())
        embed.set_footer(text="Usa el menú para navegar. Los ejemplos usan prefijo `!`.")
        view = HelpAlmanacView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="ayuda", description="Muestra la ayuda del bot (menú interactivo)")
    async def ayuda_slash(self, interaction: discord.Interaction):
        """Comando slash: /ayuda"""
        await interaction.response.defer()
        embed = discord.Embed(title="📜 Menú de Ayuda — Los Ezquisos",
                              description="Pulsa el menú para expandir secciones (Almanaque: objetos y cofres).",
                              color=discord.Color.dark_teal())
        view = HelpAlmanacView(interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)

async def setup(bot):
    await bot.add_cog(HelpCog(bot))





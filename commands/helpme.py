# commands/helpme.py
"""
Sistema completo de ayuda interactivo con menú de secciones.
Incluye guía de comandos, almanaque de items, cofres y sistema de combate.
"""
import discord
from discord.ext import commands
from discord import app_commands


# ==================== DATOS DEL ALMANAQUE ====================

ALMANAC_ITEMS = {
    # Items de Exploración - Básicos
    "Cinta adhesiva": {"rarity": "comun", "desc": "Herramienta básica. Poco poder pero barata.", "tipo": "exploración"},
    "Botella de sedante": {"rarity": "comun", "desc": "Consumible que ayuda en minijuegos y robos.", "tipo": "exploración"},
    "Cuchillo oxidado": {"rarity": "raro", "desc": "Arma de contacto — buen poder en robos físicos.", "tipo": "exploración"},
    "Pistola vieja": {"rarity": "epico", "desc": "Arma de fuego antigua — alto poder en robos y combate.", "tipo": "exploración"},
    "Botiquín": {"rarity": "comun", "desc": "Consumible que restaura durabilidad/usos.", "tipo": "exploración"},
    "Arma blanca artesanal": {"rarity": "raro", "desc": "Arma hecha a mano — buen balance entre poder y durabilidad.", "tipo": "exploración"},
    "Palo golpeador de parejas felices": {"rarity": "epico", "desc": "Arma contundente con alto poder.", "tipo": "exploración"},
    "Savi peluche": {"rarity": "epico", "desc": "Objeto engañoso — bonificaciones en minijuegos.", "tipo": "exploración"},
    "Hélice de ventilador": {"rarity": "comun", "desc": "Herramienta — útil en exploración nocturna.", "tipo": "exploración"},
    "Aconsejante Fantasma": {"rarity": "epico", "desc": "Objeto raro que otorga bonificaciones en combate y minijuegos.", "tipo": "exploración"},
    "ID falso": {"rarity": "raro", "desc": "Usable para engañar en robos (mejora chance de éxito).", "tipo": "exploración"},
    "Máscara de Xfi": {"rarity": "epico", "desc": "Objeto de engaño con alto valor en robos y combate.", "tipo": "exploración"},
    "Bastón de Staff": {"rarity": "raro", "desc": "Herramienta/arma que aumenta poder en robos y combate.", "tipo": "exploración"},
    "Teléfono": {"rarity": "comun", "desc": "Herramienta que activa opciones en minijuegos (+6s extra).", "tipo": "exploración"},
    "Chihuahua": {"rarity": "raro", "desc": "Mascota con ataques aleatorios en combate (15-35 daño).", "tipo": "exploración"},
    "Mecha Enojado": {"rarity": "epico", "desc": "Arma potente; 70 de daño directo en combate.", "tipo": "exploración"},
    "Linterna": {"rarity": "comun", "desc": "Aumenta probabilidad de encontrar cofres raros.", "tipo": "exploración"},
    "Llave Maestra": {"rarity": "epico", "desc": "Desbloquea cofres sellados; 40 HP + 30 daño en combate.", "tipo": "exploración"},
    "Núcleo energético": {"rarity": "legendario", "desc": "Objeto legendario — 80 de daño directo al jefe en combate.", "tipo": "exploración"},
    "Fragmento Omega": {"rarity": "maestro", "desc": "Objeto maestro — Sistema de 2 turnos: 1º turno prepara (sin daño), 2º turno SUPER ATAQUE 120 daño.", "tipo": "exploración"},
    "Traje ritual": {"rarity": "legendario", "desc": "Objeto legendario — 60 HP de recuperación + defensa.", "tipo": "exploración"},
    
    # Items de Tienda - Especiales
    "Paquete de peluches fino": {"rarity": "epico", "desc": "Consumible que contiene 3 peluches aleatorios. Recupera 50 HP o vende por 5000💰", "tipo": "tienda"},
    "Poción de Furia": {"rarity": "epico", "desc": "Bebida potente — inflige 60 de daño directo al jefe en combate.", "tipo": "tienda"},
    "Escudo Mágico": {"rarity": "raro", "desc": "Protección mágica — te protege del próximo ataque enemigo en combate.", "tipo": "tienda"},
    "Nektar Antiguo": {"rarity": "legendario", "desc": "Bebida legendaria — recupera 100 HP completos en combate.", "tipo": "tienda"},
    "Danza de Saviteto": {"rarity": "raro", "desc": "Hechizo de aumento — tu próximo ataque inflige +50% de daño.", "tipo": "tienda"},
    "x2 de dinero de mecha": {"rarity": "epico", "desc": "Duplica dinero ganado en trabajos durante 1 hora. Se reactiva si trabajas nuevamente.", "tipo": "tienda"},
    "Kit de reparación": {"rarity": "comun", "desc": "Consumible que repara durabilidad de un item.", "tipo": "tienda"},
}

CHEST_INFO = {
    "Cofre Común": {
        "spawn_hint": "Frecuencia alta (lo más probable que aparezca).",
        "contains": "Objetos comunes y a veces raros.",
        "example_chance": "aprox. 60% de aparecer entre cofres"
    },
    "Cofre Raro": {
        "spawn_hint": "Menos frecuente; mayor recompensa.",
        "contains": "Objetos raros y consumibles útiles.",
        "example_chance": "aprox. 25% de aparecer entre cofres"
    },
    "Cofre Épico": {
        "spawn_hint": "Baja probabilidad; buen loot.",
        "contains": "Armas épicas o herramientas valiosas.",
        "example_chance": "aprox. 10% de aparecer entre cofres"
    },
    "Cofre Legendario": {
        "spawn_hint": "Muy raro; excelente loot.",
        "contains": "Objetos legendarios (capaces de cambiar jugadas).",
        "example_chance": "aprox. 4% de aparecer entre cofres"
    },
    "Cofre Maestro": {
        "spawn_hint": "Extremadamente raro; 'drop' muy difícil.",
        "contains": "Objetos únicos de alto poder (Fragmento Omega, Núcleo Energético).",
        "example_chance": "aprox. 1% de aparecer entre cofres"
    }
}

BOSS_INFO = {
    "Mini-Bosses (5)": [
        "• **Goblin Capitán** (80 HP, raro)",
        "• **Orco Guerrero** (100 HP, raro)",
        "• **Bruja del Bosque** (70 HP, épico)",
        "• **Mecha Enojado** (120 HP, épico)",
        "• **Savi Forma Teto** (150 HP, épico)",
    ],
    "Bosses Normales (4)": [
        "• **Dragón Antiguo** (300 HP, legendario)",
        "• **Rey Esqueleto** (250 HP, épico)",
        "• **Demonio Oscuro** (280 HP, legendario)",
        "• **Savi Forma Final** (350 HP, legendario)",
    ],
    "Bosses Especiales (5)": [
        "• **Psicólogo Loco** (350 HP, maestro)",
        "• **Médico Misterioso** (320 HP, maestro)",
        "• **Enfermera de Hierro** (400 HP, maestro)",
        "• **Director del Caos** (500 HP, maestro)",
        "• **Fino** (600 HP, maestro)",
    ]
}


# ==================== VISTA INTERACTIVA ====================

class HelpAlmanacView(discord.ui.View):
    """Vista con selector de temas para la ayuda"""
    
    def __init__(self, author_id: int, timeout: int = 120):
        super().__init__(timeout=timeout)
        self.author_id = int(author_id)

        options = [
            discord.SelectOption(label="General", description="Guía rápida de todos los comandos", emoji="📜"),
            discord.SelectOption(label="Exploración & Objetos", description="Cómo explorar y usar items", emoji="🌲"),
            discord.SelectOption(label="Combate & Bosses", description="Sistema de peleas contra jefes", emoji="⚔️"),
            discord.SelectOption(label="Tienda & Compras", description="Items de tienda y efectos", emoji="🏪"),
            discord.SelectOption(label="Almanaque — Cofres", description="Tipos de cofres y probabilidades", emoji="🗝️"),
            discord.SelectOption(label="Social & Economía", description="Misiones, Trading, Mercado, Duelos", emoji="💼"),
            discord.SelectOption(label="🏢 Clubs & Gremios", description="Crear clubs, upgrades, tesorería", emoji="🏢"),
            discord.SelectOption(label="Leaderboards & Upgrades", description="Rankings y mejoras permanentes", emoji="🏆"),
            discord.SelectOption(label="Comandos Admin", description="Comandos solo para administradores", emoji="🔒"),
        ]
        self.select = discord.ui.Select(placeholder="Elige una sección...", options=options, min_values=1, max_values=1)
        self.select.callback = self.on_select
        self.add_item(self.select)

        btn = discord.ui.Button(label="Cerrar", style=discord.ButtonStyle.danger)
        btn.callback = self.on_close
        self.add_item(btn)

    async def on_select(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Solo quien abrió la ayuda puede usar este menú.", ephemeral=True)

        choice = self.select.values[0]
        if choice == "General":
            embed = self._build_general()
        elif choice == "Exploración & Objetos":
            embed = self._build_exploration()
        elif choice == "Combate & Bosses":
            embed = self._build_combat()
        elif choice == "Tienda & Compras":
            embed = self._build_shop()
        elif choice == "Almanaque — Cofres":
            embed = self._build_chests()
        elif choice == "Social & Economía":
            embed = self._build_social()
        elif choice == "🏢 Clubs & Gremios":
            embed = self._build_clubs()
        elif choice == "Leaderboards & Upgrades":
            embed = self._build_leaderboards()
        elif choice == "Comandos Admin":
            embed = self._build_admins()
        else:
            embed = discord.Embed(title="Error", description="Opción no reconocida.", color=discord.Color.red())

        try:
            await interaction.response.edit_message(embed=embed, view=self)
        except Exception:
            await interaction.response.send_message(embed=embed, ephemeral=True)

    async def on_close(self, interaction: discord.Interaction):
        if interaction.user.id != self.author_id:
            return await interaction.response.send_message("❌ Solo quien abrió la ayuda puede cerrar esto.", ephemeral=True)
        for child in list(self.children):
            try:
                child.disabled = True
            except Exception:
                pass
        try:
            await interaction.response.edit_message(content="✅ Vista cerrada", view=self, embed=None)
        except Exception:
            pass
        self.stop()

    def _build_general(self) -> discord.Embed:
        """Ayuda general de comandos"""
        embed = discord.Embed(
            title="📜 Menú de Ayuda — Los Ezquisos",
            description="Guía completa del bot (RPG de economía hospitalaria).",
            color=discord.Color.dark_teal()
        )
        embed.add_field(
            name="📊 Perfil & Dinero",
            value="`/profile` — Ver tu perfil y stats\n`/work` — Trabajar y ganar dinero\n`/jobs` — Ver trabajos disponibles\n`/apply <trabajo>` — Aplicarte a un trabajo",
            inline=False
        )
        embed.add_field(
            name="🛍️ Tienda & Items",
            value="`/shop` — Ver la tienda\n`/buy <item>` — Comprar items\n`/equip <item>` — Equipar arma\n`/inventario` — Ver tu inventario completo\n`/use <item>` — Usar un item\n`/repair` — Reparar items con Kit de reparación",
            inline=False
        )
        embed.add_field(
            name="🌲 Exploración",
            value="`/explore` — Buscar objetos y cofres (cooldown 25s)",
            inline=False
        )
        embed.add_field(
            name="⚔️ Combate & Bosses",
            value="`/spawnboss <nombre>` — Invocar un jefe en el servidor\n`/fight` — Pelear contra el jefe activo\n`/bossinfo` — Ver info del jefe actual",
            inline=False
        )
        embed.add_field(
            name="🃏 Minijuegos",
            value="`/blackjack` — Jugar blackjack y apostar dinero",
            inline=False
        )
        embed.add_field(
            name="💰 Robar",
            value="`/rob <@usuario>` — Robar dinero de otro jugador (cooldown: 5 minutos)",
            inline=False
        )
        embed.add_field(
            name="💼 Social & Competencia",
            value="`/misiones` — Ver misiones diarias\n`/leaderboard [stat]` — Ver rankings\n`/ofrecer-trade` — Intercambiar items\n`/vender-item` — Vender en mercado\n`/desafiar` — Apostar dinero vs otro jugador",
            inline=False
        )
        embed.add_field(
            name="🏢 Clubs (Gremios)",
            value="`/crear-club <nombre>` — Crear un nuevo club\n`/unirse-club <nombre>` — Unirse a un club existente\n`/club-info` — Ver info de tu club\n`/salir-club` — Salir de tu club\n`/depositar-club <dinero>` — Donar dinero al club\n`/retirar-club <dinero>` — Retirar dinero (solo líder)\n`/upgrades-club` — Ver upgrades disponibles\n`/comprar-upgrade-club <nombre>` — Comprar upgrade",
            inline=False
        )
        embed.set_footer(text="Usa el menú para ver detalles de cada sección.")
        return embed

    def _build_exploration(self) -> discord.Embed:
        """Guía de exploración"""
        embed = discord.Embed(
            title="🌲 Exploración & Objetos",
            description="Sistema de búsqueda de items y cofres.",
            color=discord.Color.teal()
        )
        embed.add_field(
            name="¿Cómo explorar?",
            value="Usa `/explore` (cooldown: 25 segundos). Encontrarás:\n• **Items aleatorios** (rareza comun a maestro)\n• **Cofres con múltiples items** (12% de probabilidad)\n• **Efectos especiales** (Linterna, Teléfono, Chihuahua)",
            inline=False
        )
        embed.add_field(
            name="Inventario",
            value="**Sin límite** de items en el inventario.\n• Puedes acumular todos los items que desees.\n• Usa `/inventario` para ver tu inventario completo con detalles.\n• Usa `/use` para usar items directamente.\n• Usa `/repair` para reparar items dañados con Kit de reparación.",
            inline=False
        )
        embed.add_field(
            name="Items Especiales",
            value="🔦 **Linterna** — Aumenta probabilidad de cofres/items raros (24h)\n📱 **Teléfono** — +6s extra en preguntas de trabajo\n🐕 **Chihuahua** — Te da una moneda de compañía",
            inline=False
        )
        embed.add_field(
            name="Cofres Sellados",
            value="Los cofres épicos, legendarios y maestros pueden estar **sellados** 🔐\nNecesitas **Llave Maestra** para abrirlos (se consume al usarla).",
            inline=False
        )
        embed.set_footer(text="Los items encontrados se usan automáticamente en combate si los tienes equipados.")
        return embed

    def _build_combat(self) -> discord.Embed:
        """Guía de combate"""
        embed = discord.Embed(
            title="⚔️ Combate & Bosses",
            description="Sistema de combate por turnos contra 14 jefes diferentes.",
            color=discord.Color.red()
        )
        embed.add_field(
            name="¿Cómo pelear?",
            value="**1.** Admin usa `/spawnboss <nombre>` para invocar un jefe\n**2.** Tú usas `/fight` para atacar\n**3.** Elige una acción cada turno: ⚔️ **Atacar**, 🛡️ **Defender**, 📦 **Usar Item**",
            inline=False
        )
        embed.add_field(
            name="⚔️ Atacar",
            value="Inflige daño basado en tu arma equipada. Posibilidad de **crítico** (doble daño).",
            inline=False
        )
        embed.add_field(
            name="🛡️ Defender",
            value="Reduce el daño del próximo ataque enemigo.",
            inline=False
        )
        embed.add_field(
            name="📦 Usar Item",
            value="**Items de exploración:**\n• Núcleo Energético: 80 daño\n• Fragmento Omega: 2-turno (1º prepara, 2º = 120 daño CRÍTICO)\n• Pistola/Máscara: 50 daño\n• Chihuahua: 15-35 daño aleatorio\n• Llave Maestra: 40 HP + 30 daño\n• Traje Ritual: 60 HP + defensa\n\n**Items de tienda:**\n• Poción de Furia: 60 daño\n• Escudo Mágico: Protege del próximo ataque\n• Nektar Antiguo: 100 HP recuperados\n• Danza de Saviteto: +50% daño próximo\n\n**Cada arma tiene beneficio único** (usa `/equip` para ver tu arma actual)",
            inline=False
        )
        embed.add_field(
            name="🎯 Beneficios de Armas",
            value="Cada arma tiene un beneficio especial único:\n• **Pistola vieja**: Ráfagas (20% crítico)\n• **Fragmento Omega**: 90% precisión, 60 daño, 40% crítico - **MÁS POTENTE**\n• **Núcleo Energético**: 80% precisión, 50 daño, 30% crítico\n• **Máscara de Xfi**: Intimidante (reduce ataque jefe 20%)\n• **Chihuahua**: Tu amiguito ataca también (15-35 dmg aleatorio)\n\nUsa `/equip <nombre>` para equipar un arma y ver su beneficio completo.",
            inline=False
        )
        embed.add_field(
            name="Cooldown de Combate",
            value="Espera **2 minutos** entre combates contra el mismo jefe.",
            inline=False
        )
        # Agregar info de bosses
        for boss_type, bosses in BOSS_INFO.items():
            embed.add_field(name=boss_type, value="\n".join(bosses), inline=False)
        return embed

    def _build_shop(self) -> discord.Embed:
        """Guía de tienda"""
        embed = discord.Embed(
            title="🏪 Tienda & Compras",
            description="Items especiales con efectos únicos y HUEVOS de mascotas.",
            color=discord.Color.gold()
        )
        
        embed.add_field(
            name="🥚 HUEVOS DE MASCOTAS (Sistema actualizado)",
            value="**Ahora hay 4 huevos genéricos con probabilidades diferentes:**\n\n🟡 **Huevo Común** (500💰)\n→ 70% mascota común, 20% rara, 10% épica\n\n🟠 **Huevo Raro** (2500💰)\n→ 30% común, 50% rara, 15% épica, 5% legendaria\n\n🔴 **Huevo Épico** (10000💰)\n→ 10% común, 25% rara, 55% épica, 10% legendaria\n\n⭐ **Huevo Legendario** (50000💰)\n→ 5% común, 10% rara, 20% épica, **65% legendaria**\n\n**Mascotas posibles:** Chihuahua, Gato, Perro, Loro (común) | Conejo, Hamster (raro) | Dragón, Fenix (épico) | Saviteto, Finopeluche, Mechones (legendario)",
            inline=False
        )
        
        tienda_items = {item: info for item, info in ALMANAC_ITEMS.items() if info.get("tipo") == "tienda"}
        for name, info in tienda_items.items():
            embed.add_field(
                name=f"{name} ({info['rarity'].capitalize()})",
                value=info["desc"],
                inline=False
            )
        
        embed.add_field(
            name="💡 Recomendaciones",
            value="🔧 **Kit de reparación** — Usa `/repair` para restaurar durabilidad de items (250💰)\n💰 **x2 de dinero de mecha** — Duplica dinero en trabajos 1 hora (1200💰)\n⚡ **Fragmento Omega** — El item más potente del juego\n🥚 **Huevos** — Compra el que mejor se adapte a tu presupuesto y riesgo",
            inline=False
        )
        
        embed.set_footer(text="Usa `/buy <nombre exacto>` para comprar. Los items se añaden a tu inventario.")
        return embed

    def _build_exploration_items(self) -> discord.Embed:
        """Almanaque de items de exploración"""
        embed = discord.Embed(title="📚 Almanaque — Items de Exploración", color=discord.Color.gold())
        embed.set_thumbnail(url="https://i.imgur.com/4M7IWwP.png")
        
        rarities = {}
        for name, info in ALMANAC_ITEMS.items():
            if info.get("tipo") == "exploración":
                rar = info.get("rarity", "comun").capitalize()
                rarities.setdefault(rar, []).append((name, info["desc"]))

        rarity_order = ["Comun", "Raro", "Epico", "Legendario", "Maestro"]
        for rar in sorted(rarities.keys(), key=lambda r: rarity_order.index(r) if r in rarity_order else 999):
            lines = []
            for n, desc in rarities[rar]:
                lines.append(f"**{n}** — {desc}")
            value = "\n".join(lines)
            if len(value) > 1024:
                value = value[:1021] + "..."
            embed.add_field(name=f"{rar} ({len(lines)})", value=value, inline=False)

        return embed

    def _build_chests(self) -> discord.Embed:
        """Guía de cofres"""
        embed = discord.Embed(
            title="🗝️ Almanaque — Cofres y Probabilidades",
            color=discord.Color.purple()
        )
        embed.add_field(
            name="¿Qué es un cofre?",
            value="Al explorar (12% probabilidad), encuentras un cofre en lugar de un item. Contiene múltiples items basados en su rareza.",
            inline=False
        )
        
        for k, v in CHEST_INFO.items():
            embed.add_field(
                name=f"{k}",
                value=f"🎁 **Frecuencia:** {v['spawn_hint']}\n📦 **Contiene:** {v['contains']}\n📊 **Probabilidad:** {v['example_chance']}",
                inline=False
            )
        
        embed.add_field(
            name="Consejos",
            value="🔦 Tener **Linterna** aumenta probabilidad de cofres raros.\n🔑 **Llave Maestra** abre cofres sellados (se consume).\n⚡ Cofre Maestro: extremadamente raro; consérvalo o prepárate bien.",
            inline=False
        )
        return embed

    def _build_social(self) -> discord.Embed:
        """Guía de sistemas sociales y economía"""
        embed = discord.Embed(
            title="💼 Social & Economía Avanzada",
            description="Interacciona con otros jugadores y expande tu imperio.",
            color=discord.Color.blurple()
        )
        embed.add_field(
            name="📋 Misiones Diarias",
            value="`/misiones` — Ver tu misión del día (gana 400-600💰)\n`/completar-mision` — Reclama la recompensa si completaste la misión\n\n**Tipos:** Trabajar 5 veces, Explorar 3 veces, Robar 2 veces",
            inline=False
        )
        embed.add_field(
            name="📦 Trading de Items",
            value="`/ofrecer-trade @user item_tuyo item_suyo` — Proponer intercambio\n`/mis-trades` — Ver trades pendientes\n\n💡 Intercambia items raros entre jugadores.",
            inline=False
        )
        embed.add_field(
            name="🏪 Mercado de Items",
            value="`/vender-item <id> <precio>` — Poner item a la venta\n`/mercado` — Ver items en venta\n\n💡 Vende items a otros jugadores por dinero.",
            inline=False
        )
        embed.add_field(
            name="⚔️ Duelos por Dinero",
            value="`/desafiar @user cantidad` — Apuesta dinero en un duelo\n`/mis-duelos` — Ver desafíos pendientes\n\n💡 El ganador se lleva todo. ¡Arriesga sabiamente!",
            inline=False
        )
        return embed

    def _build_clubs(self) -> discord.Embed:
        """Guía de clubs y gremios"""
        embed = discord.Embed(
            title="🏢 Clubs & Gremios",
            description="Crea gremios, ahorra dinero en común y obtén bonificadores para todos los miembros.",
            color=discord.Color.dark_blue()
        )
        embed.add_field(
            name="📝 Crear & Gestionar Club",
            value="`/crear-club <nombre>` — Crear un club nuevo (máx 10 miembros)\n`/unirse-club <nombre>` — Unirse a un club existente\n`/club-info` — Ver información de tu club\n`/salir-club` — Salir del club",
            inline=False
        )
        embed.add_field(
            name="💰 Tesorería Compartida",
            value="`/depositar-club <dinero>` — Donar dinero al club\n`/retirar-club <dinero>` — Retirar dinero (solo líder)\n\n💡 El dinero del club se usa para comprar upgrades que benefician a TODOS",
            inline=False
        )
        embed.add_field(
            name="🎁 Upgrades de Club (4 tipos)",
            value="**🏫 Aula de Entrenamiento** (5000💰) — +25% dinero en trabajos\n**🧘 Sala de Meditación** (8000💰) — +30% XP por victoria\n**⚔️ Armería Mejorada** (10000💰) — +15% daño en combate\n**📚 Biblioteca Antigua** (6000💰) — +20% éxito en minijuegos\n\n✅ Los upgrades benefician a TODOS los miembros automáticamente",
            inline=False
        )
        embed.add_field(
            name="👥 Rangos de Miembros",
            value="**👑 Líder** — Crea el club, gestiona tesorería y elige upgrades\n**🔨 Oficial** — Promocionado por el líder\n**👤 Miembro** — Parte del club\n\nComandos de líder: `/promover-miembro`, `/expulsar-miembro`, `/transferir-liderazgo`",
            inline=False
        )
        embed.add_field(
            name="📊 Estadísticas",
            value="`/stats-club` — Ver tesorería, dinero de miembros, XP combinado\n`/clubs` — Ver lista de todos los clubs en el servidor",
            inline=False
        )
        embed.add_field(
            name="💡 Estrategia",
            value="🤝 Únete a un club para multiplicar tus ganancias\n💰 Contribuye dinero a los upgrades para beneficiarte\n📈 Los upgrades son inversiones colectivas que pagan dividendos infinitos",
            inline=False
        )
        return embed

    def _build_leaderboards(self) -> discord.Embed:
        """Guía de leaderboards y upgrades"""
        embed = discord.Embed(
            title="🏆 Leaderboards & Upgrades Permanentes",
            description="Compite contra otros y mejora permanentemente.",
            color=discord.Color.gold()
        )
        embed.add_field(
            name="📊 Leaderboards",
            value="`/leaderboard dinero` — Ver top 10 por 💰 dinero\n`/leaderboard experiencia` — Ver top 10 por ⭐ XP\n\n💡 Demuestra que eres el mejor del servidor.",
            inline=False
        )
        embed.add_field(
            name="🐕 Mascotas con XP (Sistema completo)",
            value="**Las mascotas ganan XP automáticamente:**\n• `/comprar-mascota` — Obtén huevos en tienda\n• `/use Huevo` — Eclosiona la mascota (rareza afecta tiempo)\n• `/mi-mascota` — Ver stats de tu mascota\n• Ganan XP en trabajos (+15 XP) y bosses (+25 XP)\n• Cada 100 XP = +1 NIVEL\n• Bonus progresivo: Nivel 1 = +5%, Nivel 10 = +50%, Nivel 20 = +100%\n• **Bonus se aplica a dinero y XP automáticamente**",
            inline=False
        )
        embed.add_field(
            name="🔧 Upgrades Permanentes (Sistema en BD)",
            value="Compra mejoras que nunca desaparecen:\n• 📈 **Mejor ganancia de dinero** — +25% en trabajos\n• ⭐ **XP Boost** — +50% experiencia\n• 🛡️ **Durabilidad++** — Items duran más\n• 💪 **Poder de Robo** — +20% éxito en robos\n\n💡 Son inversiones a largo plazo que multiplican tus ganancias.",
            inline=False
        )
        embed.add_field(
            name="🍷 Bebida de la Vida",
            value="`/buy Bebida de la Vida` — 8000💰\n`/use` — Usar para ganar 1 vida extra\n\n⚠️ **Sistema de Vidas (Actualizado):**\n• **COMIENZAS CON 3 VIDAS** (antes era 1)\n• 20% probabilidad de morir en explore\n• Si mueres, PIERDES TODO (dinero, items, XP)\n• Vuelves con 3 vidas reseteadas\n• ¡Compra vidas extras para protegerte en exploración peligrosa!",
            inline=False
        )
        return embed

    def _build_admins(self) -> discord.Embed:
        """Comandos para admins"""
        embed = discord.Embed(
            title="🔒 Comandos de Administrador",
            color=discord.Color.dark_red()
        )
        embed.add_field(
            name="Gestión de Servidores",
            value="`/setchannel <#canal>` — Configurar canal para anuncios de bosses\n`/getchannel` — Ver canal configurado\n`/event enable` — Activar anuncios de eventos",
            inline=False
        )
        embed.add_field(
            name="Gestión de Jugadores",
            value="`/addmoney @user <cantidad>` — Añadir dinero\n`/setjob @user <trabajo>` — Asignar trabajo\n`/resetcooldown @user [trabajo]` — Reiniciar cooldowns",
            inline=False
        )
        embed.add_field(
            name="Bosses",
            value="`/spawnboss <nombre>` — Invocar un jefe con autocomplete\n`/bossinfo` — Ver información del jefe actual",
            inline=False
        )
        embed.set_footer(text="Estos comandos requieren permisos de administrador en el servidor.")
        return embed

    async def on_timeout(self):
        """Desactiva controles al expirar"""
        for child in list(self.children):
            try:
                child.disabled = True
            except Exception:
                pass


# ==================== COG PRINCIPAL ====================

class HelpCog(commands.Cog):
    """Sistema de ayuda interactivo"""
    
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="ayuda")
    async def ayuda_prefix(self, ctx):
        """Comando de prefijo: !ayuda"""
        embed = discord.Embed(
            title="📜 Menú de Ayuda — Los Ezquisos",
            description="Guía completa del bot. Usa el menú para navegar entre secciones.",
            color=discord.Color.dark_teal()
        )
        embed.set_footer(text="Sistema RPG de economía hospitalaria.")
        view = HelpAlmanacView(ctx.author.id)
        await ctx.send(embed=embed, view=view)

    @app_commands.command(name="ayuda", description="📜 Muestra la ayuda del bot (menú interactivo)")
    async def ayuda_slash(self, interaction: discord.Interaction):
        """Comando slash: /ayuda"""
        await interaction.response.defer()
        embed = discord.Embed(
            title="📜 Menú de Ayuda — Los Ezquisos",
            description="Guía completa del bot. Usa el menú para navegar entre secciones.",
            color=discord.Color.dark_teal()
        )
        embed.set_footer(text="Sistema RPG de economía hospitalaria.")
        view = HelpAlmanacView(interaction.user.id)
        await interaction.followup.send(embed=embed, view=view)


# ==================== SETUP ====================

async def setup(bot):
    """Carga el cog de ayuda"""
    await bot.add_cog(HelpCog(bot))

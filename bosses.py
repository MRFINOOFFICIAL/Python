# bosses.py
import random
from datetime import datetime, timedelta
from typing import Dict, Optional

# Mapeo de armas únicas por boss
BOSS_WEAPONS = {
    "Goblin Capitán": "Espada del Goblin",
    "Orco Guerrero": "Hacha del Orco",
    "Bruja del Bosque": "Vara de la Bruja",
    "Mecha Enojado": "Mecha Enojado",  # Boss único
    "Savi Forma Teto": "Núcleo de Savi",
    "Dragón Antiguo": "Aliento del Dragón",
    "Rey Esqueleto": "Corona del Rey Esqueleto",
    "Demonio Oscuro": "Espada Oscura",
    "Savi Forma Final": "Esencia de Savi",
    "Psicólogo Loco": "Cordura Rota",
    "Médico Misterioso": "Bisturí Misterioso",
    "Enfermera de Hierro": "Jeringa de Hierro",
    "Director del Caos": "Cetro del Caos",
    "Fino": "Espada de Fino",
}

BOSSES_DB = {
    "Mini-Boss": [
        {"name": "Goblin Capitán", "hp": 80, "ataque": 8, "rareza": "raro", "prob": 0.4, "rewards": {"dinero": (100, 200), "items": ["ID falso", "Chihuahua"]}},
        {"name": "Orco Guerrero", "hp": 100, "ataque": 10, "rareza": "raro", "prob": 0.3, "rewards": {"dinero": (150, 250), "items": ["Bastón de Staff"]}},
        {"name": "Bruja del Bosque", "hp": 70, "ataque": 12, "rareza": "epico", "prob": 0.2, "rewards": {"dinero": (200, 300), "items": ["Núcleo energético"]}},
        {"name": "Mecha Enojado", "hp": 120, "ataque": 15, "rareza": "epico", "prob": 0.25, "rewards": {"dinero": (300, 500), "items": ["Fragmento Omega"]}},
        {"name": "Savi Forma Teto", "hp": 150, "ataque": 18, "rareza": "epico", "prob": 0.2, "rewards": {"dinero": (400, 600), "items": ["Fragmento Omega"]}},
    ],
    "Boss": [
        {"name": "Dragón Antiguo", "hp": 300, "ataque": 20, "rareza": "legendario", "prob": 0.15, "rewards": {"dinero": (1000, 2000), "items": ["Llave Maestra", "Fragmento Omega"]}},
        {"name": "Rey Esqueleto", "hp": 250, "ataque": 18, "rareza": "epico", "prob": 0.2, "rewards": {"dinero": (800, 1500), "items": ["Fragmento Omega"]}},
        {"name": "Demonio Oscuro", "hp": 280, "ataque": 22, "rareza": "legendario", "prob": 0.1, "rewards": {"dinero": (1200, 2500), "items": ["Llave Maestra"]}},
        {"name": "Savi Forma Final", "hp": 350, "ataque": 28, "rareza": "legendario", "prob": 0.18, "rewards": {"dinero": (2000, 3500), "items": ["Fragmento Omega", "Traje ritual", "Núcleo energético"]}},
    ],
    "Especial": [
        {"name": "Psicólogo Loco", "hp": 350, "ataque": 25, "rareza": "maestro", "prob": 1.0, "rewards": {"dinero": (3000, 5000), "items": ["Fragmento Omega", "Núcleo energético"]}},
        {"name": "Médico Misterioso", "hp": 320, "ataque": 28, "rareza": "maestro", "prob": 1.0, "rewards": {"dinero": (2500, 4500), "items": ["Traje ritual", "Llave Maestra"]}},
        {"name": "Enfermera de Hierro", "hp": 400, "ataque": 30, "rareza": "maestro", "prob": 1.0, "rewards": {"dinero": (4000, 6000), "items": ["Fragmento Omega"]}},
        {"name": "Director del Caos", "hp": 500, "ataque": 35, "rareza": "maestro", "prob": 1.0, "rewards": {"dinero": (5000, 8000), "items": ["Fragmento Omega", "Núcleo energético", "Traje ritual"]}},
        {"name": "Fino", "hp": 600, "ataque": 40, "rareza": "maestro", "prob": 1.0, "rewards": {"dinero": (8000, 12000), "items": ["Fragmento Omega", "Núcleo energético", "Traje ritual"]}},
    ]
}

# Mapeo dinámico de armas basado en poder del item
WEAPON_STATS = {
    "Cinta adhesiva": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.05},
    "Botella de sedante": {"hit_chance": 0.55, "damage": 8, "crit_chance": 0.12},
    "Cuchillo oxidado": {"hit_chance": 0.7, "damage": 18, "crit_chance": 0.15},
    "Pistola vieja": {"hit_chance": 0.75, "damage": 35, "crit_chance": 0.2},
    "Botiquín": {"hit_chance": 0.3, "damage": 2, "crit_chance": 0.05},
    "Arma blanca artesanal": {"hit_chance": 0.75, "damage": 25, "crit_chance": 0.12},
    "Palo golpeador de parejas felices": {"hit_chance": 0.8, "damage": 30, "crit_chance": 0.1},
    "Savi peluche": {"hit_chance": 0.6, "damage": 12, "crit_chance": 0.3},
    "Hélice de ventilador": {"hit_chance": 0.45, "damage": 8, "crit_chance": 0.08},
    "Aconsejante Fantasma": {"hit_chance": 0.65, "damage": 30, "crit_chance": 0.25},
    "ID falso": {"hit_chance": 0.55, "damage": 22, "crit_chance": 0.35},
    "Máscara de Xfi": {"hit_chance": 0.7, "damage": 35, "crit_chance": 0.18},
    "Bastón de Staff": {"hit_chance": 0.75, "damage": 28, "crit_chance": 0.12},
    "Teléfono": {"hit_chance": 0.45, "damage": 12, "crit_chance": 0.1},
    "Chihuahua": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.2},
    "Mecha Enojado": {"hit_chance": 0.85, "damage": 40, "crit_chance": 0.25},
    "Linterna": {"hit_chance": 0.4, "damage": 7, "crit_chance": 0.05},
    "Llave Maestra": {"hit_chance": 0.3, "damage": 0, "crit_chance": 0.05},
    "Anillo oxidado": {"hit_chance": 0.45, "damage": 3, "crit_chance": 0.08},
    "Mapa antiguo": {"hit_chance": 0.5, "damage": 0, "crit_chance": 0.15},
    "Gafas de soldador": {"hit_chance": 0.6, "damage": 10, "crit_chance": 0.1},
    "Caja de cerillas": {"hit_chance": 0.35, "damage": 5, "crit_chance": 0.2},
    "Receta secreta": {"hit_chance": 0.55, "damage": 15, "crit_chance": 0.15},
    "Núcleo energético": {"hit_chance": 0.8, "damage": 50, "crit_chance": 0.3},
    "Fragmento Omega": {"hit_chance": 0.9, "damage": 60, "crit_chance": 0.4},
    "Traje ritual": {"hit_chance": 0.75, "damage": 45, "crit_chance": 0.35},
    "Placa de identificación": {"hit_chance": 0.6, "damage": 12, "crit_chance": 0.1},
    "Cable USB": {"hit_chance": 0.4, "damage": 2, "crit_chance": 0.05},
    "Garrafa de aceite": {"hit_chance": 0.35, "damage": 8, "crit_chance": 0.05},
    "Guitarra rota": {"hit_chance": 0.65, "damage": 16, "crit_chance": 0.2},
    # Items de tienda
    "Paquete de peluches fino": {"hit_chance": 0.55, "damage": 10, "crit_chance": 0.25},
    "x2 de dinero de mecha": {"hit_chance": 0.5, "damage": 5, "crit_chance": 0.1},
    "Danza de Saviteto": {"hit_chance": 0.7, "damage": 12, "crit_chance": 0.35},
    "Kit de reparación": {"hit_chance": 0.0, "damage": 0, "crit_chance": 0.0},  # No es arma de combate
    "Savi Forma Teto": {"hit_chance": 0.75, "damage": 35, "crit_chance": 0.3},
    "Savi Forma Final": {"hit_chance": 0.8, "damage": 50, "crit_chance": 0.4},
    "Fino": {"hit_chance": 0.95, "damage": 70, "crit_chance": 0.5},
    # Armas especiales de bosses
    "Espada del Goblin": {"hit_chance": 0.75, "damage": 42, "crit_chance": 0.15},
    "Hacha del Orco": {"hit_chance": 0.78, "damage": 44, "crit_chance": 0.16},
    "Vara de la Bruja": {"hit_chance": 0.76, "damage": 46, "crit_chance": 0.22},
    "Núcleo de Savi": {"hit_chance": 0.80, "damage": 48, "crit_chance": 0.25},
    "Aliento del Dragón": {"hit_chance": 0.85, "damage": 55, "crit_chance": 0.28},
    "Corona del Rey Esqueleto": {"hit_chance": 0.82, "damage": 54, "crit_chance": 0.26},
    "Espada Oscura": {"hit_chance": 0.87, "damage": 56, "crit_chance": 0.30},
    "Esencia de Savi": {"hit_chance": 0.88, "damage": 58, "crit_chance": 0.32},
    "Cordura Rota": {"hit_chance": 0.90, "damage": 60, "crit_chance": 0.35},
    "Bisturí Misterioso": {"hit_chance": 0.91, "damage": 61, "crit_chance": 0.36},
    "Jeringa de Hierro": {"hit_chance": 0.92, "damage": 62, "crit_chance": 0.37},
    "Cetro del Caos": {"hit_chance": 0.93, "damage": 63, "crit_chance": 0.38},
    "Espada de Fino": {"hit_chance": 0.95, "damage": 65, "crit_chance": 0.40},
}

def get_random_boss(boss_type: str) -> Optional[Dict]:
    """Spawn a random boss based on probability"""
    if boss_type not in BOSSES_DB:
        return None
    
    candidates = BOSSES_DB[boss_type]
    for boss in candidates:
        if random.random() < boss["prob"]:
            boss_copy = boss.copy()
            boss_copy["type"] = boss_type
            boss_copy["max_hp"] = boss_copy["hp"]
            return boss_copy
    
    boss_copy = random.choice(candidates).copy()
    boss_copy["type"] = boss_type
    boss_copy["max_hp"] = boss_copy["hp"]
    return boss_copy

def get_boss_by_name(boss_name: str) -> Optional[Dict]:
    """Get a specific boss by name"""
    for boss_type, category in BOSSES_DB.items():
        for boss in category:
            if boss["name"].lower() == boss_name.lower():
                boss_copy = boss.copy()
                boss_copy["type"] = boss_type
                boss_copy["max_hp"] = boss_copy["hp"]
                return boss_copy
    return None

def get_all_boss_names() -> list:
    """Get all available boss names for autocomplete"""
    names = []
    for category in BOSSES_DB.values():
        for boss in category:
            names.append(boss["name"])
    return names

def get_available_bosses_by_type(boss_type: str) -> list:
    """Get all boss names in a category"""
    if boss_type not in BOSSES_DB:
        return []
    return [boss["name"] for boss in BOSSES_DB[boss_type]]

def calculate_player_damage(equipped_item: Optional[str] = None) -> tuple:
    """Calculate player damage based on equipped weapon"""
    if not equipped_item or equipped_item not in WEAPON_STATS:
        return (1, 3, 0.05)  # (hit_chance, base_damage, crit_chance)
    
    stats = WEAPON_STATS[equipped_item]
    return (stats["hit_chance"], stats["damage"], stats["crit_chance"])

def calculate_damage(base_damage: int, is_crit: bool = False) -> int:
    """Calculate damage with variance and critical hits"""
    variance = random.uniform(0.8, 1.2)
    damage = int(base_damage * variance)
    if is_crit:
        damage = int(damage * 1.5)
    return max(1, damage)

def resolve_player_attack(equipped_item: Optional[str] = None) -> tuple:
    """Resolve player attack, returns (hit: bool, damage: int, is_crit: bool)"""
    hit_chance, base_damage, crit_chance = calculate_player_damage(equipped_item)
    
    hit = random.random() < hit_chance
    is_crit = random.random() < crit_chance if hit else False
    damage = calculate_damage(base_damage, is_crit) if hit else 0
    
    return (hit, damage, is_crit)

def resolve_boss_attack(boss: Dict) -> tuple:
    """Resolve boss attack, returns (hit: bool, damage: int, is_crit: bool)"""
    boss_hit_chance = 0.6
    boss_crit_chance = 0.1
    
    hit = random.random() < boss_hit_chance
    is_crit = random.random() < boss_crit_chance if hit else False
    damage = calculate_damage(boss["ataque"], is_crit) if hit else 0
    
    return (hit, damage, is_crit)

async def get_boss_reward(boss: Dict) -> Dict:
    """Get rewards for defeating a boss"""
    dinero_range = boss["rewards"]["dinero"]
    dinero = random.randint(dinero_range[0], dinero_range[1])
    items = boss["rewards"]["items"]
    item = random.choice(items) if items else None
    
    return {"dinero": dinero, "item": item}

def get_weapon_benefit(weapon: Optional[str]) -> str:
    """Get specific weapon benefit description"""
    if not weapon:
        return "⚔️ Sin arma equipada"
    
    benefits = {
        "Cinta adhesiva": "🔗 Pegadizo: Aumenta adherencia (pequeña bonificación)",
        "Botella de sedante": "💤 Sedación: Disminuye precisión del jefe (-5% ataque)",
        "Cuchillo oxidado": "🩸 Sangrado: Algunos golpes causan sangrado adicional",
        "Pistola vieja": "🔫 Ráfagas: Mayor probabilidad de crítico (20%)",
        "Botiquín": "🏥 Curación: Restaura 5 HP por cada ataque defendido",
        "Arma blanca artesanal": "⚔️ Versátil: Balance entre daño y defensa",
        "Palo golpeador de parejas felices": "💥 Contundente: 10% chance extra de crítico",
        "Savi peluche": "🎲 Engañoso: Aumento de evasión (30% crítico)",
        "Hélice de ventilador": "🌪️ Viento: Pequeña deflexión de ataques enemigos",
        "Aconsejante Fantasma": "👻 Fantasmal: Aumenta daño crítico (+25%)",
        "ID falso": "🎭 Engaño: Altas probabilidades de crítico (35%)",
        "Máscara de Xfi": "😈 Intimidante: Reduce ataque del jefe 20%, crítico 18%",
        "Bastón de Staff": "🪄 Mágico: Golpes mágicos + defensa mejorada",
        "Teléfono": "📱 Llamada: Puede convocar ayuda (pequeño daño extra)",
        "Chihuahua": "🐕 Compañía: Tu amiguito ataca también (aleatorio 15-35 dmg)",
        "Mecha Enojado": "🤖 Potencia Máxima: 85% precisión, 40 daño, 25% crítico",
        "Linterna": "🔦 Iluminación: Revela puntos débiles del jefe",
        "Llave Maestra": "🔑 Desbloqueador: Abre oportunidades de defensa (+40 HP)",
        "Núcleo energético": "⚡ Energía Pura: 80% precisión, 50 daño, 30% crítico",
        "Fragmento Omega": "✨ Omega: 90% precisión, 60 daño, 40% crítico - MÁS POTENTE",
        "Traje ritual": "🎭 Ritual: 75 HP max, 45 daño, 35% crítico + defensa",
        "Poción de Furia": "💢 Furia: +50% daño en próximo turno",
        "Escudo Mágico": "🛡️ Mágico: Protege completamente del próximo ataque",
        "Nektar Antiguo": "🍯 Antiguo: Restaura 100 HP (máximo poder de curación)",
        "Danza de Saviteto": "💃 Danza: Próximo ataque +50% daño",
        "x2 de dinero de mecha": "💰 Duplicador: Dobla el daño del próximo ataque",
    }
    
    return benefits.get(weapon, "⚔️ Arma: Mejora probabilidad de golpe, daño y crítico")

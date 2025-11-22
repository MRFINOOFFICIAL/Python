# Overview

This is a Discord economy bot built with Python that simulates a psychiatric hospital-themed RPG game. Users can work jobs, explore for items, fight bosses, play minigames like blackjack, rob each other, and manage an inventory system with various weapons and items. The bot features a comprehensive economy system with multiple progression tiers, special items with unique properties, and both prefix (`!`) and slash (`/`) command support.

# User Preferences

Preferred communication style: Simple, everyday language.

# System Architecture

## Core Technologies
- **Framework**: Discord.py (v2.3.2+) for bot functionality and slash command support
- **Database**: aiosqlite for asynchronous SQLite operations
- **AI Integration**: OpenAI GPT-4 API for chat/question features
- **Web Server**: Flask for keep-alive endpoint (likely for hosting services like Replit)
- **Async Runtime**: asyncio for concurrent operations

## Database Schema

### Main Tables
1. **users** - Stores player profiles
   - `user_id` (TEXT, PRIMARY KEY)
   - `dinero` (INTEGER) - currency
   - `experiencia` (INTEGER) - experience points
   - `rango` (TEXT) - player rank/tier
   - `trabajo` (TEXT) - current job

2. **inventory** - Item storage with durability system
   - `id` (INTEGER, PRIMARY KEY)
   - `user_id` (TEXT)
   - `item` (TEXT) - item name
   - `rareza` (TEXT) - rarity tier
   - `usos` (INTEGER) - remaining uses
   - `durabilidad` (INTEGER) - item condition
   - `categoria` (TEXT) - item category
   - `poder` (INTEGER) - item power level

3. **shop** - Purchasable items
   - `name` (TEXT, PRIMARY KEY)
   - `price` (INTEGER)
   - `type` (TEXT)
   - `effect` (TEXT)
   - `rarity` (TEXT)

4. **work_cooldowns** - Job cooldown tracking
5. **boss_tables** - Active boss fight state management

## Command Architecture

**Dual Command System**: All major commands support both traditional prefix (`!command`) and modern slash commands (`/command`) through a shared implementation pattern:
- Prefix commands use `@commands.command`
- Slash commands use `@app_commands.command`
- Both route to the same underlying `_internal_method` with a `send_fn` callback pattern

**Command Categories** (Cogs):
1. **Profile** - User stats and inventory viewing
2. **Jobs** - Employment system with rank-based progression
3. **Work** - Job execution with minigames (dice rolls, trivia questions)
4. **Shop** - Item purchasing system
5. **Explore** - Loot discovery with chest types and interactive button UI
6. **Rob** - PvP stealing mechanics with weapon selection
7. **Bosses** - Guild-wide boss fights with HP tracking and rewards
8. **Blackjack** - Casino minigame with betting
9. **Items** - Item consumption and usage (repair kits, buffs)
10. **Admin Tools** - Server administrator commands

## Game Mechanics

### Item System
- **Rarity Tiers**: común → raro → épico → legendario → maestro
- **Categories**: arma, herramientas, quimicos, engano, tecnologia, mascota, salud
- **Durability**: Items degrade with use and can be repaired
- **Power Scaling**: Each item has combat/utility power values stored in `ITEM_STATS` dictionary

### Progression System
- **Ranks**: Novato → Enfermo Básico → Enfermo Avanzado → Enfermo Supremo
- **Jobs**: Tiered employment with increasing salaries (120 to 12,000 currency)
- **Experience**: Gained through work and activities

### Boss System
- **Boss Types**: Mini-Boss, Boss, and Especial categories (14 total bosses) with varying HP/attack/rewards
- **Guild-Wide**: One active boss per server
- **Combat**: Turn-based with equipped weapon mechanics and critical hits
- **Cooldowns**: 2-minute cooldown between fight attempts per user
- **Weapon Benefits**: Each weapon has unique combat effects (25+ weapons with specific bonuses like ráfagas, sedación, etc.)
- **Fragmento Omega Mechanic**: Requires 2 sequential uses for super attack (120 damage) - first use prepares, second use activates

### Loot System
- **Chest Types**: Común, Raro, Épico, Legendario with weighted spawn rates
- **Interactive UI**: Discord buttons for opening chests
- **Special Items**: Unique effects (Teléfono extends exploration time, Linterna boosts rare finds, Chihuahua detects common chests)

## State Management

### In-Memory Cache (`cache.py`)
Temporary buffs and states stored in memory (lost on restart):
- `telefono_extra_time` - Extended exploration duration
- `linterna_boost_until` - Timestamp for flashlight effect
- `chihuahua_passive_expires` - Pet detection buff expiration

**Limitation**: Being in-memory, this data doesn't persist across bot restarts.

### Database Persistence
Core game state (money, items, XP, jobs) stored in SQLite for durability.

## Interactive UI Components

**Discord.ui.View** system for rich interactions:
- Button-based chest opening in exploration
- Weapon selection menus for robberies
- Blackjack game controls (Hit/Stand/Double)
- Timeout handling (30-120 seconds)

## External Service Integration

### OpenAI API (`ai_helpers.py`)
- Asynchronous GPT-4 calls using thread pool executor
- System prompt customization support
- Used for enhanced chat features or trivia generation
- Requires `OPENAI_API_KEY` environment variable

### Flask Keep-Alive Server (`keep_alive.py`)
- Runs on port 8080
- Provides health check endpoint for uptime monitoring services
- Daemon thread prevents blocking main bot loop

## Error Handling

**Global Error Handler** in `main.py`:
- `CommandNotFound`: Gracefully informs user
- `CommandOnCooldown`: Shows remaining wait time
- Generic error fallback with exception logging

## Cooldown System

**Multi-Level Cooldowns**:
1. **Work Cooldowns**: Per-job, per-user tracking in database
2. **Fight Cooldowns**: 2-minute delay between boss attacks
3. **Exploration**: Managed via interactive session timeouts

# External Dependencies

## Core Services
- **Discord API** - Primary platform via discord.py library
- **OpenAI GPT-4** - AI-powered chat and question generation
- **SQLite** - Local database (no external database server required)

## Hosting Considerations
- **Replit Environment**: Code uses Replit Secrets for API keys
- **Flask Server**: Suggests deployment on platforms requiring keep-alive pings
- **Environment Variables**: `OPENAI_API_KEY` required in secrets/environment

## Python Libraries
- `discord.py>=2.3.2` - Discord bot framework
- `openai` - OpenAI API client
- `aiosqlite` - Async SQLite interface
- `flask` - Web server for health checks

## Notable Architecture Decisions

**No External Database**: Uses SQLite instead of PostgreSQL/MySQL for simplicity and portability on Replit.

**Async-First Design**: Leverages asyncio throughout for non-blocking database and API operations.

**Modular Cog System**: Commands organized into separate files under `/commands` directory for maintainability.

**Dual Command Support**: Maintains backward compatibility with prefix commands while supporting modern slash commands.

## Recent Changes (Session Nov 22, 2025)

### Session Summary
**Completed Advanced Features Implementation + Game Balance Pass:**

1. **Fixed Import Error**: Added missing `import asyncio` in commands/work.py that was blocking /work command
2. **Updated /ayuda Help System**: 
   - Added new section for 4 generic egg system (Común, Raro, Épico, Legendario) with dynamic probabilities
   - Updated Tienda section with full egg details showing rareza-based pet drop rates
   - Updated Sistema de Vidas to show users NOW START WITH 3 LIVES (previously 1)
   - Updated Mascotas section with complete XP system documentation (100 XP = 1 Level, progressively up to 100% bonus)
   - Added cooldown info for /rob (5 minutes)

3. **Database Tables Verified (Tarea 1 ✓)**:
   - All required tables exist: daily_missions, trades, market, pet_xp, duels, mascotas, clubs, upgrades
   - Database schema fully supports all advanced features

4. **Command Systems Verified**:
   - **Leaderboards**: `/leaderboard [dinero|experiencia]` - Top 10 rankings
   - **Daily Missions**: `/misiones` and `/completar-mision` - Get daily missions with rewards
   - **Trading System**: `/ofrecer-trade @user item_tuyo item_suyo` - Item exchanges
   - **Market**: `/vender-item <id> <precio>` and `/mercado` - Player marketplace
   - **Duels**: `/desafiar @user cantidad` - 1v1 PvP for money

5. **Game Balance Adjustments** ⚖️:
   - **Job Salaries**: +20-25% increase (Camillero 120→150, Director 12000→15000)
   - **Shop Prices**: -20-30% reduction (más accesible, Huevo Legendario 50000→35000)
   - **Boss Rewards**: +10-30% increase (Mini-Boss dinero rango, Especial bosses 20-30% boost)
   - **Rob Rewards**: +150% increase (20-300 → 50-600) making PvP more viable
   - **Pet Egg Prices**: -20-30% (Huevo Raro 2500→1800, Épico 10000→7000)
   - **Special Items**: More affordable (Bebida Vida 8000→5500, Poción Furia 3500→2500)

6. **Visual Improvements - Embed Design** ✨:
   - **Profile Command**: Color dinámico según rango (Novato gris, Básico azul, Avanzado púrpura, Supremo oro), mostrar vidas, trabajo actual, inventario con rarezas
   - **Inventory Command**: Emojis de rareza por item (⚪🔵🟣🟠🔶), barras de durabilidad visuales (▰▱), formato mejorado
   - **Work Command**: Resultado con embed verde/rojo, ganancia en código monoespaciado, footer con info de cooldown
   - **Fight Command**: Victoria con embed dorado y emojis (🏆), derrota con embed rojo oscuro, recompensas formateadas con códigos, mostrar bonus de mascota
   - **Shop Command**: Emojis de rareza para cada item (⚪🔵🟣🟠🔶), precio en código, descripción clara, footer motivacional, navegación mejorada

7. **Cooldown System Completed** ⏳:
   - **Work** (`/work`): 10 minutos
   - **Explore** (`/explore`): 25 segundos (prefix y slash)
   - **Fight** (`/fight`): 2 minutos
   - **Rob** (`/rob`): 5 minutos (prefix y slash)
   - **Duel** (`/desafiar`): 1 minuto
   - Todas las tablas de cooldown creadas en base de datos (rob_cooldowns, explore_cooldowns, duel_cooldowns)

8. **New Gathering & Crafting Systems** ⛏️🎣🔨:
   - **Mining** (`/minar`): 30 segundos cooldown - Extract minerals and crystals (Comunes hasta Maestro)
   - **Fishing** (`/pescar`): 40 segundos cooldown - Catch aquatic creatures (Comunes hasta Maestro)
   - **Forging** (`/forjar`): Craft unique weapons from different rarities:
     - **Comunes** (500-600💰): Espada Leimma, Espada Gato, Bastón de Anciano, Daga Ratera, Espada Pez, Hélice
     - **Raras** (2000-2500💰): Espada de Finno, Kratos Espada, Espada de Energía Halo
     - **Épicas** (8000-9000💰): Bate Golpeador, Katana de Musashi
     - **Legendaria** (25000💰): Dragón Slayer

### Previous Session (Nov 21, 2025)
1. **Fixed Explore Errors**: Corrected `remove_item()` function calls - changed from 2 arguments to 1 argument (item_id only)
2. **Updated Help System**: Completely rewrote `/ayuda` command with 6 interactive sections covering 14 bosses, combat mechanics, items, chests, and admin tools
3. **Weapon Benefit System**: Added 25+ unique weapon-specific descriptions showing actual combat bonuses (e.g., "Sedación: Disminuye precisión del jefe -5%")
4. **Fragmento Omega Mechanic**: Implemented 2-turn charge system - first use prepares the weapon, second use activates 120-damage super attack
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
- **Boss Types**: Mini-Boss and Boss categories with varying HP/attack/rewards
- **Guild-Wide**: One active boss per server
- **Combat**: Turn-based with equipped weapon mechanics and critical hits
- **Cooldowns**: 2-minute cooldown between fight attempts per user

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
import discord
from discord.ext import commands
import sqlite3
import datetime
import os

TOKEN = os.getenv('DISCORD_TOKEN')

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# ======= DATABASE =========

conn = sqlite3.connect("aurum.db")
cursor = conn.cursor()

def init_db():
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS clientes (
            user_id INTEGER PRIMARY KEY,
            tiene_cuenta BOOLEAN,
            saldo INTEGER DEFAULT 0,
            rol TEXT DEFAULT 'basico',
            fecha_registro TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS prestamos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            monto INTEGER,
            intereses INTEGER,
            total_pagar INTEGER,
            estado TEXT,
            fecha_limite TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            accion TEXT,
            detalle TEXT,
            fecha TEXT
        )
    """)

    conn.commit()

# ======= LOGS =========

async def log_action(guild, user, accion, detalle):
    cursor.execute(
        "INSERT INTO logs (user_id, accion, detalle, fecha) VALUES (?, ?, ?, ?)",
        (user.id, accion, detalle, str(datetime.datetime.now()))
    )
    conn.commit()

    channel = discord.utils.get(guild.text_channels, name="🧾・logs-aurum")
    if channel:
        await channel.send(f"🧾 **{user}** → {accion}\n📌 {detalle}")

# ======= CARGA DE COGS (FUERA DE on_ready) =========

import os

async def load_cogs():
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    COGS_DIR = os.path.join(BASE_DIR, "cogs")

    for filename in os.listdir(COGS_DIR):
        if filename.endswith(".py"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"✅ Cargado: {filename}")
            except Exception as e:
                print(f"❌ Error en {filename}: {e}")
# ======= ON READY =========

@bot.event
async def on_ready():
    print(f"✅ Bot conectado como {bot.user}")

    init_db()

    try:
        synced = await bot.tree.sync()
        print(f"🔄 Slash commands: {len(synced)}")
    except Exception as e:
        print(e)

# ======= START =========

async def main():
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

import asyncio
asyncio.run(main())
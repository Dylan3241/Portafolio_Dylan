import discord
from discord.ext import commands
from discord import app_commands
import config

class CanariasBotMod(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=discord.Intents.all(),
            application_id = 1443050572910690434
        )

    async def setup_hook(self):
        from database.database import create_tables
        create_tables()
        # Aca se cargan los cogs
        await self.load_extension("cogs.admins")
        await self.load_extension("cogs.moderation")
        await self.load_extension("cogs.sistemas")

        print("Bot cargado correctamente")

bot = CanariasBotMod()

@bot.event
async def on_ready():
    print(f"Bot iniciado como {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Slash commands sincronizados: {len(synced)}")
        
    except Exception as e:
        print(f"Error al sincronizar: {e}")

bot.run(config.TOKEN)
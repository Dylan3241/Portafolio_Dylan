import discord
from discord.ext import commands
import re
import time
from datetime import timedelta

LOG_CHANNEL_ID = 1443062286502727691

class SistemasSeguridad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Anti Flood
        self.mensajes_rapidos = {}   # {user_id: [timestamps]}

        # Anti Spam (mensajes repetidos)
        self.ultimo_mensaje = {}     # {user_id: "contenido"}

        # Strikes para calcular mute escalado
        self.strikes = {}            # {user_id: strike_count}

    # --------------------------------------------------------------------
    # EVENTO: cada mensaje
    # --------------------------------------------------------------------
    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if message.author.bot:
            return

        await self.anti_flood(message)
        await self.anti_spam(message)
        await self.anti_links(message)

    # --------------------------------------------------------------------
    # APLICAR SANCION AUTOMATICA
    # --------------------------------------------------------------------
    async def aplicar_mute(self, usuario: discord.Member, razon: str):
        user_id = usuario.id

        if user_id not in self.strikes:
            self.strikes[user_id] = 0

        self.strikes[user_id] += 1

        tiempos = {
            1: timedelta(minutes=1),
            2: timedelta(minutes=5),
            3: timedelta(minutes=10),
            4: timedelta(minutes=20),
            5: timedelta(minutes=30)
        }

        nivel = self.strikes[user_id]
        if nivel > 5:
            nivel = 5  # Máximo 30 minutos

        duracion = tiempos[nivel]

        # Aplicar timeout
        try:
            await usuario.timeout(duracion, reason=razon)
        except:
            return  # Si no tiene permisos, evitamos crasheo

        # Logs
        embed = discord.Embed(
            title="🚨 SANCION AUTOMÁTICA",
            description=(
                f"**Usuario:** {usuario.mention}\n"
                f"**Razón:** {razon}\n"
                f"**Mute automático:** {duracion.total_seconds() / 60:.0f} minutos\n"
                f"**Strikes:** {self.strikes[user_id]}/5"
            ),
            color=discord.Color.red()
        )
        embed.set_footer(text="Sistema automático de protección")

        canal_log = self.bot.get_channel(LOG_CHANNEL_ID)
        if canal_log:
            await canal_log.send(embed=embed)

    # --------------------------------------------------------------------
    # ANTI FLOOD
    # --------------------------------------------------------------------
    async def anti_flood(self, message: discord.Message):
        user_id = message.author.id
        ahora = time.time()

        if user_id not in self.mensajes_rapidos:
            self.mensajes_rapidos[user_id] = []

        self.mensajes_rapidos[user_id].append(ahora)

        # Limpiar mensajes viejos
        ventana = 5  # segundos
        limite = 5   # mensajes permitidos en esa ventana

        self.mensajes_rapidos[user_id] = [
            t for t in self.mensajes_rapidos[user_id] if ahora - t <= ventana
        ]

        # Si excede límite → sanción
        if len(self.mensajes_rapidos[user_id]) > limite:
            try: await message.delete()
            except: pass

            await self.aplicar_mute(
                usuario=message.author,
                razon="Anti Flood: demasiados mensajes en muy poco tiempo"
            )

    # --------------------------------------------------------------------
    # ANTI SPAM (mensajes repetidos)
    # --------------------------------------------------------------------
    async def anti_spam(self, message: discord.Message):
        user_id = message.author.id
        contenido = message.content.lower()

        if user_id not in self.ultimo_mensaje:
            self.ultimo_mensaje[user_id] = contenido
            return

        if contenido == self.ultimo_mensaje[user_id]:
            try: await message.delete()
            except: pass

            await self.aplicar_mute(
                usuario=message.author,
                razon="Anti Spam: mensajes repetidos"
            )

        self.ultimo_mensaje[user_id] = contenido

    # --------------------------------------------------------------------
    # ANTI LINKS
    # --------------------------------------------------------------------
    async def anti_links(self, message: discord.Message):
        texto = message.content.lower()

        patron = r"(https?://|discord\.gg|www\.)"
        if re.search(patron, texto):

            # Si es del mismo servidor → permitido
            if message.guild:
                invitaciones = ["discord.gg", "discord.com/invite"]
                if any(inv in texto for inv in invitaciones):
                    return

            try: await message.delete()
            except: pass

            await self.aplicar_mute(
                usuario=message.author,
                razon="Anti Links: envío de enlaces no permitidos"
            )


async def setup(bot):
    await bot.add_cog(SistemasSeguridad(bot))

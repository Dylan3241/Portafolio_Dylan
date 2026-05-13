import discord
from discord.ext import commands
from discord import app_commands
import datetime
import asyncio
import io


INACTIVITY_MINUTES = 30


# ================== CERRAR TICKET ==================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar ticket", style=discord.ButtonStyle.red, emoji="🔒")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):

        await interaction.response.send_message("🔒 Cerrando ticket...", ephemeral=True)

        await TicketUtils.close_ticket(
            interaction.channel,
            interaction.guild,
            interaction.user,
            "manual"
        )


# ================== UTILS ==================
class TicketUtils:

    @staticmethod
    async def generate_transcript(channel: discord.TextChannel):
        messages = [msg async for msg in channel.history(limit=200, oldest_first=True)]

        content = ""
        for msg in messages:
            time = msg.created_at.strftime("%Y-%m-%d %H:%M")
            content += f"[{time}] {msg.author}: {msg.content}\n"

        file = io.BytesIO(content.encode("utf-8"))
        return discord.File(file, filename=f"transcript-{channel.name}.txt")

    @staticmethod
    async def close_ticket(channel, guild, user, reason="auto", tipo="general"):

        canales = {
            "crear_cuenta": "📥・𝐥𝐨𝐠𝐬-𝐜𝐮𝐞𝐧𝐭𝐚𝐬",
            "prestamo": "💰・𝐥𝐨𝐠𝐬-𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬",
            "pago": "📤・𝐥𝐨𝐠𝐬-𝐩𝐚𝐠𝐨𝐬"
        }

        canal_nombre = canales.get(tipo, "🧾・logs-aurum")

        log_channel = discord.utils.get(guild.text_channels, name=canal_nombre)

        transcript = await TicketUtils.generate_transcript(channel)

        if log_channel:
            await log_channel.send(
                content=(
                    f"🔒 Ticket cerrado ({reason})\n"
                    f"📁 Canal: {channel.name}\n"
                    f"👤 Cerrado por: {user}"
                ),
                file=transcript
            )

        await channel.delete()


# ================== PANEL ==================
class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def crear_ticket(self, interaction, tipo):

        guild = interaction.guild
        user = interaction.user

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True)
        }

        channel = await guild.create_text_channel(
            name=f"{tipo}-{user.name}".lower(),
            overwrites=overwrites
        )

        embed = discord.Embed(
            title="🏦 AURUM BANK • TICKET ABIERTO",
            color=0x2ECC71
        )

        if tipo == "crear_cuenta":
            embed.description = (
                "🪙 **CREAR CUENTA BANCARIA**\n\n"
                "📌 Para procesar tu cuenta debes enviar:\n\n"
                "• Nombre IC\n"
                "• Edad IC\n"
                "• Número de DNI\n"
                "• Foto del DNI\n\n"
                "⚠️ Sin estos datos no se podrá crear la cuenta."
            )

        elif tipo == "prestamo":
            embed.description = (
                "💸 **SOLICITUD DE PRÉSTAMO**\n\n"
                "📌 Debes enviar:\n\n"
                "• Nombre IC\n"
                "• Edad IC\n"
                "• DNI + foto\n"
                "• Motivo del préstamo\n"
                "• Monto solicitado\n\n"
                "⚠️ El préstamo será evaluado por el staff."
            )

        elif tipo == "pago":
            embed.description = (
                "💰 **PAGO DE PRÉSTAMO**\n\n"
                "📌 Debes enviar:\n\n"
                "• Nombre IC\n"
                "• Qué préstamo estás pagando\n"
                "• Monto a pagar\n\n"
                "⚠️ El pago será registrado por el banco."
            )

        else:
            embed.description = (
                "📊 **CONSULTA BANCARIA**\n\n"
                "📌 Escribe tu consulta o problema.\n"
                "Un staff te atenderá pronto."
            )

        role = discord.utils.get(guild.roles, name="𝐀𝐠𝐞𝐧𝐭𝐞 Bancario")

        content = user.mention

        if role:
            content = f"{role.mention} {user.mention}"

        await channel.send(
            content=content,
            embed=embed,
            view=CloseTicketView()
        )

        await interaction.response.send_message(
            f"🎫 Ticket creado: {channel.mention}",
            ephemeral=True
        )

    @discord.ui.button(label="Crear cuenta", style=discord.ButtonStyle.green, emoji="🪙")
    async def crear_cuenta(self, interaction, button):
        await self.crear_ticket(interaction, "crear_cuenta")

    @discord.ui.button(label="Pedir préstamo", style=discord.ButtonStyle.blurple, emoji="💸")
    async def prestamo(self, interaction, button):
        await self.crear_ticket(interaction, "prestamo")

    @discord.ui.button(label="Pagar préstamo", style=discord.ButtonStyle.red, emoji="💰")
    async def pago(self, interaction, button):
        await self.crear_ticket(interaction, "pago")

    @discord.ui.button(label="Ver préstamo", style=discord.ButtonStyle.gray, emoji="📊")
    async def ver(self, interaction, button):
        await self.crear_ticket(interaction, "ver")


# ================== COG ==================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_activity = {}

    @app_commands.command(name="panel_tickets", description="Enviar panel de tickets")
    async def panel_tickets(self, interaction: discord.Interaction):

        embed = discord.Embed(
            title="🏦 AURUM BANK • SISTEMA DE TICKETS",
            description=(
                "🪙 Crear cuenta → abrir cuenta bancaria\n"
                "💸 Préstamo → solicitar dinero\n"
                "💰 Pagar → liquidar deuda\n"
                "📊 Ver → estado de cuenta"
            ),
            color=0x2ECC71
        )

        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Panel enviado", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):

        if message.author.bot:
            return

        if "ticket-" in message.channel.name:
            self.last_activity[message.channel.id] = datetime.datetime.utcnow()


# ================== AUTO CLOSE ==================
async def auto_close_loop(bot):

    await bot.wait_until_ready()

    while not bot.is_closed():

        await asyncio.sleep(60)

        for guild in bot.guilds:
            for channel in guild.text_channels:

                if "ticket-" in channel.name:

                    last = bot.get_cog("Tickets").last_activity.get(channel.id)

                    if last:
                        diff = (datetime.datetime.utcnow() - last).total_seconds() / 60

                        if diff >= INACTIVITY_MINUTES:
                            await TicketUtils.close_ticket(
                                channel,
                                guild,
                                bot.user,
                                "inactividad"
                            )


async def setup(bot):
    await bot.add_cog(Tickets(bot))
    bot.loop.create_task(auto_close_loop(bot))
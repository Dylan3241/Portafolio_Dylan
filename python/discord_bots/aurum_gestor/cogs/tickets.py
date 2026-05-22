import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import asyncio
import io

# --- CONFIGURACIÓN ---
INACTIVITY_MINUTES = 1440
ID_CATEGORIA_TICKETS = 1499627048317222912 

# ================== UTILS ==================
class TicketUtils:
    @staticmethod
    async def generate_transcript(channel: discord.TextChannel):
        messages = [msg async for msg in channel.history(limit=500, oldest_first=True)]
        content = f"--- TRANSCRIPT DE {channel.name.upper()} ---\n"
        content += f"Aurum Bank - Registro Oficial\n"
        content += f"Cerrado el: {datetime.datetime.now().strftime('%d/%m/%Y %H:%M')}\n"
        content += "------------------------------------------\n\n"
        
        for msg in messages:
            time_str = msg.created_at.strftime("%Y-%m-%d %H:%M")
            content += f"[{time_str}] {msg.author}: {msg.content}\n"
            if msg.attachments:
                for att in msg.attachments:
                    content += f" > Archivo adjunto: {att.url}\n"

        file_bytes = io.BytesIO(content.encode("utf-8"))
        file_bytes.seek(0)
        return discord.File(file_bytes, filename=f"transcript-{channel.name}.txt")

    @staticmethod
    async def close_ticket(channel, guild, user, reason="manual"):
        NOMBRE_LOG_CENTRAL = "🧾・logs-aurum"
        log_channel = discord.utils.get(guild.text_channels, name=NOMBRE_LOG_CENTRAL)
        transcript = await TicketUtils.generate_transcript(channel)

        if log_channel:
            embed = discord.Embed(
                title="🔒 Ticket Archivado",
                description=f"Se ha cerrado y generado el reporte del canal `{channel.name}`.",
                color=0x2B2D31,
                timestamp=datetime.datetime.now()
            )
            embed.add_field(name="👤 Cerrado por", value=user.mention if hasattr(user, 'mention') else f"{user}", inline=True)
            embed.add_field(name="📝 Motivo", value=reason, inline=True)
            embed.set_footer(text="Aurum Bank - Sistema de Seguridad")
            await log_channel.send(embed=embed, file=transcript)
        else:
            print(f"❌ ERROR: No se encontró el canal '{NOMBRE_LOG_CENTRAL}'.")

        await channel.delete()

# ================== VISTAS ==================
class CloseTicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Cerrar ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_message("🔒 Cerrando ticket en unos segundos...", ephemeral=True)
        await TicketUtils.close_ticket(interaction.channel, interaction.guild, interaction.user, "manual")

class TicketPanelView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def crear_ticket(self, interaction: discord.Interaction, tipo: str):
        guild = interaction.guild
        user = interaction.user

        # Evitar duplicados
        existing = discord.utils.get(guild.text_channels, name=f"{tipo}-{user.name}".lower()[:32])
        if existing:
            return await interaction.response.send_message(f"❌ Ya tienes un ticket abierto aquí: {existing.mention}", ephemeral=True)

        # 1. Permisos base
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            user: discord.PermissionOverwrite(view_channel=True, send_messages=True, attach_files=True, embed_links=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # 2. Definición de Roles
        role_agente = discord.utils.get(guild.roles, name="𝐀𝐠𝐞𝐧𝐭𝐞 Bancario")
        role_cobrador = discord.utils.get(guild.roles, name="Cobrador")
        role_seguridad = discord.utils.get(guild.roles, name="Seguridad Financiera")
        role_gerente_pres = discord.utils.get(guild.roles, name="𝐆𝐞𝐫𝐞𝐧𝐭𝐞 de Préstamos")

        # 3. Lógica de visibilidad 
        if role_seguridad:
            overwrites[role_seguridad] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        if tipo == "crear_cuenta":
            if role_agente: overwrites[role_agente] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        elif tipo == "prestamo":
            if role_agente: overwrites[role_agente] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
            if role_gerente_pres: overwrites[role_gerente_pres] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        elif tipo == "ver":
            if role_agente: overwrites[role_agente] = discord.PermissionOverwrite(view_channel=True, send_messages=True)
        elif tipo == "deposito_retiro":
            if role_agente: overwrites[role_agente] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        categoria = guild.get_channel(ID_CATEGORIA_TICKETS)
        channel = await guild.create_text_channel(
            name=f"{tipo}-{user.name}".lower()[:32],
            overwrites=overwrites,
            category=categoria
        )

        embed = discord.Embed(title="🏦 AURUM BANK • TICKET ABIERTO", color=0xD4AF37)
        descripciones = {
            "crear_cuenta": "🪙 **CREAR CUENTA BANCARIA**\n\n📌 Envía:\n• Nombre Completo\n• Edad IC\n• Número de DNI\n• Foto del DNI\n ⚠️ Sin esto no hay cuenta.",
            "prestamo": "💸 **SOLICITUD DE PRÉSTAMO**\n\n📌 Envía:\n• Nombre Completo\n• Número de DNI\n• Foto del DNI\n• Motivo\n• Monto",
            "ver": "📊 **CONSULTA BANCARIA**\n\n📌 Un agente revisará tu estado de cuenta.",
            "deposito_retiro": "💼 **MÓDULO DE DEPÓSITO / RETIRO**\n\n📌 Por favor especifica:\n• Tipo de transacción (Depósito o Retiro)\n• Monto exacto en efectivo\n• Captura de pantalla de la entrega física si aplica.\n\n⚠️ *Un Agente Bancario procesará tu solicitud de inmediato.*"
        }
        embed.description = descripciones.get(tipo, "Consulta general.")
        
        # Mención dinámica para avisar al personal
        mentions = f"{user.mention}"
        if tipo in ["crear_cuenta", "prestamo", "ver", "deposito_retiro"] and role_agente: mentions += f" {role_agente.mention}"
        if tipo in ["prestamo"] and role_gerente_pres: mentions += f" {role_gerente_pres.mention}"

        await channel.send(content=mentions, embed=embed, view=CloseTicketView())
        await interaction.response.send_message(f"🎫 Ticket creado: {channel.mention}", ephemeral=True)

    # 1. Crear cuenta
    @discord.ui.button(label="Crear cuenta", style=discord.ButtonStyle.green, emoji="🪙", custom_id="tk_cuenta")
    async def btn_cuenta(self, it, bt): await self.crear_ticket(it, "crear_cuenta")

    # 2. Pedir préstamo (Crear préstamo)
    @discord.ui.button(label="Pedir préstamo", style=discord.ButtonStyle.blurple, emoji="💸", custom_id="tk_pres")
    async def btn_pres(self, it, bt): await self.crear_ticket(it, "prestamo")

    # 3. Depósito/Retiro (Exclusivo para Agentes Bancarios)
    @discord.ui.button(label="Depósito/Retiro", style=discord.ButtonStyle.green, emoji="💼", custom_id="tk_deposito")
    async def btn_deposito(self, it, bt):
        role_agente = discord.utils.get(it.guild.roles, name="𝐀𝐠𝐞𝐧𝐭𝐞 Bancario")
        if role_agente not in it.user.roles:
            return await it.response.send_message("❌ **Acceso Restringido:** Solo los usuarios con el rol de **💡 𝐀𝐠𝐞𝐧𝐭𝐞 Bancario** pueden iniciar este trámite.", ephemeral=True)
        
        await self.crear_ticket(it, "deposito_retiro")
    
    # 4. Ver préstamo
    @discord.ui.button(label="Ver préstamo", style=discord.ButtonStyle.gray, emoji="📊", custom_id="tk_ver")
    async def btn_ver(self, it, bt): await self.crear_ticket(it, "ver")


# ================== COG ==================
class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.last_activity = {}

    @app_commands.command(name="panel_tickets", description="Enviar panel de tickets de Aurum Bank")
    async def panel_tickets(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        embed = discord.Embed(
            title="🏦 AURUM BANK • SERVICIOS",
            description="""
            🪙 **Crear cuenta** → Abrir cuenta bancaria oficial
            💸 **Préstamo** → Solicitar capital financiero
            💼 **Depósito/Retiro** → Gestión de divisas
            📊 **Ver** → Consultar estados de cuenta
            """,
            color=0x2ECC71
        )
        embed.set_thumbnail(url="https://i.imgur.com/TGUHiux.png")
        await interaction.channel.send(embed=embed, view=TicketPanelView())
        await interaction.response.send_message("✅ Panel de Aurum configurado.", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot: return
        if any(x in message.channel.name for x in ["crear_cuenta-", "prestamo-", "ver-", "deposito_retiro-"]):
            self.last_activity[message.channel.id] = datetime.datetime.now(datetime.timezone.utc)

# ================== AUTO CLOSE ==================
async def auto_close_loop(bot):
    await bot.wait_until_ready()
    while not bot.is_closed():
        await asyncio.sleep(60)
        cog = bot.get_cog("Tickets")
        if not cog: continue

        ahora = datetime.datetime.now(datetime.timezone.utc)
        for channel_id in list(cog.last_activity.keys()):
            last = cog.last_activity[channel_id]
            diff = (ahora - last).total_seconds() / 60

            if diff >= INACTIVITY_MINUTES:
                channel = bot.get_channel(channel_id)
                if channel:
                    await TicketUtils.close_ticket(channel, channel.guild, "Sistema (Inactividad)", "inactividad")
                if channel_id in cog.last_activity:
                    del cog.last_activity[channel_id]

async def setup(bot):
    await bot.add_cog(Tickets(bot))
    if not hasattr(bot, 'auto_close_task'):
        bot.auto_close_task = bot.loop.create_task(auto_close_loop(bot))
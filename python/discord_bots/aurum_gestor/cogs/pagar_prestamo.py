import discord
from discord.ext import commands
from discord import app_commands
import sqlite3
import datetime

ROLES_PERMITIDOS = [
    "𝐂𝐄𝐎 | Director General",
    "𝐂𝐅𝐎 | Director Financiero",
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]

# ID del canal donde estará el panel visual de préstamos activos
CANAL_PANEL_ID = 1498698092856217672

# URL del logo de Aurum Bank
LOGO_URL = "https://i.imgur.com/TGUHiux.png"


class Pagos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= ON READY: PANEL AL INICIAR =================
    @commands.Cog.listener()
    async def on_ready(self):
        """Al encender el bot, actualiza el panel en todos los servidores"""
        print("[Pagos] Bot listo — actualizando panel visual...")
        for guild in self.bot.guilds:
            try:
                await self.actualizar_panel_visual(guild)
            except Exception as e:
                print(f"[Pagos] Error actualizando panel en {guild.name}: {e}")
        print("[Pagos] Panel visual actualizado.")

    # ================= PANEL VISUAL =================
    async def actualizar_panel_visual(self, guild):
        """Actualiza el panel de cartera borrando el mensaje anterior y enviando uno nuevo"""
        channel = guild.get_channel(CANAL_PANEL_ID)
        if not channel:
            return

        self.cursor.execute("""
            SELECT p.user_id, p.id, p.total_pagar, p.cuota_valor, p.fecha_limite, p.estado,
                   c.numero_cuenta
            FROM prestamos p
            LEFT JOIN clientes c ON c.user_id = p.user_id
            WHERE p.estado IN ('activo', 'mora', 'congelado')
            ORDER BY p.id ASC
        """)
        prestamos_activos = self.cursor.fetchall()

        # ── EMBED CABECERA ──────────────────────────────────────────
        embed_header = discord.Embed(
            description="```\nAURUM BANK • CARTERA DE CLIENTES ACTIVOS\n```",
            color=0xd4af37
        )
        embed_header.set_author(
            name="🏛️   AURUM BANK  •  CENTRAL DE CRÉDITOS",
            icon_url=LOGO_URL
        )
        embed_header.set_thumbnail(url=LOGO_URL)
        
        fecha_actual = datetime.datetime.now().strftime('%d/%m/%Y %H:%M')
        embed_header.set_footer(
            text=f"Aurum Bank Certificado  •  Actualizado: {fecha_actual}",
            icon_url=LOGO_URL
        )

        if not prestamos_activos:
            embed_header.add_field(
                name="📭  CARTERA VACÍA",
                value="No hay préstamos activos ni en mora en este momento.",
                inline=False
            )
            await self._borrar_panel(channel)
            await channel.send(embed=embed_header)
            return

        # ── UN EMBED POR CLIENTE ────────────────────────────────────
        embeds = [embed_header]

        for p in prestamos_activos:
            u_id, p_id, total, cuota, vence, estado, numero_cuenta = p

            member = guild.get_member(u_id)
            nombre = member.display_name if member else f"ID: {u_id}"
            mention = member.mention if member else f"<@{u_id}>"

            if numero_cuenta is not None:
                if isinstance(numero_cuenta, str) and "AUR-" in numero_cuenta:
                    cuenta_str = numero_cuenta
                else:
                    try:
                        cuenta_str = f"AUR-{int(numero_cuenta):06d}"
                    except (ValueError, TypeError):
                        cuenta_str = str(numero_cuenta)
            else:
                cuenta_str = "—"

            p_id_int    = int(p_id)
            total_int   = int(total)
            cuota_int   = int(cuota)

            try:
                fecha_limpia = str(vence).replace("T", " ").strip()
                if " " in fecha_limpia:
                    fecha_obj = datetime.datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")
                else:
                    fecha_obj = datetime.datetime.strptime(fecha_limpia, "%Y-%m-%d")
                vence_bonito = fecha_obj.strftime("%d/%m/%Y %H:%M:%S")
            except:
                vence_bonito = vence

            # Cambiar el diseño del estado dinámicamente según la salud de la cuenta
            if estado == "mora":
                status_indicator = "🔴 **EN MORA (PENALIZADO)**"
                card_color = 0xE74C3C  
                
            elif estado == "congelado":
                status_indicator = "🔵 **PRESTAMO CONGELADO**"
                card_color = 0x5DADE2 
                
            else:
                status_indicator = "🟢 **AL DÍA**"
                card_color = 0x1a1a2e  

            embed_cliente = discord.Embed(color=card_color)
            embed_cliente.add_field(
                name=f"👤  Cliente: {nombre}",
                value=(
                    f"🪪 **Cuenta Cliente:** `{cuenta_str}`\n"
                    f"📋 **ID Préstamo:** `PREST-{p_id_int:06d}`\n"
                    f"{mention}  |  {status_indicator}\n"
                    f"💰 **Cuota:** `€{cuota_int:,}`  |  📉 **Deuda Total:** `€{total_int:,}`\n"
                    f"📅 **Vence:** `{vence_bonito}`\n"
                    f"{'─' * 36}"
                ),
                inline=False
            )
            embeds.append(embed_cliente)

        await self._borrar_panel(channel)

        chunk_size = 10
        for i in range(0, len(embeds), chunk_size):
            chunk = embeds[i:i + chunk_size]
            await channel.send(embeds=chunk)

    async def _borrar_panel(self, channel):
        """Borra todos los mensajes del panel anterior enviados por el bot de forma segura"""
        async for message in channel.history(limit=100):
            if message.author == self.bot.user and message.embeds:
                es_panel = False
                
                for embed in message.embeds:
                    if embed.description and "CARTERA DE CLIENTES ACTIVOS" in embed.description:
                        es_panel = True
                        break
                    if embed.author and embed.author.name and "CENTRAL DE CRÉDITOS" in embed.author.name:
                        es_panel = True
                        break
                    if embed.fields:
                        for field in embed.fields:
                            if "Cliente:" in field.name or "Cuenta Cliente:" in field.value:
                                es_panel = True
                                break
                    if es_panel:
                        break

                if es_panel:
                    try:
                        await message.delete()
                    except (discord.Forbidden, discord.HTTPException):
                        pass

    # ================= COMMAND: RECORDATORIO =================
    @app_commands.command(name="recordatorio", description="Enviar aviso de vencimiento a un cliente")
    @app_commands.describe(usuario="Cliente a recordar")
    async def recordatorio(self, interaction: discord.Interaction, usuario: discord.Member):
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        # Buscamos tanto préstamos activos como en mora para poder alertar de igual forma
        self.cursor.execute(
            "SELECT id, cuota_valor, fecha_limite, estado FROM prestamos WHERE user_id = ? AND estado IN ('activo', 'mora')",
            (usuario.id,)
        )
        data = self.cursor.fetchone()

        if not data:
            return await interaction.response.send_message("❌ Este usuario no tiene préstamos pendientes.", ephemeral=True)

        p_id, cuota, vence, estado = data

        try:
            fecha_limpia = str(vence).replace("T", " ").strip()
            if " " in fecha_limpia:
                fecha_obj = datetime.datetime.strptime(fecha_limpia, "%Y-%m-%d %H:%M:%S")
            else:
                fecha_obj = datetime.datetime.strptime(fecha_limpia, "%Y-%m-%d")
            vence_recordatorio = fecha_obj.strftime("%d/%m/%Y %H:%M:%S")
        except:
            vence_recordatorio = vence

        embed = discord.Embed(title="⚠️ Aviso de Cuota: " + usuario.display_name, color=0x000000)
        embed.set_author(name="AURUM BANK • AVISO DE VENCIMIENTO", icon_url=LOGO_URL)
        
        if estado == "mora":
            embed.description = (
                f"Estimado/a {usuario.mention}, le notificamos que su crédito se encuentra **VENCIDO**.\n\n"
                f"🆔 **ID de Préstamo:** `#{p_id}`\n"
                f"🚨 **Saldo en Mora:** `€{int(cuota):,}`\n"
                f"📅 **Fecha Límite Pasada:** `{vence_recordatorio}`\n\n"
                f"❌ *Su cuenta ya ha sido penalizada con recargos financieros recurrentes y estatus en Blacklist.*"
            )
        else:
            embed.description = (
                f"Estimado/a {usuario.mention}, le recordamos el cumplimiento de su cuota, "
                f"según se estipuló en el contrato firmado.\n\n"
                f"🆔 **ID de Préstamo:** `#{p_id}`\n"
                f"💵 **Cuota a Pagar:** `€{int(cuota):,}`\n"
                f"📅 **Fecha Límite:** `{vence_recordatorio}`\n\n"
                f"📜 **Cláusula Contractual**\n"
                f"*El incumplimiento del pago activará automáticamente la **cláusula de mora (5% de recargo)**.*\n\n"
                f"Solicite su comprobante al finalizar el pago en caja."
            )
            
        embed.set_thumbnail(url=LOGO_URL)
        embed.set_footer(text="Aurum Gestor • Sistema de Créditos", icon_url=LOGO_URL)

        await interaction.response.send_message(content=f"{usuario.mention} ⚠️", embed=embed)

    # ================= PAGAR PRESTAMO =================
    @app_commands.command(name="pagar_prestamo", description="Registrar pago de préstamo específico")
    @app_commands.describe(
        usuario="Cliente", 
        id_prestamo="ID del préstamo (Ej: 3 o PREST-000003)", 
        monto="Cantidad a pagar"
    )
    async def pagar_prestamo(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member, 
        id_prestamo: str, 
        monto: int
    ):
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        clean_id = id_prestamo.upper().replace("PREST-", "")
        try:
            prestamo_id_int = int(clean_id)
        except ValueError:
            return await interaction.response.send_message("❌ Formato de ID de préstamo inválido. Usa el número o formato PREST-00000X.", ephemeral=True)

        self.cursor.execute(
            "SELECT id, total_pagar, cuota_valor FROM prestamos WHERE id = ? AND user_id = ? AND estado IN ('activo', 'mora')",
            (prestamo_id_int, usuario.id)
        )
        prestamo = self.cursor.fetchone()

        if not prestamo:
            return await interaction.response.send_message(f"❌ No se encontró ningún préstamo pendiente con el ID `PREST-{prestamo_id_int:06d}` para este usuario.", ephemeral=True)

        prestamo_id, total_pagar, cuota_valor = prestamo
        total_pagar = int(total_pagar)
        cuota_valor = int(cuota_valor)

        monto_real = min(monto, total_pagar)
        restante   = total_pagar - monto_real
        estado     = "pagado" if restante <= 0 else "activo"  # Al pagar la mora, regresa a estado activo si queda remanente

        nueva_fecha = None
        if estado == "activo":
            nueva_fecha = (datetime.datetime.now() + datetime.timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")

        vence_bonito = "—"
        if nueva_fecha:
            vence_bonito = datetime.datetime.strptime(nueva_fecha, "%Y-%m-%d %H:%M:%S").strftime("%d/%m/%Y %H:%M:%S")

        # 💾 Actualizar préstamo en la BD limpiando la mora si correspondiera
        self.cursor.execute(
            "UPDATE prestamos SET total_pagar = ?, estado = ?, fecha_limite = ? WHERE id = ?",
            (restante, estado, nueva_fecha, prestamo_id)
        )
        
        self.conn.commit()

        # Respuesta de confirmación
        embed = discord.Embed(title="💸 Pago registrado", color=0x2ecc71)
        embed.set_author(name="AURUM BANK • REGISTRO DE PAGO", icon_url=LOGO_URL)
        embed.add_field(name="👤 Cliente",  value=usuario.mention,    inline=False)
        embed.add_field(name="📋 Préstamo", value=f"`PREST-{prestamo_id:06d}`", inline=False)
        embed.add_field(name="💰 Pagado",   value=f"€{monto_real:,}", inline=True)
        embed.add_field(name="📉 Restante", value=f"€{restante:,}",   inline=True)
        if estado == "activo":
            embed.add_field(name="📅 Próxima cuota", value=vence_bonito, inline=False)
        else:
            embed.add_field(name="✅ Estado", value="Préstamo completamente pagado", inline=False)
        embed.set_footer(text="Aurum Gestor • Sistema de Créditos", icon_url=LOGO_URL)
        await interaction.response.send_message(embed=embed)

        #  Log
        log_channel = discord.utils.get(interaction.guild.text_channels, name="📤・𝐥𝐨𝐠𝐬-𝐩𝐚𝐠𝐨𝐬")
        if log_channel:
            log_emb = discord.Embed(title="📤 Pago Procesado", color=0x3498db)
            log_emb.set_author(name="AURUM BANK • LOGS DE PAGOS", icon_url=LOGO_URL)
            log_emb.add_field(name="Staff",          value=interaction.user.mention)
            log_emb.add_field(name="Cliente",        value=usuario.mention)
            log_emb.add_field(name="ID Préstamo",    value=f"`PREST-{prestamo_id:06d}`")
            log_emb.add_field(name="Monto",          value=f"€{monto_real:,}")
            log_emb.add_field(name="Deuda restante", value=f"€{restante:,}")
            if nueva_fecha:
                log_emb.add_field(name="Próxima cuota", value=vence_bonito)
            await log_channel.send(embed=log_emb)

        # MD al cliente
        try:
            dm_emb = discord.Embed(title="🏦 Aurum Bank - Recibo de Pago", color=0x3498db)
            dm_emb.set_author(name="AURUM BANK • RECIBO", icon_url=LOGO_URL)
            dm_emb.description = (
                f"Se ha registrado su pago de **€{monto_real:,}** para el préstamo `PREST-{prestamo_id:06d}`.\n"
                f"Deuda restante: **€{restante:,}**."
            )
            if estado == "activo":
                dm_emb.add_field(name="📅 Próxima cuota", value=vence_bonito)
            else:
                dm_emb.add_field(name="✅ Estado", value="Su préstamo ha sido saldado. ¡Gracias!")
            dm_emb.set_footer(text="Aurum Bank", icon_url=LOGO_URL)
            await usuario.send(dm_emb)
        except:
            pass

        # Actualizar panel visual de inmediato
        await self.actualizar_panel_visual(interaction.guild)


async def setup(bot):
    await bot.add_cog(Pagos(bot))
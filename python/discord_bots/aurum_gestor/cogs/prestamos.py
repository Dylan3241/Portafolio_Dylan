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

LIMITES = {
    "basica": 100000,
    "premium": 250000,
    "vip": 400000
}

INTERESES = {
    "basica": 0.20,
    "premium": 0.15,
    "vip": 0.10
}

MAX_PRESTAMOS = {
    "basica": 1,
    "premium": 2,
    "vip": 3
}

# Definición global del logo para evitar errores en los embeds
LOGO_URL = "https://i.imgur.com/TGUHiux.png"


class Prestamos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= CREAR PRESTAMO =================
    @app_commands.command(name="crear_prestamo", description="Crear un préstamo")
    @app_commands.describe(
        usuario="Cliente",
        nombre_ic="Nombre completo del cliente (para el contrato)",
        dni="DNI o identificación del cliente",
        monto="Cantidad de dinero a prestar",
        cuotas="Número de cuotas para devolver el préstamo",
        contrato="Adjunta el PDF del contrato firmado"
    )
    @app_commands.choices(cuotas=[
        app_commands.Choice(name="3 cuotas",  value=3),
        app_commands.Choice(name="6 cuotas",  value=6),
        app_commands.Choice(name="12 cuotas", value=12),
    ])
    async def crear_prestamo(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        nombre_ic: str,
        dni: str,
        monto: int,
        cuotas: int,
        contrato: discord.Attachment
    ):
        #  Permisos
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
            return

        #  Validar que el adjunto sea un PDF
        if not contrato.filename.lower().endswith(".pdf"):
            await interaction.response.send_message(
                "❌ El contrato debe ser un archivo PDF.",
                ephemeral=True
            )
            return

        await interaction.response.defer()

        #  Ver cliente
        self.cursor.execute("SELECT saldo, rol FROM clientes WHERE user_id = ?", (usuario.id,))
        cliente = self.cursor.fetchone()

        if not cliente:
            await interaction.followup.send("❌ El usuario no tiene cuenta.", ephemeral=True)
            return

        saldo, tipo = cliente

        #  Validar límite
        if monto > LIMITES[tipo]:
            await interaction.followup.send(
                f"❌ Supera el límite de {tipo.upper()} (€{LIMITES[tipo]:,})",
                ephemeral=True
            )
            return

        # Validar préstamos activos
        self.cursor.execute(
            "SELECT COUNT(*) FROM prestamos WHERE user_id = ? AND TRIM(LOWER(estado)) = 'activo'",
            (usuario.id,)
        )
        activos = self.cursor.fetchone()[0]

        if activos >= MAX_PRESTAMOS[tipo]:
            await interaction.followup.send(
                "❌ Ya alcanzó el máximo de préstamos activos.",
                ephemeral=True
            )
            return

        #  Calcular interés, total y cuota
        interes = INTERESES[tipo]
        interes_pct = int(interes * 100)
        total = int(monto + (monto * interes))
        cuota_valor = total // cuotas

        # Primera fecha límite: 1 semana desde hoy (Formato unificado)
        fecha_limite = datetime.datetime.now() + datetime.timedelta(days=7)
        
        fecha_limite_bd = fecha_limite.strftime("%Y-%m-%d %H:%M:%S")
        
        # Formato visual para los Embeds de Discord (Día/Mes/Año)
        fecha_visual_embed = fecha_limite.strftime("%d/%m/%Y %H:%M:%S")

        # 💾 Guardar préstamo en la BD con el nuevo formato de fecha estable
        self.cursor.execute(
            """INSERT INTO prestamos
               (user_id, monto, intereses, total_pagar, cuota_valor, estado, fecha_limite)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (usuario.id, monto, interes, total, cuota_valor, "activo", fecha_limite_bd)
        )
        
        # Sumar el monto aprobado al saldo del cliente
        self.cursor.execute(
            "UPDATE clientes SET saldo = saldo + ? WHERE user_id = ?",
            (monto, usuario.id)
        )
        
        self.conn.commit()

        #  Descargar el PDF adjunto
        pdf_bytes = await contrato.read()

        #  Embed confirmación en el canal
        embed = discord.Embed(title="💸 Préstamo aprobado", color=0x2ECC71)
        embed.add_field(name="👤 Cliente",          value=f"{usuario.mention}\n`{nombre_ic}`", inline=False)
        embed.add_field(name="🪪 DNI",              value=f"`{dni}`",                          inline=True)
        embed.add_field(name="💰 Monto",            value=f"€{monto:,}",                       inline=True)
        embed.add_field(name="📈 Interés",          value=f"{interes_pct}%",                   inline=True)
        embed.add_field(name="💵 Total a pagar",    value=f"€{total:,}",                       inline=True)
        embed.add_field(name="🔢 Cuotas",           value=f"{cuotas} cuotas",                  inline=True)
        embed.add_field(name="🧾 Valor por cuota",  value=f"€{cuota_valor:,}",                 inline=True)
        embed.add_field(name="📅 Primera cuota",    value=fecha_visual_embed,                  inline=True)
        embed.set_footer(text="Aurum Bank • Cuotas subsiguientes cada 5 días tras cada pago")

        archivo_canal = discord.File(
            fp=__import__("io").BytesIO(pdf_bytes),
            filename=contrato.filename
        )
        await interaction.followup.send(embed=embed, file=archivo_canal)

        #  Log en canal con el PDF adjunto
        log_channel = discord.utils.get(
            interaction.guild.text_channels,
            name="💰・𝐥𝐨𝐠𝐬-𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬"
        )
        if log_channel:
            embed_log = discord.Embed(title="💰 Préstamo registrado", color=0x3498DB)
            embed_log.add_field(name="Staff",           value=interaction.user.mention)
            embed_log.add_field(name="Cliente",         value=f"{usuario.mention} — {nombre_ic}")
            embed_log.add_field(name="DNI",             value=dni)
            embed_log.add_field(name="Monto",           value=f"€{monto:,}")
            embed_log.add_field(name="Total + interés", value=f"€{total:,}")
            embed_log.add_field(name="Cuotas",          value=f"{cuotas} × €{cuota_valor:,}")
            embed_log.add_field(name="Primera cuota",   value=fecha_visual_embed)
            archivo_log = discord.File(
                fp=__import__("io").BytesIO(pdf_bytes),
                filename=contrato.filename
            )
            await log_channel.send(embed=embed_log, file=archivo_log)

        #  MD al cliente con el PDF adjunto
        try:
            dm_embed = discord.Embed(
                title="🏦 Préstamo aprobado",
                description="Tu solicitud de préstamo ha sido aprobada. Adjunto encontrarás el contrato.",
                color=0x2ECC71
            )
            dm_embed.add_field(name="💰 Monto",            value=f"€{monto:,}",       inline=True)
            dm_embed.add_field(name="📈 Interés",          value=f"{interes_pct}%",  inline=True)
            dm_embed.add_field(name="💵 Total a pagar",    value=f"€{total:,}",       inline=False)
            dm_embed.add_field(name="🔢 Cuotas",          value=f"{cuotas}",        inline=True)
            dm_embed.add_field(name="🧾 Valor por cuota", value=f"€{cuota_valor:,}", inline=True)
            dm_embed.add_field(name="📅 Primera cuota",    value=fecha_visual_embed,   inline=True)
            dm_embed.set_footer(text="Aurum Bank • Cuotas subsiguientes cada 5 días tras cada pago")

            archivo_dm = discord.File(
                fp=__import__("io").BytesIO(pdf_bytes),
                filename=contrato.filename
            )
            await usuario.send(embed=dm_embed, file=archivo_dm)
        except Exception:
            await interaction.followup.send(
                f"⚠️ No se pudo enviar MD a {usuario.mention}.",
                ephemeral=True
            )
            
    # ================= CONGELAR PRESTAMO =================
    @app_commands.command(name="congelar_prestamo", description="Congela un préstamo activo o en mora para pausar penalizaciones")
    @app_commands.describe(
        usuario="Cliente dueño del préstamo",
        id_prestamo="ID del préstamo (Ej: 3 o PREST-000003)",
        motivo="Razón por la cual se congela el crédito"
    )
    async def congelar_prestamo(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        id_prestamo: str,
        motivo: str
    ):
        #  Validación de Permisos de Staff
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)

        #  Limpieza del ID recibido
        clean_id = id_prestamo.upper().replace("PREST-", "")
        try:
            prestamo_id_int = int(clean_id)
        except ValueError:
            return await interaction.response.send_message("❌ Formato de ID inválido. Usa el número plano o el formato `PREST-00000X`.", ephemeral=True)

        #  Buscar el préstamo usando TRIM y LOWER para evitar fallos por espacios o mayúsculas
        self.cursor.execute(
            "SELECT id, total_pagar, cuota_valor, fecha_limite, estado, user_id FROM prestamos WHERE id = ?",
            (prestamo_id_int,)
        )
        data_db = self.cursor.fetchone()

        #  Sistema de Diagnóstico si no coincide la búsqueda exacta
        if not data_db:
            return await interaction.response.send_message(f"❌ El ID `PREST-{prestamo_id_int:06d}` ni siquiera existe en la base de datos.", ephemeral=True)
        
        p_id, total, cuota, vence, estado_actual, user_id_db = data_db
        estado_clean = estado_actual.strip().lower()

        # Validación cruzada de dueño
        if user_id_db != usuario.id:
            return await interaction.response.send_message(
                f"❌ Error de asignación: El préstamo `PREST-{p_id:06d}` no pertenece a {usuario.mention}.\n*(En la base de datos está asignado al ID de usuario: `{user_id_db}`)*", 
                ephemeral=True
            )

        # Validación de estado apto
        if estado_clean not in ['activo', 'mora']:
            return await interaction.response.send_message(
                f"❌ No se puede congelar. El préstamo se encuentra en estado: `{estado_actual.upper()}` (Solo se pueden congelar préstamos 'activo' o 'mora').", 
                ephemeral=True
            )

        ahora = datetime.datetime.now()

        #  Cambiar el estado a 'congelado' en la base de datos
        self.cursor.execute(
            "UPDATE prestamos SET estado = 'congelado' WHERE id = ?",
            (p_id,)
        )
        self.conn.commit()

        # Respuesta de éxito en el canal al Staff
        embed_staff = discord.Embed(
            title="🧊 Préstamo Congelado Exitosamente",
            description=f"El préstamo `PREST-{p_id:06d}` ha sido pausado. El sistema automático de morosos no aplicará recargos.",
            color=0x3498DB
        )
        embed_staff.add_field(name="👤 Cliente", value=usuario.mention, inline=True)
        embed_staff.add_field(name="💰 Deuda Congelada", value=f"€{int(total):,}", inline=True)
        embed_staff.add_field(name="📝 Motivo", value=motivo, inline=False)
        embed_staff.set_footer(text="Aurum Bank", icon_url=LOGO_URL)
        
        await interaction.response.send_message(embed=embed_staff)

        # Registro oficial en el canal especializado: 🧊・𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬-𝐜𝐨𝐧𝐠𝐞𝐥𝐚𝐝𝐨𝐬
        log_channel = discord.utils.get(interaction.guild.text_channels, name="🧊・𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬-𝐜𝐨𝐧𝐠𝐞𝐥𝐚𝐝𝐨𝐬")
        if log_channel:
            embed_log = discord.Embed(title="🧊 REGISTRO DE CRÉDITO CONGELADO", color=0x5DADE2, timestamp=ahora)
            embed_log.set_author(name="AURUM BANK • DEPARTAMENTO DE RIESGOS", icon_url=LOGO_URL)
            embed_log.add_field(name="💼 Staff Responsable", value=interaction.user.mention, inline=True)
            embed_log.add_field(name="👤 Cliente Afectado", value=usuario.mention, inline=True)
            embed_log.add_field(name="📋 ID Préstamo", value=f"`PREST-{p_id:06d}`", inline=True)
            embed_log.add_field(name="💰 Saldo en Pausa", value=f"€{int(total):,}", inline=True)
            embed_log.add_field(name="📉 Estado Anterior", value=f"`{estado_actual.upper()}`", inline=True)
            embed_log.add_field(name="📝 Motivo de la Congelación", value=f"```\n{motivo}\n```", inline=False)
            embed_log.set_thumbnail(url=LOGO_URL)
            embed_log.set_footer(text="Central de Créditos Aurum", icon_url=LOGO_URL)
            
            await log_channel.send(embed=embed_log)

        # Notificación formal al MD del cliente
        try:
            embed_dm = discord.Embed(
                title="🧊 NOTIFICACIÓN DE MORATORIA / CONGELACIÓN",
                description="Le informamos que la dirección de Aurum Bank ha congelado temporalmente su préstamo activo.",
                color=0x5DADE2,
                timestamp=ahora
            )
            embed_dm.set_author(name="AURUM BANK • CONTROL DE CUENTAS", icon_url=LOGO_URL)
            embed_dm.add_field(name="📋 Código de Crédito", value=f"`PREST-{p_id:06d}`", inline=True)
            embed_dm.add_field(name="💰 Deuda Remanente", value=f"€{int(total):,}", inline=True)
            embed_dm.add_field(name="🛡️ Beneficio", value="Los recargos del 5% e intereses recurrentes de mora quedan suspendidos por completo de forma temporal.", inline=False)
            embed_dm.add_field(name="💬 Justificación Oficial", value=motivo, inline=False)
            embed_dm.set_footer(text="Póngase en contacto con un agente bancario para reactivar su plan de pagos regular.")
            
            await usuario.send(embed=embed_dm)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ El préstamo se congeló correctamente, pero no se pudo notificar a {usuario.mention} porque tiene los mensajes privados cerrados.", ephemeral=True)

        # Actualizar el panel visual automáticamente si la Cog de Pagos está activa
        pagos_cog = self.bot.get_cog("Pagos")
        if pagos_cog:
            try:
                await pagos_cog.actualizar_panel_visual(interaction.guild)
            except Exception as e:
                print(f"Error al actualizar panel visual desde congelar: {e}")
                
 
    # ================= ACTIVAR PRESTAMO =================
    @app_commands.command(name="activar_prestamo", description="Reactiva un préstamo que estaba congelado")
    @app_commands.describe(
        usuario="Cliente dueño del préstamo",
        id_prestamo="ID del préstamo (Ej: 3 o PREST-000003)",
        motivo="Razón por la cual se descongela y reactiva el crédito"
    )
    async def activar_prestamo(
        self,
        interaction: discord.Interaction,
        usuario: discord.Member,
        id_prestamo: str,
        motivo: str
    ):
        # Permisos
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)

        clean_id = id_prestamo.upper().replace("PREST-", "")
        try:
            prestamo_id_int = int(clean_id)
        except ValueError:
            return await interaction.response.send_message("❌ Formato de ID inválido. Usa el número o el formato `PREST-00000X`.", ephemeral=True)

        # Buscar el préstamo evaluando posibles inconsistencias de texto
        self.cursor.execute(
            "SELECT id, total_pagar, cuota_valor, estado, user_id FROM prestamos WHERE id = ?",
            (prestamo_id_int,)
        )
        data_db = self.cursor.fetchone()

        if not data_db:
            return await interaction.response.send_message(f"❌ El ID `PREST-{prestamo_id_int:06d}` no existe en los registros.", ephemeral=True)

        p_id, total, cuota, estado_actual, user_id_db = data_db
        estado_clean = estado_actual.strip().lower()

        # Validación cruzada de dueño
        if user_id_db != usuario.id:
            return await interaction.response.send_message(
                f"❌ Error de asignación: El préstamo `PREST-{p_id:06d}` no le pertenece a {usuario.mention}.", 
                ephemeral=True
            )

        # Validación de que realmente esté congelado
        if estado_clean != 'congelado':
            return await interaction.response.send_message(
                f"❌ Este préstamo no se puede activar porque actualmente no está congelado (Su estado es: `{estado_actual.upper()}`).", 
                ephemeral=True
            )

        ahora = datetime.datetime.now()

        # Calcular nueva fecha de vencimiento (Le otorgamos 5 días nuevos de margen desde hoy)
        nueva_fecha_limite = ahora + datetime.timedelta(days=5)
        nueva_fecha_bd = nueva_fecha_limite.strftime("%Y-%m-%d %H:%M:%S")
        fecha_visual = nueva_fecha_limite.strftime("%d/%m/%Y %H:%M:%S")

        # Actualizar la Base de datos pasando el estado a 'activo' y fijando la nueva fecha
        self.cursor.execute(
            "UPDATE prestamos SET estado = 'activo', fecha_limite = ? WHERE id = ?",
            (nueva_fecha_bd, p_id)
        )
        self.conn.commit()

        # Respuesta de éxito en el canal al Staff
        embed_staff = discord.Embed(
            title="🔥 Préstamo Reactivado Exitosamente",
            description=f"El préstamo `PREST-{p_id:06d}` ha vuelto al flujo regular. Se le han otorgado 5 días de margen al cliente.",
            color=0x2ECC71
        )
        embed_staff.add_field(name="👤 Cliente", value=usuario.mention, inline=True)
        embed_staff.add_field(name="📅 Próximo Vence", value=fecha_visual, inline=True)
        embed_staff.add_field(name="📝 Motivo Reactivación", value=motivo, inline=False)
        embed_staff.set_footer(text="Aurum Bank", icon_url=LOGO_URL)
        await interaction.response.send_message(embed=embed_staff)

        # Registro oficial en el mismo canal: 🧊・𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬-𝐜𝐨𝐧𝐠𝐞𝐥𝐚𝐝𝐨𝐬
        log_channel = discord.utils.get(interaction.guild.text_channels, name="🧊・𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬-𝐜𝐨𝐧𝐠𝐞𝐥𝐚𝐝𝐨𝐬")
        if log_channel:
            embed_log = discord.Embed(title="🔥 REGISTRO DE CRÉDITO REACTIVADO", color=0x2ECC71, timestamp=ahora)
            embed_log.set_author(name="AURUM BANK • CENTRAL DE CRÉDITOS", icon_url=LOGO_URL)
            embed_log.add_field(name="💼 Staff Responsable", value=interaction.user.mention, inline=True)
            embed_log.add_field(name="👤 Cliente", value=usuario.mention, inline=True)
            embed_log.add_field(name="📋 ID Préstamo", value=f"`PREST-{p_id:06d}`", inline=True)
            embed_log.add_field(name="💰 Deuda Activa", value=f"€{int(total):,}", inline=True)
            embed_log.add_field(name="📅 Nuevo Vencimiento", value=fecha_visual, inline=True)
            embed_log.add_field(name="📝 Motivo del Alta", value=f"```\n{motivo}\n```", inline=False)
            embed_log.set_thumbnail(url=LOGO_URL)
            embed_log.set_footer(text="Finanzas Aurum Bank", icon_url=LOGO_URL)
            await log_channel.send(embed=embed_log)

        #  Notificación formal al MD del cliente
        try:
            embed_dm = discord.Embed(
                title="⚡ RECONEXIÓN DE CRÉDITO REGULAR",
                description="Le informamos que Aurum Bank ha levantado la moratoria. Su préstamo vuelve a estar **ACTIVO**.",
                color=0x2ECC71,
                timestamp=ahora
            )
            embed_dm.set_author(name="AURUM BANK • ATENCIÓN AL CLIENTE", icon_url=LOGO_URL)
            embed_dm.add_field(name="📋 Código de Crédito", value=f"`PREST-{p_id:06d}`", inline=True)
            embed_dm.add_field(name="💰 Cuota Vigente", value=f"€{int(cuota):,}", inline=True)
            embed_dm.add_field(name="📅 Nueva Fecha de Pago", value=f"`{fecha_visual}`", inline=False)
            embed_dm.add_field(name="💬 Mensaje Oficial", value=motivo, inline=False)
            embed_dm.set_footer(text="Recuerde abonar antes del vencimiento para evitar penalizaciones automáticas del 5%.")
            await usuario.send(embed=embed_dm)
        except discord.Forbidden:
            pass

        # Actualizar el panel visual al instante
        pagos_cog = self.bot.get_cog("Pagos")
        if pagos_cog:
            try: await pagos_cog.actualizar_panel_visual(interaction.guild)
            except Exception as e: print(f"Error actualizando panel: {e}")


async def setup(bot):
    await bot.add_cog(Prestamos(bot))
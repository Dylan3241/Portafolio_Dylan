import discord
from discord.ext import commands, tasks
from discord import app_commands
import datetime
import sqlite3
import io

ROLES_PERMITIDOS = [
    "𝐂𝐄𝐎 | Director General",
    "𝐂𝐅𝐎 | Director Financiero",
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]

TIPOS_CUENTA = {
    "basica": "🪙 Cliente Básico",
    "premium": "💳 Cliente Premium",
    "vip": "💎 Cliente VIP"
}

# Configuración del ciclo del plan 
DIAS_PLAN = 21 


class Clientes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "aurum.db"
        self._verificar_columnas_db()
        
        # Iniciar el bucle automático en segundo plano
        self.verificador_planes_loop.start()

    def cog_unload(self):
        # Detener el bucle si la cog se recarga
        self.verificador_planes_loop.cancel()

    def _verificar_columnas_db(self):
        """Asegura que la tabla clientes tenga todas las columnas necesarias"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN numero_cuenta TEXT")
        except sqlite3.OperationalError:
            pass 
            
        try:
            cursor.execute("ALTER TABLE clientes ADD COLUMN fecha_proximo_pago TEXT")
        except sqlite3.OperationalError:
            pass

        conn.commit()
        conn.close()

    def generar_numero_cuenta(self):
        """Genera el siguiente número de cuenta secuencial"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT numero_cuenta FROM clientes WHERE numero_cuenta LIKE 'AUR-%' ORDER BY numero_cuenta DESC LIMIT 1")
        ultimo_registro = cursor.fetchone()
        conn.close()

        if ultimo_registro and ultimo_registro[0]:
            try:
                ultimo_numero_str = ultimo_registro[0].replace("AUR-", "")
                siguiente_numero = int(ultimo_numero_str) + 1
            except (ValueError, TypeError):
                siguiente_numero = 12  
        else:
            siguiente_numero = 1
                
        return f"AUR-{siguiente_numero:06d}"

    # ================= LOOP AUTOMÁTICO DE RECORDATORIOS =================
    @tasks.loop(hours=24) # Se ejecuta una vez al día automáticamente
    async def verificador_planes_loop(self):
        """Revisa la base de datos y avisa un día antes de que venza el plan de 3 semanas"""
        await self.bot.wait_until_ready()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Obtenemos todos los clientes con planes premium o vip que tengan fecha de próximo pago
        cursor.execute("SELECT user_id, rol, fecha_proximo_pago, numero_cuenta FROM clientes WHERE rol IN ('premium', 'vip') AND fecha_proximo_pago IS NOT NULL")
        clientes = cursor.fetchall()
        conn.close()
        
        ahora = datetime.datetime.now()
        
        for user_id, rol, fecha_pago_str, n_cuenta in clientes:
            try:
                # Convertimos el texto de la BD a un objeto de fecha analizable
                fecha_pago = datetime.datetime.strptime(fecha_pago_str, "%Y-%m-%d %H:%M:%S")
                # Calculamos cuántos días faltan para llegar a esa fecha
                dias_restantes = (fecha_pago - ahora).days
                
                # ¡UN DÍA ANTES! Si faltan exactamente 0 días y horas (o 1 día según margen de ejecución)
                # El valor '0' en .days significa que quedan menos de 24 horas para el cobro (El día anterior)
                if dias_restantes == 0:
                    guilds = self.bot.guilds
                    member = None
                    for g in guilds:
                        member = g.get_member(user_id)
                        if member: break
                    
                    if member:
                        try:
                            nombre_plan = TIPOS_CUENTA.get(rol, "Plan Comercial")
                            embed_aviso = discord.Embed(
                                title="⏳ RECORDATORIO DE RENOVACIÓN DE PLAN",
                                description=f"Estimado/a {member.display_name},\nLe recordamos que **mañana** se cumple el ciclo de 3 semanas de su suscripción bancaria.",
                                color=0x34495E
                            )
                            embed_aviso.add_field(name="💳 Cuenta Afectada", value=f"`{n_cuenta}`", inline=True)
                            embed_aviso.add_field(name="✨ Beneficio Actual", value=nombre_plan, inline=True)
                            embed_aviso.add_field(name="📅 Fecha Límite de Pago", value=fecha_pago.strftime("%d/%m/%Y a las %H:%M"), inline=False)
                            embed_aviso.set_footer(text="Aurum Bank • Mantenga su saldo al día para evitar la baja del plan.")
                            
                            await member.send(embed=embed_aviso)
                            print(f"📦 [AVISO PLAN] Recordatorio enviado correctamente a {member.name} por su plan {rol}.")
                        except discord.Forbidden:
                            print(f"❌ [AVISO PLAN] No se pudo enviar MD a {user_id} (Tiene los MD cerrados).")
            except Exception as e:
                print(f"Error procesando recordatorio para usuario {user_id}: {e}")

    # ================= CREAR CUENTA =================
    @app_commands.command(name="crear_cuenta", description="Crear cuenta bancaria a un cliente")
    @app_commands.describe(
        usuario="Usuario de Discord",
        nombre_dni="Nombre completo como figura en el DNI",
        numero_dni="Número de identificación",
        tipo="Tipo de cuenta (basica/premium/vip)",
        contrato="Contrato firmado en PDF",
        dni_frontal="Foto del DNI (png/jpg)"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Básica", value="basica"),
        app_commands.Choice(name="Premium", value="premium"),
        app_commands.Choice(name="VIP", value="vip")
    ])
    async def crear_cuenta(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member, 
        nombre_dni: str,
        numero_dni: str,
        tipo: app_commands.Choice[str], 
        contrato: discord.Attachment, 
        dni_frontal: discord.Attachment
    ):
        await interaction.response.defer(ephemeral=True)

        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.followup.send("❌ No tienes permisos para realizar esta acción.", ephemeral=True)
            return

        # Validaciones de archivos
        if not contrato.filename.lower().endswith(".pdf"):
            await interaction.followup.send("❌ El contrato debe ser un archivo PDF.", ephemeral=True)
            return
        
        valid_imgs = (".png", ".jpg", ".jpeg")
        if not dni_frontal.filename.lower().endswith(valid_imgs):
            await interaction.followup.send("❌ El DNI debe ser una imagen (PNG o JPG).", ephemeral=True)
            return

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM clientes WHERE user_id = ?", (usuario.id,))
        
        if cursor.fetchone():
            await interaction.followup.send(f"❌ {usuario.display_name} ya posee una cuenta activa.", ephemeral=True)
            conn.close()
            return

        # --- GENERACIÓN DE NÚMERO DE CUENTA SECUENCIAL ---
        n_cuenta = self.generar_numero_cuenta()
        
        ahora = datetime.datetime.now()
        fecha_actual = ahora.strftime("%Y-%m-%d %H:%M:%S")
        
        fecha_proximo_pago = (ahora + datetime.timedelta(days=DIAS_PLAN)).strftime("%Y-%m-%d %H:%M:%S")

        # INSERTAR INCLUYENDO LA NUEVA columna 'fecha_proximo_pago'
        cursor.execute(
            "INSERT INTO clientes (user_id, tiene_cuenta, saldo, rol, fecha_registro, numero_cuenta, fecha_proximo_pago) VALUES (?, ?, ?, ?, ?, ?, ?)",
            (usuario.id, True, 0, tipo.value, fecha_actual, n_cuenta, fecha_proximo_pago)
        )
        conn.commit()
        conn.close()

        contrato_bytes = await contrato.read()
        dni_bytes = await dni_frontal.read()

        def get_files():
            return [
                discord.File(io.BytesIO(contrato_bytes), filename=contrato.filename),
                discord.File(io.BytesIO(dni_bytes), filename=dni_frontal.filename)
            ]

        # Gestión de Roles
        nombre_rol_objetivo = TIPOS_CUENTA[tipo.value]
        rol_obj = discord.utils.get(interaction.guild.roles, name=nombre_rol_objetivo)
        role_status = ""
        
        if rol_obj:
            try:
                await usuario.add_roles(rol_obj)
                role_status = f"✅ Rol **{nombre_rol_objetivo}** asignado."
            except:
                role_status = "⚠️ Error al asignar rol (Jerarquía)."

        # ENVÍO DE BIENVENIDA AL CLIENTE
        try:
            embed_md = discord.Embed(
                title="🏦 ¡Bienvenido a Aurum Bank!",
                description=f"Hola {usuario.display_name}, tu cuenta ha sido dada de alta correctamente en nuestro sistema central.",
                color=0xFFD700
            )
            embed_md.add_field(name="💳 Número de Cuenta", value=f"`{n_cuenta}`", inline=False)
            embed_md.add_field(name="📝 Titular DNI", value=nombre_dni, inline=True)
            embed_md.add_field(name="🆔 ID DNI", value=numero_dni, inline=True)
            embed_md.add_field(name="✨ Rango", value=nombre_rol_objetivo, inline=False)
            embed_md.set_footer(text="Guarda bien tu número de cuenta para futuros préstamos.")
            
            await usuario.send(embed=embed_md, files=get_files())
            md_status = "✅ MD enviado al cliente."
        except discord.Forbidden:
            md_status = "⚠️ MD cerrado."

        # LOGS
        log_channel = discord.utils.get(interaction.guild.text_channels, name="📥・𝐥𝐨𝐠𝐬-𝐜𝐮𝐞𝐧𝐭𝐚𝐬")
        if log_channel:
            embed_log = discord.Embed(title="📥 Nueva Cuenta Creada", color=0x2ECC71)
            embed_log.add_field(name="👤 Cliente", value=f"{usuario.mention}", inline=True)
            embed_log.add_field(name="💳 Cuenta", value=f"`{n_cuenta}`", inline=True)
            embed_log.add_field(name="🏦 Gestor", value=interaction.user.mention, inline=False)
            await log_channel.send(embed=embed_log, files=get_files())

        await interaction.followup.send(
            f"✅ Cuenta `{n_cuenta}` creada con éxito para {usuario.mention}.\n{role_status}\n{md_status}",
            ephemeral=False
        )

    # ================= ACTUALIZAR CUENTA =================
    @app_commands.command(name="actualizar_cuenta", description="Cambia el tipo de cuenta de un usuario")
    @app_commands.describe(usuario="El cliente a actualizar", nuevo_rol="El nuevo rango (basico, premium, vip)")
    @app_commands.choices(nuevo_rol=[
        app_commands.Choice(name="Básica", value="basica"),
        app_commands.Choice(name="Premium", value="premium"),
        app_commands.Choice(name="VIP", value="vip")
    ])
    async def actualizar_cuenta(self, interaction: discord.Interaction, usuario: discord.Member, nuevo_rol: app_commands.Choice[str]):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.administrator:
            return await interaction.followup.send("❌ No tienes permiso.", ephemeral=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Verificamos si existe
        cursor.execute("SELECT user_id FROM clientes WHERE user_id = ?", (usuario.id,))
        if not cursor.fetchone():
            conn.close()
            return await interaction.followup.send("❌ Este usuario no tiene una cuenta abierta.", ephemeral=True)

        nueva_fecha = (datetime.datetime.now() + datetime.timedelta(days=DIAS_PLAN)).strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("UPDATE clientes SET rol = ?, fecha_proximo_pago = ? WHERE user_id = ?", (nuevo_rol.value, nueva_fecha, usuario.id))
        conn.commit()
        conn.close()

        for clave, nombre_r in TIPOS_CUENTA.items():
            rol_viejito = discord.utils.get(interaction.guild.roles, name=nombre_r)
            if rol_viejito: await usuario.remove_roles(rol_viejito)
            
        rol_nuevo_obj = discord.utils.get(interaction.guild.roles, name=TIPOS_CUENTA[nuevo_rol.value])
        if rol_nuevo_obj: await usuario.add_roles(rol_nuevo_obj)

        await interaction.followup.send(f"✅ Cuenta de {usuario.mention} actualizada a rango: **{nuevo_rol.name.upper()}** y ciclo de cobro reiniciado.")
        
    # ================= VER CARTERA =================
    @app_commands.command(name="ver_cartera", description="Muestra el estado financiero, préstamos y acciones de un usuario")
    @app_commands.describe(usuario="El cliente a consultar (Dejar vacío para ver tu propia cartera)")
    async def ver_cartera(self, interaction: discord.Interaction, usuario: discord.Member = None):
        usuario_objetivo = usuario or interaction.user
        await interaction.response.defer(ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 1. Obtener datos de la cuenta central del cliente
        cursor.execute(
            "SELECT numero_cuenta, saldo, rol, fecha_registro FROM clientes WHERE user_id = ?", 
            (usuario_objetivo.id,)
        )
        cuenta = cursor.fetchone()

        if not cuenta:
            conn.close()
            return await interaction.followup.send(
                f"❌ {'El usuario' if usuario else 'No'} posee una cuenta activa en Aurum Bank. Usa `/crear_cuenta` primero.", 
                ephemeral=True
            )

        n_cuenta, saldo, rol_key, fecha_reg = cuenta
        nombre_rango = TIPOS_CUENTA.get(rol_key, "Desconocido")

        # 2. Obtener préstamos activos del cliente
        try:
            cursor.execute(
                "SELECT SUM(monto) FROM prestamos WHERE user_id = ? AND estado = 'activo'", 
                (usuario_objetivo.id,)
            )
            total_prestamos = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            total_prestamos = "Tabla 'prestamos' no disponible"

        # 3. Obtener acciones del cliente
        try:
            cursor.execute(
                "SELECT SUM(cantidad_poseidas) FROM cartera_inversores WHERE usario_id = ?", 
                (usuario_objetivo.id,)
            )
            total_acciones = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            total_acciones = 0 

        # 4. Datos globales de Aurum Bank
        try:
            cursor.execute("SELECT SUM(saldo) FROM clientes")
            capital_total_banco = cursor.fetchone()[0] or 0
        except sqlite3.OperationalError:
            capital_total_banco = 0

        conn.close()

        # --- CONSTRUCCIÓN DEL EMBED ---
        embed_cartera = discord.Embed(
            title=f"💼 Cartera Financiera — {usuario_objetivo.display_name}",
            description=f"Historial central de activos y pasivos en **Aurum Bank**.\n*Miembro desde: {fecha_reg.split(' ')[0]}*",
            color=0xFFD700 if rol_key == "vip" else (0x95A5A6 if rol_key == "premium" else 0xCD7F32)
        )
        
        if usuario_objetivo.avatar:
            embed_cartera.set_thumbnail(url=usuario_objetivo.avatar.url)

        embed_cartera.add_field(name="💳 Número de Cuenta", value=f"`{n_cuenta}`", inline=True)
        embed_cartera.add_field(name="✨ Rango Comercial", value=nombre_rango, inline=True)
        embed_cartera.add_field(name="💰 Saldo Disponible", value=f"**$ {saldo:,.2f}**", inline=False)

        prestamos_val = f"$ {total_prestamos:,.2f}" if isinstance(total_prestamos, (int, float)) else total_prestamos
        embed_cartera.add_field(name="📉 Préstamos Activos", value=f"```{prestamos_val}```", inline=True)
        embed_cartera.add_field(name="📈 Acciones en Propiedad", value=f"```{total_acciones} u.```", inline=True)

        embed_cartera.add_field(
            name="🏛️ Liquidez Global de Aurum Bank", 
            value=f"El banco central gestiona actualmente: `$ {capital_total_banco:,.2f}`", 
            inline=False
        )

        embed_cartera.set_footer(text="Aurum Bank • Seguridad, Transparencia y Poder.")
        await interaction.followup.send(embed=embed_cartera, ephemeral=True)

    # ================= CERRAR CUENTA =================
    @app_commands.command(name="cerrar_cuenta", description="Elimina la cuenta de un cliente de la base de datos")
    async def cerrar_cuenta(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.user.guild_permissions.administrator:
            return await interaction.response.send_message("❌ No tienes permiso.", ephemeral=True)

        conn = sqlite3.connect("aurum.db")
        cursor = conn.cursor()
        
        cursor.execute("SELECT id FROM prestamos WHERE user_id = ? AND estado = 'activo'", (usuario.id,))
        if cursor.fetchone():
            conn.close()
            return await interaction.response.send_message("⚠️ No puedes cerrar la cuenta de un usuario con préstamos activos.", ephemeral=True)

        cursor.execute("DELETE FROM clientes WHERE user_id = ?", (usuario.id,))
        conn.commit()
        conn.close()

        await interaction.response.send_message(f"🗑️ La cuenta de {usuario.mention} ha sido eliminada del sistema.")


async def setup(bot):
    await bot.add_cog(Clientes(bot))
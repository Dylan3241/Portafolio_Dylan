import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import logging
import logging
import sys
from datetime import datetime

# Configuración de logs
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger("AurumBank.Bolsa")

class BolsaCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_path = "aurum.db"
        self.CANAL_PERMITIDO_ID = 1506387624514949242  
        self.EMPRESAS_WEST = [
            "Wild Wheels Autos",
            "Wild West Armery",
            "Centro de Licencias (CDL)",
            "Casino Montecarlo"
        ]
        self.init_database()
        
    def _canal_permitido(self, interaction: discord.Interaction):
        """Verifica si el comando se ejecuta en el canal autorizado."""
        return interaction.channel_id == self.CANAL_PERMITIDO_ID

    def _generar_barra(self, disponibles):
        """Genera una representación visual del stock disponible."""
        total = 100
        progreso = max(0, min(10, (disponibles // 10))) 
        return "█" * progreso + "░" * (10 - progreso)

    def init_database(self):
        """Inicializa las tablas y asegura que las empresas existan."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Crear tablas
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS empresas_bolsa (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    nombre_empresa TEXT UNIQUE,
                    acciones_totales INTEGER DEFAULT 1000,
                    acciones_disponibles INTEGER DEFAULT 100,
                    precio_inicial REAL,
                    precio_actual REAL
                )
            """)
            
            # Poblar empresas si no existen (REEMPLAZAR O ACTUALIZAR)
            empresas_iniciales = [
                ("Wild Wheels Autos", 2500.0),
                ("Wild West Armery", 2000.0),
                ("Centro de Licencias (CDL)", 1500.0),
                ("Casino Montecarlo", 1000.0),
                ("Aurum Bank", 500.0)
            ]

            for nombre, precio in empresas_iniciales:
                cursor.execute("""
                    INSERT OR IGNORE INTO empresas_bolsa 
                    (nombre_empresa, acciones_totales, acciones_disponibles, precio_inicial, precio_actual)
                    VALUES (?, 1000, 100, ?, ?)
                """, (nombre, precio, precio))
            
            conn.commit()

    async def empresa_autocomplete(self, interaction: discord.Interaction, current: str):
        """Autocompletado corregido: consulta directamente los nombres existentes."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Buscamos coincidencias con lo que el usuario escribe
                cursor.execute("SELECT nombre_empresa FROM empresas_bolsa WHERE nombre_empresa LIKE ?", (f"%{current}%",))
                resultados = cursor.fetchall()
                
                # Retornar los nombres encontrados
                return [
                    app_commands.Choice(name=emp[0], value=emp[0]) 
                    for emp in resultados
                ][:25]
        except Exception as e:
            logger.error(f"Error en autocompletado: {e}")
            return []

    @app_commands.command(name="bolsa", description="Muestra el estado actual de las empresas en la Bolsa de Valores.")
    async def bolsa(self, interaction: discord.Interaction):
        if not self._canal_permitido(interaction):
            embed_restriccion = discord.Embed(
                title="📍 Ubicación Incorrecta",
                description="Este comando financiero solo se puede ejecutar en el canal de operaciones bursátiles: `📊・𝐀𝐜𝐜𝐢𝐨𝐧𝐞𝐬`.",
                color=0xDF2935
            )
            return await interaction.response.send_message(embed=embed_restriccion, ephemeral=True)

        await interaction.response.defer()
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT nombre_empresa, precio_actual, acciones_disponibles 
                    FROM empresas_bolsa
                    ORDER BY CASE WHEN nombre_empresa = 'Aurum Bank' THEN 0 ELSE 1 END, precio_actual DESC
                """)
                empresas = cursor.fetchall()

            embed = discord.Embed(
                title="📊  Bolsa de Valores  |  Aurum Bank",
                description=(
                    "Bienvenido al índice financiero. Aquí puedes adquirir acciones directamente "
                    "de la **Oferta Inicial (IPO)** antes de que entren al mercado de libre comercio.\n\n"
                    "⚠️ *Recuerda que durante el lanzamiento aplican límites de compra diaria según tu tipo de cuenta bancaria.*"
                ),
                color=0xD4AF37
            )
            if self.bot.user.avatar:
                embed.set_thumbnail(url=self.bot.user.avatar.url)

            for nombre, precio, disponibles in empresas:
                barra_visual = self._generar_barra(disponibles)
                nombre_formateado = f"{nombre.upper()}" if nombre == "Aurum Bank" else f"🏢 {nombre.upper()}"
                embed.add_field(
                    name=nombre_formateado,
                    value=f"**Valor por Acción:** `${precio:,.2f}`\n**Estado IPO:** {barra_visual}\n⠀",
                    inline=False
                )

            embed.set_footer(text="Invierte de forma segura usando /comprar_acciones", icon_url=interaction.user.display_avatar.url)
            await interaction.followup.send(embed=embed)

        except sqlite3.Error as e:
            logger.error(f"Error en comando /bolsa: {e}", exc_info=True)
            embed_err = discord.Embed(title="⚠️ Error del Sistema", description="No se pudo conectar con el servidor financiero.", color=0xDF2935)
            await interaction.followup.send(embed=embed_err, ephemeral=True)

    @app_commands.command(name="comprar_acciones", description="Compra acciones de la IPO de una empresa.")
    @app_commands.describe(empresa="Selecciona la empresa donde deseas invertir", cantidad="Cantidad de acciones a comprar")
    @app_commands.autocomplete(empresa=empresa_autocomplete)
    async def comprar_acciones(self, interaction: discord.Interaction, empresa: str, cantidad: int):
        if not self._canal_permitido(interaction):
            return await interaction.response.send_message("Canal no autorizado.", ephemeral=True)

        if cantidad <= 0:
            return await interaction.response.send_message("La cantidad debe ser mayor a 0.", ephemeral=True)

        await interaction.response.defer(ephemeral=True)
        usuario_id = str(interaction.user.id)
        fecha_hoy = datetime.now().strftime("%Y-%m-%d")
        limites_rangos = {"basica": 20, "premium": 50, "vip": 150}

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # 1. Obtener datos usuario
                cursor.execute("SELECT saldo, rol FROM clientes WHERE user_id = ?", (usuario_id,))
                user_data = cursor.fetchone()
                
                # LOG DE DEPURACION: Esto te dirá exactamente qué ve el bot
                logger.info(f"DEBUG DEP: Usuario {usuario_id} | Datos BD: {user_data}")

                if not user_data:
                    return await interaction.followup.send("No eres cliente del banco. Abre una cuenta primero.", ephemeral=True)
                
                saldo_usuario, tipo_cuenta = user_data
                
                # Manejo por si el saldo es None o 0
                saldo_usuario = float(saldo_usuario) if saldo_usuario is not None else 0.0
                limite_diario_max = limites_rangos.get(str(tipo_cuenta).lower(), 20)
                
                # 2. Consultar historial
                cursor.execute("SELECT cantidad_comprada FROM registro_compras_diarias WHERE usuario_id = ? AND ultima_compra_fecha = ?", (usuario_id, fecha_hoy))
                reg = cursor.fetchone()
                comprado_hoy = reg[0] if reg else 0

                if comprado_hoy + cantidad > limite_diario_max:
                    return await interaction.followup.send(f"Límite excedido. Has comprado {comprado_hoy} hoy, tu límite es {limite_diario_max}.", ephemeral=True)

                # 3. Obtener empresa
                cursor.execute("SELECT id, precio_actual, acciones_disponibles, nombre_empresa FROM empresas_bolsa WHERE nombre_empresa = ?", (empresa,))
                empresa_data = cursor.fetchone()
                if not empresa_data:
                    return await interaction.followup.send("Empresa no encontrada.", ephemeral=True)
                
                empresa_id, precio, disponibles, nombre_real = empresa_data
                costo_total = cantidad * precio

                if saldo_usuario < costo_total:
                    return await interaction.followup.send(f"Saldo insuficiente. Tienes ${saldo_usuario:,.2f} y necesitas ${costo_total:,.2f}.", ephemeral=True)

                # 4. EJECUTAR TRANSACCION
                cursor.execute("UPDATE clientes SET saldo = saldo - ? WHERE user_id = ?", (costo_total, usuario_id))
                cursor.execute("UPDATE empresas_bolsa SET acciones_disponibles = acciones_disponibles - ? WHERE id = ?", (cantidad, empresa_id))
                
                # Registro diario
                cursor.execute("""
                    INSERT INTO registro_compras_diarias (usuario_id, cantidad_comprada, ultima_compra_fecha)
                    VALUES (?, ?, ?)
                    ON CONFLICT(usuario_id) DO UPDATE SET 
                    cantidad_comprada = cantidad_comprada + ?, ultima_compra_fecha = ?
                """, (usuario_id, cantidad, fecha_hoy, cantidad, fecha_hoy))
                
                # Cartera
                cursor.execute("SELECT id, acciones_poseidas FROM cartera_inversores WHERE usuario_id = ? AND empresa_id = ?", (usuario_id, empresa_id))
                cartera = cursor.fetchone()
                if cartera:
                    cursor.execute("UPDATE cartera_inversores SET acciones_poseidas = acciones_poseidas + ? WHERE id = ?", (cantidad, cartera[0]))
                else:
                    cursor.execute("INSERT INTO cartera_inversores (usuario_id, empresa_id, acciones_poseidas, precio_compra) VALUES (?, ?, ?, ?)", (usuario_id, empresa_id, cantidad, precio))
                
                conn.commit()
                await interaction.followup.send(f"✅ Compra exitosa de {cantidad} acciones de {nombre_real} por un total de ${costo_total:,.2f}.", ephemeral=True)

        except Exception as e:
            logger.error(f"Error fatal en compra: {e}", exc_info=True)
            await interaction.followup.send("Error al procesar la transacción. Revisa los logs.", ephemeral=True)

    @app_commands.command(name="cartera", description="Visualiza tus inversiones actuales y el rendimiento de tus acciones.")
    async def cartera(self, interaction: discord.Interaction):
        if not self._canal_permitido(interaction):
            embed_restriccion = discord.Embed(
                title="📍 Ubicación Incorrecta",
                description="Este comando financiero solo se puede ejecutar en el canal de operaciones bursátiles: `📊・𝐀𝐜𝐜𝐢𝐨𝐧𝐞𝐬`.",
                color=0xDF2935
            )
            return await interaction.response.send_message(embed=embed_restriccion, ephemeral=True)

        await interaction.response.defer()
        usuario_id = str(interaction.user.id)

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT e.nombre_empresa, c.acciones_poseidas, c.precio_compra, e.precio_actual
                    FROM cartera_inversores c
                    JOIN empresas_bolsa e ON c.empresa_id = e.id
                    WHERE c.usuario_id = ? AND c.acciones_poseidas > 0
                """, (usuario_id,))
                inversiones = cursor.fetchall()

            embed = discord.Embed(
                title=f"💼  Portafolio Financiero  |  {interaction.user.display_name}",
                color=0x0077B6
            )
            embed.set_thumbnail(url=interaction.user.display_avatar.url)

            if not inversiones:
                embed.description = "Actualmente no posees acciones activas en ninguna de las empresas listadas.\n\n💡 *¡Comienza a invertir hoy usando `/comprar_acciones`!*"
                await interaction.followup.send(embed=embed)
                return

            valor_total_cartera = 0.0
            rendimiento_total_neto = 0.0

            for nombre, acciones, precio_compra, precio_actual in inversiones:
                costo_adquisicion = acciones * precio_compra
                valor_mercado_actual = acciones * precio_actual
                rendimiento_neto = valor_mercado_actual - costo_adquisicion

                valor_total_cartera += valor_mercado_actual
                rendimiento_total_neto += rendimiento_neto

                emoji_trend = "📈" if rendimiento_neto >= 0 else "📉"
                signo = "+" if rendimiento_neto >= 0 else ""

                embed.add_field(
                    name=f"🏢 {nombre.upper()}",
                    value=(
                        f"🔹 **Acciones:** `{acciones}`\n"
                        f"🔹 **Precio Medio:** `${precio_compra:,.2f}`\n"
                        f"🔹 **Precio Actual:** `${precio_actual:,.2f}`\n"
                        f"🔹 **Rendimiento:** {emoji_trend} `{signo}${rendimiento_neto:,.2f}`\n━━━━━━"
                    ),
                    inline=False
                )

            emoji_global = "🟢" if rendimiento_total_neto >= 0 else "🔴"
            signo_global = "+" if rendimiento_total_neto >= 0 else ""

            embed.description = (
                f"### Resumen General del Portafolio\n"
                f"💰 **Valoración Actual:** `${valor_total_cartera:,.2f}`\n"
                f"📊 **Margen de Ganancia:** {emoji_global} `{signo_global}${rendimiento_total_neto:,.2f}`\n━━━━━━"
            )
            embed.set_footer(text="Aurum Bank • Información actualizada en tiempo real")
            await interaction.followup.send(embed=embed)

        except sqlite3.Error as e:
            logger.error(f"Error en comando /cartera: {e}", exc_info=True)
            embed_err = discord.Embed(title="⚠️ Error de Carga", description="No se pudo procesar la información de tus inversiones.", color=0xDF2935)
            await interaction.followup.send(embed=embed_err, ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(BolsaCog(bot))
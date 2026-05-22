import discord
from discord.ext import commands, tasks
from discord import app_commands
import sqlite3
import datetime

# ID SERVIDORES
DICCIONARIO_EMPRESAS = {
    1498416336974647467: "Aurum Bank",
    1169351365370335304: "Wild West Armery",
    1394956464388571216: "Centro de Licencias",
    1478157950832087111: "Wild Wheels Autos"
}

# ID AURUM BANK
AURUM_BANK_GUILD_ID = 1498416336974647467

# Lista de IDs de los bots de las empresas para medir interacciones automatizadas
BOTS_AFILIADOS_IDS = [
    1321163653692522547,  # Bot de West Armery
    1487960779989979206,   # Centro de licencia
    1478157950832087111    # Wild Wheels Autos
]

# DICCIONARIO DE LICENCIAS
VALOR_LICENCIAS_EMPRESAS = {
    "〡🪪〢Licencia Bajo Calibre": 5,  
    "〡🪪〢Licencia C": 5,           
    "〡🪪〢Licencia A": 15,          
    "〡🪪〢Licencia B": 20,          
    "〡🪪〢Licencia D": 35,          
    "〡🪪〢Licencia Tactica": 50,     
}

# DICCIONARIO DE CLIENTES EXCLUSIVOS DE AURUM BANK
VALOR_CLIENTES_AURUM = {
    "🪙 Cliente Básico": 10,  
    "💳 Cliente Premium": 30,  
    "💎 Cliente VIP": 75,   
    "💸 Prestamo 1/3": 10,  
    "💸 Prestamo 2/3": 20,     
    "💸 Prestamo 3/3": 35,     
    "🚫 Moroso": -10,
}

# ROLES DEL STAFF DE AURUM BANK 
ROLES_AUTORIZADOS_STAFF = [
    "𝐂𝐄𝐎 | Director General", 
    "𝐂𝐅𝐎 | Director Financiero", 
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]


class Actividad(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()
        
        # 📂 CREACIÓN DE TABLA
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS bolsa (
                guild_id INTEGER PRIMARY KEY,
                nombre_empresa TEXT,
                precio INTEGER DEFAULT 1000,
                ultima_actualizacion TEXT
            )
        """)
        self.conn.commit()
        
        self.escanear_actividad_diaria.start()

    def cog_unload(self):
        self.escanear_actividad_diaria.cancel()

    # ================= SYSTEM: OBTENER METRICAS DE UN GUILD =================
    async def obtener_metricas_servidor(self, guild: discord.Guild):
        """Procesa la actividad adaptándose si cuenta clientes (Aurum) o licencias (Filiales)"""
        datos_roles = {}
        puntos_totales_roles = 0
        
        # Si es Aurum Bank usa su diccionario de clientes, si no, el de licencias.
        diccionario_a_usar = VALOR_CLIENTES_AURUM if guild.id == AURUM_BANK_GUILD_ID else VALOR_LICENCIAS_EMPRESAS

        for role in guild.roles:
            if role.name in diccionario_a_usar:
                cant_miembros = len(role.members)
                datos_roles[role.name] = cant_miembros
                puntos_totales_roles += cant_miembros * diccionario_a_usar[role.name]

        # DETECCIÓN DE TICKETS 
        if guild.id == AURUM_BANK_GUILD_ID:
            # Prefijos operativos exclusivos de Aurum Bank
            prefijos_aurum = ("crear_cuenta-", "prestamo-", "deposito_retiro-", "ver-")
            tickets_activos = sum(
                1 for ch in guild.text_channels 
                if ch.name.lower().startswith(prefijos_aurum)
            )
        else:
            # Filtro estándar de tickets para las empresas afiliadas (Cubre tanto 'ticket-' como 'tickets-')
            tickets_activos = sum(
                1 for ch in guild.text_channels 
                if "ticket" in ch.name.lower()
            )

        mensajes_de_bots = 0
        usuarios_que_ya_hablaron = set()
        puntos_mensajes_usuarios = 0
        
        canales_a_revisar = guild.text_channels[:5]
        for channel in canales_a_revisar:
            try:
                async for msg in channel.history(limit=50, after=datetime.datetime.now() - datetime.timedelta(days=1)):
                    if msg.author.bot:
                        if msg.author.id in BOTS_AFILIADOS_IDS:
                            mensajes_de_bots += 1
                        continue
                    
                    if msg.author.id in usuarios_que_ya_hablaron:
                        continue

                    member = guild.get_member(msg.author.id)

                    if not member:
                        try:
                            member = await guild.fetch_member(msg.author.id)
                        except:
                            member = None

                    if member:
                        for role in member.roles:
                            if role.name in diccionario_a_usar:
                                puntos_mensajes_usuarios += diccionario_a_usar[role.name]
                                usuarios_que_ya_hablaron.add(msg.author.id)
                                break
            # 🛡️ CAPTURA DE ERRORES: Añadimos anomalías y caídas de la API de Discord
            except (discord.Forbidden, discord.HTTPException, discord.DiscordServerError):
                print(f"[Actividad] ⚠️ Discord API inestable o sin acceso al canal '{channel.name}' en '{guild.name}'. Saltando canal...")
                continue

        return {
            "datos_roles": datos_roles,
            "puntos_roles": puntos_totales_roles,
            "tickets": tickets_activos,
            "bot_msgs": mensajes_de_bots,
            "puntos_mensajes": puntos_mensajes_usuarios,
            "usuarios_activos": len(usuarios_que_ya_hablaron)
        }

    # ================= TASK: ESCANEO AUTOMÁTICO DIARIO =================
    @tasks.loop(hours=24)
    async def escanear_actividad_diaria(self):
        print(f"[Actividad] 🕒 Iniciando proceso de análisis financiero global...")
        fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        for guild_id in DICCIONARIO_EMPRESAS.keys():
            guild = self.bot.get_guild(guild_id)
            if not guild:
                continue
                
            res = await self.obtener_metricas_servidor(guild)
            
            # ALGORITMO DE FLUCTUACIÓN ECONÓMICA
            impacto_bolsa = res["puntos_roles"] + (res["tickets"] * 5) + res["puntos_mensajes"] + (res["bot_msgs"] * 0.5)
            impacto_final = int(impacto_bolsa)

            print(f"[Bolsa] {guild.name} generó un impacto económico neto de: +€{impacto_final:,}")
            
            # PERSISTENCIA EN BD
            self.cursor.execute("""
                INSERT INTO bolsa (guild_id, nombre_empresa, precio, ultima_actualizacion)
                VALUES (?, ?, ?, ?)
                ON CONFLICT(guild_id) DO UPDATE SET
                    precio = precio + excluded.precio,
                    ultima_actualizacion = excluded.ultima_actualizacion
            """, (guild_id, DICCIONARIO_EMPRESAS[guild_id], impacto_final, fecha_hoy))
            
        self.conn.commit()
        print("[Actividad] ✅ Base de datos de la Bolsa de Valores actualizada correctamente.")

    @escanear_actividad_diaria.before_loop
    async def before_escanear(self):
        await self.bot.wait_until_ready()

    # ================= COMANDO STAFF: /ACTIVIDAD =================
    @app_commands.command(name="actividad", description="Ver reporte ejecutivo de actividad de una empresa")
    @app_commands.describe(empresa="Selecciona la empresa a auditar")
    @app_commands.choices(empresa=[
        app_commands.Choice(name=nombre, value=str(guild_id)) for guild_id, nombre in DICCIONARIO_EMPRESAS.items()
    ])
    async def actividad(self, interaction: discord.Interaction, empresa: app_commands.Choice[str]):
        # 🛡️ Permite usar el comando solo si el usuario tiene un rol del Staff del Banco Aurum
        if not any(role.name in ROLES_AUTORIZADOS_STAFF for role in interaction.user.roles):
            return await interaction.response.send_message("❌ No formas parte del directorio de Aurum Bank para auditar empresas.", ephemeral=True)

        target_guild_id = int(empresa.value)
        guild = self.bot.get_guild(target_guild_id)

        if not guild:
            return await interaction.response.send_message(f"❌ Error: El bot no tiene acceso a **{empresa.name}** o la ID es incorrecta.", ephemeral=True)

        await interaction.response.defer(ephemeral=False)

        res = await self.obtener_metricas_servidor(guild)

        if res["datos_roles"]:
            desglose_roles = ""
            # Cambia dinámicamente el texto según el servidor analizado
            tipo_miembro = "clientes" if target_guild_id == AURUM_BANK_GUILD_ID else "licencias"
            for r_name, cant in res["datos_roles"].items():
                desglose_roles += f"• **{r_name}:** `{cant}` {tipo_miembro}.\n"
        else:
            desglose_roles = "*No se detectaron roles evaluables en este servidor.*"

        impacto_estimado = res["puntos_roles"] + (res["tickets"] * 5) + res["puntos_mensajes"] + (res["bot_msgs"] * 0.5)

        self.cursor.execute("SELECT precio FROM bolsa WHERE guild_id = ?", (target_guild_id,))
        row = self.cursor.fetchone()
        precio_actual_bd = row[0] if row else 1000

        # DISEÑO DEL EMBED DE INFORMACIÓN 
        embed = discord.Embed(
            title=f"🏛️ Auditoría Económica: {guild.name}",
            description=f"Análisis estadístico e índice de actividad del servidor para el mercado financiero.",
            color=0xd4af37
        )
        embed.set_thumbnail(url=guild.icon.url if guild.icon else "https://i.imgur.com/TGUHiux.png")
        
        embed.add_field(
            name="💰 Valor de la Acción Actual (BD)",
            value=f"**€{precio_actual_bd:,}**",
            inline=True
        )
        embed.add_field(
            name="📈 Rendimiento Esperado (Próximo Cierre)", 
            value=f"+€{int(impacto_estimado):,}",
            inline=True
        )
        
        # Título dinámico para el censo
        titulo_censo = "👥 Censo de Cartera de Clientes" if target_guild_id == AURUM_BANK_GUILD_ID else "👥 Censo de Licencias Activas"
        embed.add_field(
            name=titulo_censo,
            value=desglose_roles,
            inline=False
        )
        embed.add_field(
            name="📊 Métricas Operacionales (Últimas 24h)",
            value=f"• Tickets de operaciones activos: `{res['tickets']}`\n• Interacciones de sistemas: `{res['bot_msgs']}`\n• Usuarios activos: `{res['usuarios_activos']}`",
            inline=False
        )
        
        await interaction.followup.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Actividad(bot))
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime
from typing import Optional

DB_PATH = "database.db"
#MULTAS_CHANNEL_ID = 1395579722464755752  # canal donde se publican las multas
#DENUNCIAS_CHANNEL_ID = 1395579600360181870  # canal para denuncias (ajustar si hace falta)
#ROLES_PERMITIDOS = ["Policía Nacional", "Policía Local", "Guardia Civil"]
#JUECES_ROLES = ["Juez"]
#STAFF_ALLOWED = ROLES_PERMITIDOS + JUECES_ROLES


class MultasArrestosDenuncias(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # Una sola conexión compartida dentro del cog
        self.db = sqlite3.connect(DB_PATH)
        self.cursor = self.db.cursor()
        self.db_init()

    def db_init(self):
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS cedulas (
                user_id INTEGER PRIMARY KEY,
                nombre TEXT,
                apellido TEXT,
                nacimiento TEXT,
                nacionalidad TEXT,
                lugar TEXT,
                dni TEXT,
                tipo_sangre TEXT,
                genero TEXT,
                roblox TEXT,
                foto_url TEXT
            );
            """
        )

        # Tabla multas
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS multas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                oficial_nombre TEXT,
                monto INTEGER,
                razon TEXT,
                fecha TEXT
            );
            """
        )

        # Tabla arrestos
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS arrestos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                oficial_nombre TEXT,
                motivo TEXT,
                fecha TEXT,
                duracion INTEGER
            );
            """
        )

        # Tabla denuncias
        self.cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS denuncias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario_id INTEGER,
                usuario_nombre TEXT,
                motivo TEXT,
                pruebas TEXT,
                fecha TEXT,
                denunciante_id INTEGER,
                denunciante_nombre TEXT
            );
            """
        )

        self.db.commit()

    # -------------------------
    # Helper: comprobar rol
    # -------------------------
    def has_any_role(self, member: discord.abc.Snowflake, allowed_roles: list) -> bool:
        return any(role.name in allowed_roles for role in member.roles)

    # -------------------------
    # COMANDO: /multar
    # -------------------------
    @app_commands.command(name="multar", description="Multa a un user (solo oficiales).")
    @app_commands.describe(user="Usuario a multar", monto="Monto de la multa", razon="Razón de la multa")
    async def multar(self, interaction: discord.Interaction, user: discord.Member, monto: int, razon: str):
        # Verificar canal
        #if interaction.channel.id != MULTAS_CHANNEL_ID:
            #await interaction.response.send_message("❌ Este comando solo puede usarse en el canal de multas.", ephemeral=True)
            #return

        #if not self.has_any_role(interaction.user, ROLES_PERMITIDOS):
            #await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
            #return

        fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        self.cursor.execute("SELECT nombre, apellido FROM cedulas WHERE user_id=?", (interaction.user.id,))
        row = self.cursor.fetchone()
        if row:
            nombre_oficial = f"{row[0]} {row[1]}".strip()
        else:
            nombre_oficial = interaction.user.name

        self.cursor.execute(
            "INSERT INTO multas (user_id, oficial_nombre, monto, razon, fecha) VALUES (?, ?, ?, ?, ?)",
            (user.id, nombre_oficial, monto, razon, fecha)
        )
        self.db.commit()

        multa_id = self.cursor.lastrowid

        self.cursor.execute("SELECT COUNT(*) FROM multas WHERE user_id=?", (user.id,))
        total_multas = self.cursor.fetchone()[0]

        canal_embed = discord.Embed(
            title="⚠️ Multa Aplicada",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        canal_embed.add_field(name="🙍 User multado", value=f"{user.mention}", inline=True)
        canal_embed.add_field(name="👮 Oficial", value=nombre_oficial, inline=True)
        canal_embed.add_field(name="💸 Monto", value=f"${monto}", inline=True)
        canal_embed.add_field(name="🧾 Razón", value=razon, inline=False)
        canal_embed.add_field(name="🆔 ID de la multa", value=str(multa_id), inline=False)
        canal_embed.set_footer(text=f"Fecha: {fecha}")

        dm_embed = discord.Embed(
            title="🚨 Has recibido una multa",
            description="Has sido multado en **Canarias RP**.",
            color=discord.Color.red(),
            timestamp=datetime.datetime.now()
        )
        dm_embed.add_field(name="🧾 Razón", value=razon, inline=False)
        dm_embed.add_field(name="💸 Monto", value=f"${monto}", inline=True)
        dm_embed.add_field(name="👮 Oficial", value=nombre_oficial, inline=True)
        dm_embed.add_field(name="🆔 ID de multa", value=str(multa_id), inline=True)
        dm_embed.add_field(name="📊 Multas acumuladas", value=f"Tienes **{total_multas}** multas activas.", inline=False)
        dm_embed.set_footer(text="Si crees que esto fue un error, contacta a la policía.")


        await interaction.response.send_message(embed=canal_embed)
        try:
            await user.send(embed=dm_embed)
        except discord.Forbidden:
            await interaction.followup.send(f"⚠️ {user.mention} tiene los MD cerrados, no se pudo enviar la notificación por MD.", ephemeral=True)

    # -------------------------
    # COMANDO: VER MULTAS
    # -------------------------
    @app_commands.command(name="ver_multas", description="Ver multas de un usuario. Si no pones usuario, muestra tus multas.")
    @app_commands.describe(user="Usuario a consultar (opcional)")
    async def ver_multas(self, interaction: discord.Interaction, user: Optional[discord.Member] = None):
        target = user or interaction.user

        #if user and not self.has_any_role(interaction.user, ROLES_PERMITIDOS):
            #await interaction.response.send_message("❌ No tienes permiso para ver las multas de otros usuarios.", ephemeral=True)
            #return

        self.cursor.execute("SELECT id, monto, razon, fecha, oficial_nombre FROM multas WHERE user_id=?", (target.id,))
        multas = self.cursor.fetchall()

        if not multas:
            await interaction.response.send_message(f"{target.mention} no tiene multas.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📋 Multas de {target.name}", color=discord.Color.orange())
        for m in multas:
            mid, monto, razon, fecha, oficial = m[0], m[1], m[2], m[3], m[4]
            embed.add_field(
                name=f"ID {mid} - ${monto}",
                value=f"Razón: {razon}\nOficial: {oficial}\nFecha: {fecha}",
                inline=False
            )

        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Te envié las multas por MD.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ No pude enviarte MD. Tenés los DMs cerrados.", ephemeral=True)

    # -------------------------
    # COMANDO: ELIMINAR MULTA
    # -------------------------
    @app_commands.command(name="eliminar_multa", description="Eliminar una multa por ID (solo oficiales/jueces).")
    @app_commands.describe(multa_id="ID de la multa a eliminar")
    async def eliminar_multa(self, interaction: discord.Interaction, multa_id: int):

        #if not self.has_any_role(interaction.user, STAFF_ALLOWED):
            #await interaction.response.send_message("❌ No tienes permisos para eliminar multas.", ephemeral=True)
            #return

        self.cursor.execute("SELECT user_id, monto, razon FROM multas WHERE id=?", (multa_id,))
        result = self.cursor.fetchone()
        if not result:
            await interaction.response.send_message("❌ No se encontró la multa con ese ID.", ephemeral=True)
            return

        user_id, monto, razon = result
        try:
            usuario = await self.bot.fetch_user(user_id)
            mention = usuario.mention
        except Exception:
            mention = f"ID {user_id}"

        embed = discord.Embed(
            title="✅ Multa eliminada",
            description=f"Multa eliminada correctamente.",
            color=discord.Color.green()
        )
        embed.add_field(name="Usuario", value=mention, inline=False)
        embed.add_field(name="ID de la multa", value=str(multa_id), inline=True)
        embed.add_field(name="Monto", value=f"${monto}", inline=True)
        embed.add_field(name="Razón", value=razon, inline=False)

        self.cursor.execute("DELETE FROM multas WHERE id=?", (multa_id,))
        self.db.commit()

        await interaction.response.send_message(embed=embed)

    # -------------------------
    # COMANDO: /arrestar
    # -------------------------
    @app_commands.command(name="arrestar", description="Arrestar a un user (solo oficiales).")
    @app_commands.describe(user="Usuario a arrestar", motivo="Motivo", duracion="Duración en minutos")
    async def arrestar(self, interaction: discord.Interaction, user: discord.Member, motivo: str, duracion: int):
        #if not self.has_any_role(interaction.user, ROLES_PERMITIDOS):
            #await interaction.response.send_message("❌ No tienes permisos para arrestar.", ephemeral=True)
            #return

        fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")
        self.cursor.execute("SELECT nombre, apellido FROM cedulas WHERE user_id=?", (interaction.user.id,))
        row = self.cursor.fetchone()
        nombre_oficial = f"{row[0]} {row[1]}".strip() if row else interaction.user.name

        self.cursor.execute(
            "INSERT INTO arrestos (user_id, oficial_nombre, motivo, fecha, duracion) VALUES (?, ?, ?, ?, ?)",
            (user.id, nombre_oficial, motivo, fecha, duracion)
        )
        self.db.commit()

        embed = discord.Embed(title="🚨 Arresto Realizado", color=discord.Color.dark_red(), timestamp=datetime.datetime.now())
        embed.add_field(name="User arrestado", value=f"{user.mention}", inline=True)
        embed.add_field(name="Oficial", value=nombre_oficial, inline=True)
        embed.add_field(name="Duración", value=f"{duracion} minutos", inline=True)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.set_footer(text=f"Fecha: {fecha}")

        await interaction.response.send_message(embed=embed)

    # -------------------------
    # COMANDO: /ver_registro
    # -------------------------
    @app_commands.command(name="ver_registro", description="Ver arrestos de un user (solo oficiales).")
    @app_commands.describe(user="Usuario a consultar")
    async def ver_registro(self, interaction: discord.Interaction, user: discord.Member):
        #if not self.has_any_role(interaction.user, ROLES_PERMITIDOS):
            #await interaction.response.send_message("❌ No tienes permisos para ver registros.", ephemeral=True)
            #return

        self.cursor.execute("SELECT id, oficial_nombre, motivo, fecha, duracion FROM arrestos WHERE user_id=?", (user.id,))
        registros = self.cursor.fetchall()
        if not registros:
            await interaction.response.send_message("No se encontraron arrestos.", ephemeral=True)
            return

        embed = discord.Embed(title=f"📋 Registro de Arrestos - {user}", color=discord.Color.dark_red())
        for reg in registros:
            rid, oficial, motivo, fecha, dur = reg
            embed.add_field(
                name=f"ID {rid} - Oficial: {oficial} - Duración: {dur} min",
                value=f"Motivo: {motivo}\nFecha: {fecha}",
                inline=False
            )

        try:
            await interaction.user.send(embed=embed)
            await interaction.response.send_message("✅ Te envié el registro por MD.", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message("❌ No pude enviarte MD. Tenés los DMs cerrados.", ephemeral=True)


    # -------------------------
    # COMANDO: DENUNCIAR
    # -------------------------
    @app_commands.command(name="denunciar", description="Realiza una denuncia contra un usuario.")
    @app_commands.describe(usuario="Usuario denunciado", motivo="Motivo de la denuncia", pruebas="Pruebas opcionales")
    async def denunciar(
        self,
        interaction: discord.Interaction,
        usuario: discord.User,
        motivo: str,
        pruebas: Optional[discord.Attachment] = None
    ):

        prueba_url = pruebas.url if pruebas else "Sin pruebas adjuntas"
        fecha = datetime.datetime.now().strftime("%d/%m/%Y %H:%M")

        self.cursor.execute("""
            INSERT INTO denuncias (
                usuario_id, usuario_nombre, motivo, pruebas, fecha,
                denunciante_id, denunciante_nombre
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            usuario.id,
            usuario.name,
            motivo,
            prueba_url,
            fecha,
            interaction.user.id,
            interaction.user.name
        ))
        self.db.commit()

        denuncia_id = self.cursor.lastrowid

        embed_publico = discord.Embed(
            title="📢 Nueva Denuncia Registrada",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )
        embed_publico.add_field(name="👤 Denunciado", value=f"{usuario.mention} (`{usuario.id}`)", inline=False)
        embed_publico.add_field(name="📝 Motivo", value=motivo, inline=False)
        embed_publico.add_field(name="📁 Pruebas", value=prueba_url, inline=False)
        embed_publico.add_field(name="🆔 ID de Denuncia", value=str(denuncia_id), inline=False)
        embed_publico.set_footer(text=f"Denunciado por {interaction.user.name}")

        await interaction.channel.send(embed=embed_publico)

        try:
            embed_dm = discord.Embed(
                title="⚠️ Has sido denunciado",
                color=discord.Color.red(),
                timestamp=datetime.datetime.now()
            )
            embed_dm.add_field(name="Motivo", value=motivo, inline=False)
            embed_dm.add_field(name="Pruebas", value=prueba_url, inline=False)
            embed_dm.add_field(name="ID de denuncia", value=str(denuncia_id), inline=False)
            embed_dm.set_footer(text=f"Denuncia realizada por {interaction.user.name}")

            await usuario.send(embed=embed_dm)

        except discord.Forbidden:
            pass  

        await interaction.response.send_message(
            f"✅ Denuncia registrada correctamente con ID **{denuncia_id}**.",
            ephemeral=True
        )

    # -------------------------
    # COMANDO: /levantar_denuncia
    # -------------------------
    @app_commands.command(name="levantar_denuncia", description="Levanta una denuncia existente.")
    @app_commands.describe(denuncia_id="ID de la denuncia a levantar")
    async def levantar_denuncia(self, interaction: discord.Interaction, denuncia_id: int):

        self.cursor.execute("SELECT * FROM denuncias WHERE id = ?", (denuncia_id,))
        denuncia = self.cursor.fetchone()

        if not denuncia:
            return await interaction.response.send_message(
                "❌ No existe una denuncia con ese ID.",
                ephemeral=True
            )

        # Datos guardados en la DB
        usuario_id = denuncia[1]
        usuario_nombre = denuncia[2]
        motivo = denuncia[3]
        pruebas = denuncia[4]
        fecha = denuncia[5]
        denunciante_id = denuncia[6]
        denunciante_nombre = denuncia[7]

        def es_url_valida(url):
            return isinstance(url, str) and (url.startswith("http://") or url.startswith("https://"))

        embed = discord.Embed(
            title="🟢 Denuncia levantada",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="👤 Usuario denunciado", value=f"{usuario_nombre} (`{usuario_id}`)", inline=False)
        embed.add_field(name="📝 Motivo", value=motivo, inline=False)
        embed.add_field(name="📅 Fecha de denuncia", value=fecha, inline=False)
        embed.add_field(name="📁 Pruebas", value=pruebas, inline=False)

        if es_url_valida(pruebas):
            embed.set_image(url=pruebas)

        self.cursor.execute("DELETE FROM denuncias WHERE id = ?", (denuncia_id,))
        self.db.commit()

        # ============================================================
        #  MANDAR DM AL DENUNCIANTE
        # ============================================================
        try:
            denunciante_user = await self.bot.fetch_user(denunciante_id)

            embed_dm_denunciante = discord.Embed(
                title="📨 Tu denuncia fue levantada",
                color=discord.Color.orange(),
                timestamp=datetime.datetime.now()
            )
            embed_dm_denunciante.add_field(name="ID de la denuncia", value=str(denuncia_id), inline=False)
            embed_dm_denunciante.add_field(name="Usuario denunciado", value=f"{usuario_nombre} (`{usuario_id}`)", inline=False)
            embed_dm_denunciante.add_field(name="Motivo", value=motivo, inline=False)

            if es_url_valida(pruebas):
                embed_dm_denunciante.set_image(url=pruebas)

            await denunciante_user.send(embed=embed_dm_denunciante)

        except discord.Forbidden:
            pass 

        try:
            denunciado_user = await self.bot.fetch_user(usuario_id)

            embed_dm_denunciado = discord.Embed(
                title="🟢 Una denuncia contra ti fue levantada",
                color=discord.Color.green(),
                timestamp=datetime.datetime.now()
            )
            embed_dm_denunciado.add_field(name="ID de la denuncia", value=str(denuncia_id), inline=False)
            embed_dm_denunciado.add_field(name="Motivo de la denuncia", value=motivo, inline=False)
            embed_dm_denunciado.add_field(name="Fecha original", value=fecha, inline=False)

            if es_url_valida(pruebas):
                embed_dm_denunciado.set_image(url=pruebas)

            await denunciado_user.send(embed=embed_dm_denunciado)

        except discord.Forbidden:
            pass  

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # COMANDO: VER DENUNCIAS
    # -------------------------
    @app_commands.command(name="ver_denuncias", description="Muestra todas las denuncias realizadas a un usuario.")
    @app_commands.describe(usuario="Usuario del cual quieres ver las denuncias")
    async def ver_denuncias(self, interaction: discord.Interaction, usuario: discord.User):

        self.cursor.execute("SELECT id, motivo, pruebas, fecha, denunciante_nombre FROM denuncias WHERE usuario_id=?", (usuario.id,))
        denuncias = self.cursor.fetchall()

        if not denuncias:
            await interaction.response.send_message(f"❌ El usuario {usuario.mention} no tiene denuncias registradas.", ephemeral=True)
            return

        embed = discord.Embed(
            title=f"📑 Denuncias de {usuario.name}",
            color=discord.Color.orange(),
            timestamp=datetime.datetime.now()
        )

        for d in denuncias:
            denuncia_id, motivo, pruebas, fecha, denunciante = d
            embed.add_field(
                name=f"🆔 Denuncia {denuncia_id}",
                value=(
                    f"**Motivo:** {motivo}\n"
                    f"**Pruebas:** {pruebas}\n"
                    f"**Fecha:** {fecha}\n"
                    f"**Denunciante:** {denunciante}"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # COMANDO: HISTORIAL
    # -------------------------
    @app_commands.command(name="historial", description="Muestra el historial completo (multas y denuncias) de un usuario.")
    @app_commands.describe(usuario="Usuario a consultar")
    async def historial(self, interaction: discord.Interaction, usuario: discord.User):

        self.cursor.execute("SELECT id, razon, oficial_nombre, fecha FROM multas WHERE user_id=?", (usuario.id,))
        multas = self.cursor.fetchall()

        self.cursor.execute("SELECT id, motivo, denunciante_nombre, fecha FROM denuncias WHERE usuario_id=?", (usuario.id,))
        denuncias = self.cursor.fetchall()

        embed = discord.Embed(
            title=f"📚 Historial Completo de {usuario.name}",
            color=discord.Color.blue(),
            timestamp=datetime.datetime.now()
        )

        if multas:
            texto_multas = ""
            for m in multas:
                multa_id, razon, oficial, fecha = m
                texto_multas += f"**ID {multa_id}** — {razon}\n👮 Oficial: {oficial}\n📅 Fecha: {fecha}\n\n"
            embed.add_field(name="🚔 Multas registradas", value=texto_multas, inline=False)
        else:
            embed.add_field(name="🚔 Multas registradas", value="Sin multas.", inline=False)

        if denuncias:
            texto_denuncias = ""
            for d in denuncias:
                denuncia_id, motivo, denunciante, fecha = d
                texto_denuncias += f"**ID {denuncia_id}** — {motivo}\n📣 Denunciante: {denunciante}\n📅 Fecha: {fecha}\n\n"
            embed.add_field(name="📢 Denuncias registradas", value=texto_denuncias, inline=False)
        else:
            embed.add_field(name="📢 Denuncias registradas", value="Sin denuncias.", inline=False)

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # COMANDO: VER DENUNCIAS
    # -------------------------
    @app_commands.command(name="ver_denuncias", description="Ver todas las denuncias registradas.")
    async def ver_denuncias(self, interaction: discord.Interaction):

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
            return

        self.cursor.execute("SELECT * FROM denuncias")
        denuncias = self.cursor.fetchall()

        if not denuncias:
            await interaction.response.send_message("📭 No hay denuncias registradas.", ephemeral=True)
            return

        embed = discord.Embed(
            title="📄 Lista de denuncias",
            color=discord.Color.blue()
        )

        for d in denuncias:
            embed.add_field(
                name=f"ID: {d[0]}",
                value=(
                    f"👤 **Denunciado:** {d[2]} (ID: {d[1]})\n"
                    f"📝 **Motivo:** {d[3]}\n"
                    f"📎 **Pruebas:** {d[4]}\n"
                    f"📅 **Fecha:** {d[5]}\n"
                    f"📣 **Denunciante:** {d[7]} (ID: {d[6]})\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                ),
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------
    # COMANDO: ELIMINAR DENUNCIA
    # -------------------------
    @app_commands.command(name="eliminar_denuncia", description="Eliminar una denuncia por ID.")
    @app_commands.describe(denuncia_id="ID de la denuncia que deseas eliminar")
    async def eliminar_denuncia(self, interaction: discord.Interaction, denuncia_id: int):

        if not interaction.user.guild_permissions.manage_messages:
            await interaction.response.send_message("❌ No tienes permisos para usar este comando.", ephemeral=True)
            return

        self.cursor.execute("SELECT * FROM denuncias WHERE id = ?", (denuncia_id,))
        denuncia = self.cursor.fetchone()

        if not denuncia:
            await interaction.response.send_message("❌ No existe una denuncia con ese ID.", ephemeral=True)
            return

        denunciado_id = denuncia[1]
        denunciado_nombre = denuncia[2]
        motivo = denuncia[3]
        pruebas = denuncia[4]
        fecha = denuncia[5]
        denunciante_id = denuncia[6]
        denunciante_nombre = denuncia[7]

        self.cursor.execute("DELETE FROM denuncias WHERE id = ?", (denuncia_id,))
        self.db.commit()

        embed = discord.Embed(
            title="🗑️ Denuncia eliminada",
            color=discord.Color.red()
        )
        embed.add_field(name="ID", value=str(denuncia_id), inline=False)
        embed.add_field(name="Denunciado", value=f"{denunciado_nombre} (ID: {denunciado_id})", inline=False)
        embed.add_field(name="Denunciante", value=f"{denunciante_nombre} (ID: {denunciante_id})", inline=False)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        embed.add_field(name="Pruebas", value=pruebas, inline=False)
        embed.add_field(name="Fecha", value=fecha, inline=False)

        await interaction.response.send_message(embed=embed)

        try:
            user_denunciante = await interaction.client.fetch_user(denunciante_id)
            await user_denunciante.send(
                f"📢 Tu denuncia con **ID {denuncia_id}** fue levantada por el staff."
            )
        except:
            pass

        try:
            user_denunciado = await interaction.client.fetch_user(denunciado_id)
            await user_denunciado.send(
                f"📢 La denuncia en tu contra (**ID {denuncia_id}**) fue levantada."
            )
        except:
            pass

async def setup(bot: commands.Bot):
    await bot.add_cog(MultasArrestosDenuncias(bot))

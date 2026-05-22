import discord
from discord import app_commands
from discord.ext import commands, tasks
import sqlite3
import datetime

class Empleos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "aurum.db"
        self.revisar_pagos.start()

    def cog_unload(self):
        self.revisar_pagos.cancel()

    def get_db(self):
        return sqlite3.connect(self.db_path)

    @tasks.loop(hours=1) # Bajamos a 1 hora para ser más precisos, pero la lógica interna evita spam
    async def revisar_pagos(self):
        """Revisa qué empleados deben cobrar y avisa una sola vez"""
        await self.bot.wait_until_ready()
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        # Filtramos por aviso_enviado = 0 para no repetir mensajes
        cursor.execute("""
            SELECT user_id, nombre_ic, pago_periodico, fecha_ingreso, ultimo_pago 
            FROM empleados 
            WHERE estado = 'activo' AND aviso_enviado = 0
        """)
        empleados = cursor.fetchall()
        
        hoy = datetime.date.today()
        pagos_a_notificar = []
        ids_a_actualizar = []

        for emp in empleados:
            u_id, nombre, monto, f_ingreso, u_pago = emp
            
            # Fecha de referencia para el cálculo
            fecha_ref_str = u_pago if u_pago else f_ingreso
            fecha_referencia = datetime.datetime.strptime(fecha_ref_str, "%Y-%m-%d").date()
            
            dias_transcurridos = (hoy - fecha_referencia).days
            
            # Si pasaron 2 días o más, agendamos para avisar
            if dias_transcurridos >= 2:
                pagos_a_notificar.append({
                    "mencion": f"<@{u_id}>",
                    "nombre": nombre,
                    "monto": monto
                })
                ids_a_actualizar.append(u_id)

        if pagos_a_notificar:
            # Buscamos el canal y el servidor
            guild = self.bot.guilds[0] 
            canal_logs = discord.utils.get(guild.text_channels, name="🙍・logs-trabajadores")
            
            # --- BUSCAR ROL GERENCIA ---
            rol_gerencia = discord.utils.get(guild.roles, name="---- Gerencia ----")
            mencion_rol = rol_gerencia.mention if rol_gerencia else "@Gerencia"

            if canal_logs:
                embed = discord.Embed(
                    title="💰 NÓMINA PENDIENTE",
                    description=f"Atención {mencion_rol}, los siguientes empleados deben cobrar:",
                    color=discord.Color.gold()
                )
                
                for p in pagos_a_notificar:
                    embed.add_field(
                        name=p["nombre"], 
                        value=f"**Monto:** €{p['monto']}\n**Usuario:** {p['mencion']}", 
                        inline=False
                    )
                
                embed.set_footer(text="Usa /confirmar_pago para limpiar este aviso.")
                await canal_logs.send(content=mencion_rol, embed=embed)

                # Marcamos en la DB que ya avisamos para que no se repita en la próxima hora
                for uid in ids_a_actualizar:
                    cursor.execute("UPDATE empleados SET aviso_enviado = 1 WHERE user_id = ?", (uid,))
                conn.commit()
        
        conn.close()

    @app_commands.command(name="confirmar_pago", description="Marca el pago de un empleado como realizado")
    async def confirmar_pago(self, interaction: discord.Interaction, usuario: discord.Member):
        await interaction.response.defer(ephemeral=True)
        
        conn = self.get_db()
        cursor = conn.cursor()
        hoy = datetime.date.today().strftime("%Y-%m-%d")
        
        # Al pagar, ponemos aviso_enviado en 0 para que en 2 días vuelva a avisar
        cursor.execute("""
            UPDATE empleados 
            SET ultimo_pago = ?, aviso_enviado = 0 
            WHERE user_id = ? AND estado = 'activo'
        """, (hoy, usuario.id))
        
        if cursor.rowcount > 0:
            conn.commit()
            await interaction.followup.send(f"✅ Pago registrado para {usuario.mention}. El aviso se ha limpiado.")
        else:
            await interaction.followup.send("❌ No se encontró un contrato activo.")
        
        conn.close()
        
    @app_commands.command(name="agendar_trabajador", description="Registra un nuevo empleado en el banco")
    @app_commands.describe(
        usuario="El usuario de Discord del trabajador",
        nombre_ic="Nombre y Apellido IC",
        edad_ic="Edad del personaje",
        area="Área de trabajo (Seguridad, Caja, etc.)",
        pago="Monto del pago periodico",
        contrato="Archivo PDF del contrato"
    )
    async def agendar_trabajador(
        self, 
        interaction: discord.Interaction, 
        usuario: discord.Member,
        nombre_ic: str, 
        edad_ic: int, 
        area: str, 
        pago: int, 
        contrato: discord.Attachment
    ):
        # Ganamos tiempo para procesar el archivo y la DB
        await interaction.response.defer(ephemeral=True)

        # 1. Validar que sea un PDF
        if not contrato.filename.lower().endswith(".pdf"):
            return await interaction.followup.send("❌ El contrato debe ser un archivo **PDF**.")

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        fecha_hoy = datetime.datetime.now().strftime("%Y-%m-%d")

        try:
            # 2. Insertar en la base de datos
            cursor.execute("""
                INSERT INTO empleados (user_id, nombre_ic, edad_ic, area_trabajo, pago_periodico, contrato_url, fecha_ingreso)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (usuario.id, nombre_ic, edad_ic, area, pago, contrato.url, fecha_hoy))
            
            conn.commit()
            
            # 3. Respuesta para el administrador
            embed = discord.Embed(title="✅ Trabajador Registrado", color=discord.Color.green())
            embed.add_field(name="Empleado", value=usuario.mention, inline=True)
            embed.add_field(name="Nombre IC", value=nombre_ic, inline=True)
            embed.add_field(name="Área", value=area, inline=True)
            embed.add_field(name="Sueldo", value=f"€{pago} (cada dos días)", inline=True)
            embed.add_field(name="Contrato", value=f"[Enlace al PDF]({contrato.url})", inline=False)
            
            await interaction.followup.send(embed=embed)

            # 4. DM automático al trabajador
            try:
                dm_embed = discord.Embed(
                    title="🏦 BIENVENIDO/A AL EQUIPO DE AURUM BANK",
                    description=f"Hola **{nombre_ic}**, tu contrato ha sido firmado y registrado correctamente.",
                    color=0xF1C40F
                )
                dm_embed.add_field(name="📍 Área", value=area, inline=True)
                dm_embed.add_field(name="💰 Sueldo", value=f"€{pago} (Cada 2 días)", inline=True)
                dm_embed.add_field(name="📄 Contrato", value=f"[Descargar aquí]({contrato.url})", inline=False)
                dm_embed.set_footer(text="Cualquier duda, contacta con recursos humanos.")
                
                await usuario.send(embed=dm_embed)
            except:
                await interaction.followup.send("⚠️ No pude enviar el DM al trabajador (mensajes cerrados).")

            # 5. Log en el canal de logs
            log_trabajadores = discord.utils.get(interaction.guild.text_channels, name="🙍・logs-trabajadores")
            if log_trabajadores:
                await log_trabajadores.send(content=f"📥 **Nueva Alta Laboral - {nombre_ic}**", embed=embed)
            else:
                await interaction.followup.send("⚠️ Nota: No se encontró el canal `🙍・logs-trabajadores` para enviar el reporte.")

        except Exception as e:
            await interaction.followup.send(f"❌ Error crítico: {e}")
        finally:
            conn.close()

    @app_commands.command(name="dar_de_baja", description="Da de baja a un trabajador del sistema")
    @app_commands.describe(usuario="El usuario de Discord a despedir", motivo="Razón de la baja")
    async def dar_de_baja(self, interaction: discord.Interaction, usuario: discord.Member, motivo: str):
        await interaction.response.defer(ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Buscar si el trabajador existe y está activo
        cursor.execute("SELECT nombre_ic FROM empleados WHERE user_id = ? AND estado = 'activo'", (usuario.id,))
        resultado = cursor.fetchone()

        if not resultado:
            conn.close()
            return await interaction.followup.send(f"❌ No encontré un contrato activo para {usuario.mention}.")

        nombre_ic = resultado[0]

        # Cambiar estado a inactivo
        cursor.execute("UPDATE empleados SET estado = 'inactivo' WHERE user_id = ?", (usuario.id,))
        conn.commit()
        conn.close()

        # Respuesta y DM
        embed = discord.Embed(title="🚫 Baja Laboral Procesada", color=discord.Color.red())
        embed.add_field(name="Trabajador", value=f"{nombre_ic} ({usuario.mention})", inline=False)
        embed.add_field(name="Motivo", value=motivo, inline=False)
        
        await interaction.followup.send(embed=embed)

        try:
            dm_baja = discord.Embed(
                title="⚠️ FIN DE CONTRATO | AURUM BANK",
                description=f"Se te comunica que has sido dado de baja de la empresa.\n**Motivo:** {motivo}",
                color=0xE74C3C
            )
            await usuario.send(embed=dm_baja)
        except:
            pass

        # Log
        log_channel = discord.utils.get(interaction.guild.text_channels, name="🧾・logs-aurum")
        if log_channel:
            await log_channel.send(f"⚠️ **Baja:** {usuario.mention} ha dejado de trabajar en el banco. Motivo: {motivo}")

    @app_commands.command(name="lista_empleados", description="Muestra la lista de trabajadores activos")
    async def lista_empleados(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("SELECT nombre_ic, area_trabajo, pago_periodico FROM empleados WHERE estado = 'activo'")
        empleados = cursor.fetchall()
        conn.close()

        if not empleados:
            return await interaction.followup.send("No hay trabajadores registrados actualmente.")

        embed = discord.Embed(title="👥 Plantilla de Aurum Bank", color=discord.Color.blue())
        
        lista_texto = ""
        total_pagos = 0
        for nombre, area, pago in empleados:
            lista_texto += f"• **{nombre}** - {area} (€{pago})\n"
            total_pagos += pago

        embed.description = lista_texto
        embed.add_field(name="📊 Gastos cada dos días", value=f"€{total_pagos}", inline=False)
        
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Empleos(bot))
import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime

class Economia(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db_path = "aurum.db"

    def get_db(self):
        return sqlite3.connect(self.db_path)

    async def registrar_transaccion(self, user_id, tipo, monto):
        conn = self.get_db()
        cursor = conn.cursor()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            INSERT INTO historial_transacciones (user_id, tipo, monto, fecha)
            VALUES (?, ?, ?, ?)
        """, (user_id, tipo, monto, ahora))
        conn.commit()
        conn.close()

    @app_commands.command(name="depositar", description="Ingresa dinero en la cuenta de un usuario")
    @app_commands.describe(usuario="Titular de la cuenta", monto="Cantidad a ingresar")
    @app_commands.checks.has_permissions(administrator=True)
    async def depositar(self, interaction: discord.Interaction, usuario: discord.Member, monto: int):
        if monto <= 0:
            return await interaction.response.send_message("❌ El monto debe ser positivo.", ephemeral=True)

        await interaction.response.defer()
        conn = self.get_db()
        cursor = conn.cursor()
        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO cuentas (user_id, saldo, ultima_actualizacion) 
            VALUES (?, ?, ?)
            ON CONFLICT(user_id) DO UPDATE SET 
            saldo = saldo + excluded.saldo,
            ultima_actualizacion = excluded.ultima_actualizacion
        """, (usuario.id, monto, ahora))
        conn.commit()
        
        cursor.execute("SELECT saldo FROM cuentas WHERE user_id = ?", (usuario.id,))
        nuevo_saldo = cursor.fetchone()[0]
        conn.close()

        await self.registrar_transaccion(usuario.id, 'deposito', monto)

        # --- LOGS EN CANAL ESPECÍFICO ---
        log_channel = discord.utils.get(interaction.guild.text_channels, name="🌐・logs-depositos-retiros")
        embed_log = discord.Embed(title="📥 NUEVO DEPÓSITO", color=discord.Color.green(), timestamp=datetime.datetime.now())
        embed_log.add_field(name="Empleado", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="Cliente", value=usuario.mention, inline=True)
        embed_log.add_field(name="Monto", value=f"€{monto}", inline=True)
        embed_log.add_field(name="Saldo Final", value=f"€{nuevo_saldo}", inline=True)
        
        if log_channel:
            await log_channel.send(embed=embed_log)

        # --- AVISO POR MD AL USUARIO ---
        try:
            dm_embed = discord.Embed(title="🏦 Aurum Bank - Ingreso Recibido", color=0x2ECC71)
            dm_embed.description = f"Se ha depositado **€{monto}** en tu cuenta."
            dm_embed.add_field(name="Saldo Actual", value=f"€{nuevo_saldo}")
            dm_embed.set_footer(text="Gracias por confiar en Aurum Bank.")
            await usuario.send(embed=dm_embed)
        except:
            pass 

        await interaction.followup.send(f"✅ Depósito de €{monto} registrado para {usuario.mention}.")

    @app_commands.command(name="retirar", description="Retira dinero de la cuenta de un usuario")
    @app_commands.describe(usuario="Titular de la cuenta", monto="Cantidad a extraer")
    @app_commands.checks.has_permissions(administrator=True)
    async def retirar(self, interaction: discord.Interaction, usuario: discord.Member, monto: int):
        if monto <= 0:
            return await interaction.response.send_message("❌ El monto debe ser positivo.", ephemeral=True)

        await interaction.response.defer()
        conn = self.get_db()
        cursor = conn.cursor()

        cursor.execute("SELECT saldo FROM cuentas WHERE user_id = ?", (usuario.id,))
        resultado = cursor.fetchone()

        if not resultado or resultado[0] < monto:
            conn.close()
            return await interaction.followup.send(f"❌ Saldo insuficiente. (Disponible: €{resultado[0] if resultado else 0})")

        ahora = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE cuentas SET saldo = saldo - ?, ultima_actualizacion = ? WHERE user_id = ?", (monto, ahora, usuario.id))
        conn.commit()
        nuevo_saldo = resultado[0] - monto
        conn.close()

        await self.registrar_transaccion(usuario.id, 'retiro', monto)

        # --- LOGS EN CANAL ESPECÍFICO ---
        log_channel = discord.utils.get(interaction.guild.text_channels, name="🌐・logs-depositos-retiros")
        embed_log = discord.Embed(title="📤 NUEVO RETIRO", color=discord.Color.red(), timestamp=datetime.datetime.now())
        embed_log.add_field(name="Empleado", value=interaction.user.mention, inline=True)
        embed_log.add_field(name="Cliente", value=usuario.mention, inline=True)
        embed_log.add_field(name="Monto", value=f"€{monto}", inline=True)
        embed_log.add_field(name="Saldo Restante", value=f"€{nuevo_saldo}", inline=True)
        
        if log_channel:
            await log_channel.send(embed=embed_log)

        # --- AVISO POR MD AL USUARIO ---
        try:
            dm_embed = discord.Embed(title="🏦 Aurum Bank - Retiro Realizado", color=0xE74C3C)
            dm_embed.description = f"Se ha retirado **€{monto}** de tu cuenta."
            dm_embed.add_field(name="Saldo Restante", value=f"€{nuevo_saldo}")
            await usuario.send(embed=dm_embed)
        except:
            pass

        await interaction.followup.send(f"✅ Retiro de €{monto} registrado para {usuario.mention}.")

async def setup(bot):
    await bot.add_cog(Economia(bot))
from discord.ext import commands
import discord
import sqlite3
import os
from datetime import datetime
from discord import app_commands


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

        # Base de datos
        os.makedirs("./database", exist_ok=True)
        self.db = sqlite3.connect("./database/warnings.db")
        self.cursor = self.db.cursor()

        # Tabla warnings
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS warnings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                moderator_id INTEGER,
                reason TEXT,
                timestamp TEXT
            )
        """)

        # Tabla config
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS config (
                guild_id INTEGER,
                log_channel_id INTEGER
            )
        """)

        self.db.commit()

    # -------------------------------------------------------------
    # ENVÍO DE LOGS
    # -------------------------------------------------------------
    
    async def send_log(self, guild, embed):
        self.cursor.execute(
            "SELECT log_channel_id FROM config WHERE guild_id = ?",
            (guild.id,)
        )
        data = self.cursor.fetchone()
        if not data:
            return

        channel_id = data[0]

        channel = self.bot.get_channel(channel_id)

        if channel is None:
            channel = discord.utils.get(guild.text_channels, id=channel_id)

        if channel:
            try:
                await channel.send(embed=embed)
            except discord.Forbidden:
                print(f"No tengo permisos para enviar mensajes en {channel.name}")

    # -------------------------------------------------------------
    # SET LOG CHANNEL
    # -------------------------------------------------------------
    @app_commands.command(
        name="setlogchannel",
        description="Configura el canal donde se enviarán los logs."
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def setlogchannel(self, interaction: discord.Interaction, channel: discord.TextChannel):

        self.cursor.execute("DELETE FROM config WHERE guild_id = ?", (interaction.guild.id,))
        self.cursor.execute(
            "INSERT INTO config (guild_id, log_channel_id) VALUES (?, ?)",
            (interaction.guild.id, channel.id)
        )
        self.db.commit()

        embed = discord.Embed(
            title="📌 Canal de logs configurado",
            description=f"Los logs ahora se enviarán a {channel.mention}",
            color=discord.Color.green()
        )

        await interaction.response.send_message(embed=embed)

    # -------------------------------------------------------------
    async def send_log(self, guild, embed):
        self.cursor.execute(
            "SELECT log_channel_id FROM config WHERE guild_id = ?",
            (guild.id,)
        )
        data = self.cursor.fetchone()

        if not data:
            return
        
        channel = guild.get_channel(data[0])
        if channel:
            await channel.send(embed=embed)

    # -------------------------------------------------------------
    # WARN
    # -------------------------------------------------------------
    @app_commands.command(
        name="warn",
        description="Warnear a un usuario."
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def warn(self, interaction: discord.Interaction, member: discord.Member, reason: str = "No especificado"):

        fecha = datetime.now().strftime("%d/%m/%Y %H:%M")

        # Guardar en DB
        self.cursor.execute(
            "INSERT INTO warnings (user_id, moderator_id, reason, timestamp) VALUES (?, ?, ?, ?)",
            (member.id, interaction.user.id, reason, fecha)
        )
        self.db.commit()

        embed_staff = discord.Embed(
            title="⚠️ Usuario advertido",
            description=f"{member.mention} recibió una advertencia.",
            color=discord.Color.yellow()
        )
        embed_staff.add_field(name="👮 Moderador", value=interaction.user.mention, inline=False)
        embed_staff.add_field(name="📄 Motivo", value=reason, inline=False)
        embed_staff.add_field(name="📅 Fecha", value=fecha, inline=False)

        await interaction.response.send_message(embed=embed_staff, ephemeral=True)

        try:
            embed_dm = discord.Embed(
                title="⚠️ Has sido advertido",
                description=f"Recibiste una advertencia en **{interaction.guild.name}**.",
                color=discord.Color.orange()
            )
            embed_dm.add_field(name="📄 Motivo", value=reason, inline=False)
            embed_dm.add_field(name="👮 Moderador", value=interaction.user.name, inline=False)
            embed_dm.add_field(name="📅 Fecha", value=fecha, inline=False)

            await member.send(embed=embed_dm)
        except:
            pass

        embed_log = discord.Embed(
            title="📒 Log | Nueva advertencia",
            color=discord.Color.orange()
        )
        embed_log.add_field(name="👤 Usuario", value=f"{member} ({member.id})", inline=False)
        embed_log.add_field(name="👮 Moderador", value=f"{interaction.user} ({interaction.user.id})", inline=False)
        embed_log.add_field(name="📄 Motivo", value=reason, inline=False)
        embed_log.add_field(name="📅 Fecha", value=fecha, inline=False)

        await self.send_log(interaction.guild, embed_log)

    # -------------------------------------------------------------
    # VER WARNS
    # -------------------------------------------------------------
    @app_commands.command(
        name="unwarn",
        description="Ver las advertencias de un usuario."
    )
    async def warnings(self, interaction: discord.Interaction, member: discord.Member):

        self.cursor.execute(
            "SELECT id, moderator_id, reason, timestamp FROM warnings WHERE user_id = ?",
            (member.id,)
        )
        datos = self.cursor.fetchall()

        if not datos:
            embed = discord.Embed(
                title="✔️ Sin advertencias",
                description=f"{member.mention} no tiene warns.",
                color=discord.Color.green()
            )
            return await interaction.response.send_message(embed=embed, ephemeral= True)

        embed = discord.Embed(
            title=f"Advertencias de {member}",
            color=discord.Color.red()
        )

        for warn_id, mod_id, reason, fecha in datos:
            embed.add_field(
                name=f"⚠️ Warn #{warn_id}",
                value=f"**Motivo:** {reason}\n**Fecha:** {fecha}\n**Moderador:** <@{mod_id}>",
                inline=False
            )

        await interaction.response.send_message(embed=embed, ephemeral=True)

    # -------------------------------------------------------------
    # REMOVE WARN
    # -------------------------------------------------------------
    @app_commands.command(
        name="sacar-warn",
        description="Eliminar un warn por ID."
    )
    @app_commands.checks.has_permissions(manage_messages=True)
    async def removewarn(self, interaction: discord.Interaction, warn_id: int):

        self.cursor.execute(
            "SELECT user_id, moderator_id, reason, timestamp FROM warnings WHERE id = ?",
            (warn_id,)
        )
        warn = self.cursor.fetchone()

        if not warn:
            return await interaction.response.send_message("⚠️ Ese warn no existe.")

        user_id, mod_id, reason, fecha = warn
        self.cursor.execute("DELETE FROM warnings WHERE id = ?", (warn_id,))
        self.db.commit()

        embed = discord.Embed(
            title="🗑️ Advertencia eliminada",
            description=f"Warn #{warn_id} fue eliminado.",
            color=discord.Color.blue()
        )
        await interaction.response.send_message(embed=embed, ephemeral=True)

        embed_log = discord.Embed(
            title="📒 Log | Warn eliminado",
            color=discord.Color.blue()
        )
        embed_log.add_field(name="Warn ID", value=warn_id)
        embed_log.add_field(name="Usuario", value=f"<@{user_id}> ({user_id})")
        embed_log.add_field(name="Moderador original", value=f"<@{mod_id}>")
        embed_log.add_field(name="Motivo", value=reason)
        embed_log.add_field(name="Fecha del warn", value=fecha)
        embed_log.add_field(name="Eliminado por", value=interaction.user.mention, inline=False)

        await self.send_log(interaction.guild, embed_log)


async def setup(bot):
    await bot.add_cog(Moderation(bot))

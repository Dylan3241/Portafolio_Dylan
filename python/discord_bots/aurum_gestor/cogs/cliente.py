import discord
from discord.ext import commands
from discord import app_commands
import datetime
import sqlite3

ROLES_PERMITIDOS = [
    "𝐂𝐄𝐎 | Director General",
    "𝐂𝐅𝐎 | Director Financiero",
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]

TIPOS_CUENTA = {
    "basica": "Cliente Básico",
    "premium": "Cliente Premium",
    "vip": "Cliente VIP"
}

class Clientes(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= CREAR CUENTA =================
    @app_commands.command(name="crear_cuenta", description="Crear cuenta a un cliente")
    @app_commands.describe(
        usuario="Usuario",
        tipo="Tipo de cuenta (basica/premium/vip)"
    )
    @app_commands.choices(tipo=[
        app_commands.Choice(name="Básica", value="basica"),
        app_commands.Choice(name="Premium", value="premium"),
        app_commands.Choice(name="VIP", value="vip")
    ])
    async def crear_cuenta(self, interaction: discord.Interaction, usuario: discord.Member, tipo: app_commands.Choice[str]):

        # 🔒 Verificar roles
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
            return

        # Verificar si ya tiene cuenta
        self.cursor.execute("SELECT * FROM clientes WHERE user_id = ?", (usuario.id,))
        if self.cursor.fetchone():
            await interaction.response.send_message("❌ Ya tiene cuenta.", ephemeral=True)
            return

        tipo_cuenta = tipo.value

        # Crear cuenta
        self.cursor.execute(
            "INSERT INTO clientes (user_id, tiene_cuenta, saldo, rol, fecha_registro) VALUES (?, ?, ?, ?, ?)",
            (usuario.id, True, 0, tipo_cuenta, str(datetime.datetime.now()))
        )
        self.conn.commit()

        # 📥 LOG
        log_channel = discord.utils.get(
            interaction.guild.text_channels,
            name="📥・𝐥𝐨𝐠𝐬-𝐜𝐮𝐞𝐧𝐭𝐚𝐬"
        )

        if log_channel:
            embed_log = discord.Embed(
                title="📥 Cuenta bancaria creada",
                color=0x2ECC71
            )

            embed_log.add_field(name="👤 Usuario", value=usuario.mention, inline=False)
            embed_log.add_field(name="💳 Tipo de cuenta", value=tipo.name, inline=True)
            embed_log.add_field(name="🏦 Creada por", value=interaction.user.mention, inline=True)
            embed_log.add_field(name="📅 Fecha", value=str(datetime.datetime.now()), inline=False)

            await log_channel.send(embed=embed_log)

        # 🎭 Asignar rol Discord
        nombre_rol = TIPOS_CUENTA[tipo_cuenta]
        rol = discord.utils.get(usuario.guild.roles, name=nombre_rol)

        if rol:
            await usuario.add_roles(rol)

        # 📩 Embed
        embed = discord.Embed(
            title="🏦 Cuenta creada",
            description=f"Se creó la cuenta de {usuario.mention}",
            color=0x2ECC71
        )

        embed.add_field(name="💳 Tipo", value=tipo.name, inline=True)
        embed.add_field(name="💰 Saldo", value="€0", inline=True)

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Clientes(bot))
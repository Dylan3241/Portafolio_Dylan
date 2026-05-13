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

class Prestamos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= CREAR PRESTAMO =================
    @app_commands.command(name="crear_prestamo", description="Crear un préstamo")
    @app_commands.describe(usuario="Cliente", monto="Cantidad de dinero")
    async def crear_prestamo(self, interaction: discord.Interaction, usuario: discord.Member, monto: int):

        # 🔒 Permisos
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
            return

        # 📊 Ver cliente
        self.cursor.execute("SELECT * FROM clientes WHERE user_id = ?", (usuario.id,))
        cliente = self.cursor.fetchone()

        if not cliente:
            await interaction.response.send_message("❌ El usuario no tiene cuenta.", ephemeral=True)
            return

        _, _, saldo, tipo, _ = cliente

        # 📈 Validar límite
        if monto > LIMITES[tipo]:
            await interaction.response.send_message(
                f"❌ Supera el límite de {tipo.upper()} (€{LIMITES[tipo]})",
                ephemeral=True
            )
            return

        # 🔁 Validar préstamos activos
        self.cursor.execute(
            "SELECT COUNT(*) FROM prestamos WHERE user_id = ? AND estado = 'activo'",
            (usuario.id,)
        )
        activos = self.cursor.fetchone()[0]

        if activos >= MAX_PRESTAMOS[tipo]:
            await interaction.response.send_message(
                "❌ Ya alcanzó el máximo de préstamos activos.",
                ephemeral=True
            )
            return

        # 💰 Calcular interés
        interes = INTERESES[tipo]
        total = int(monto + (monto * interes))

        fecha_limite = datetime.datetime.now() + datetime.timedelta(days=7)

        # 💾 Guardar préstamo
        self.cursor.execute(
            "INSERT INTO prestamos (user_id, monto, interes, total_pagar, estado, fecha_limite) VALUES (?, ?, ?, ?, ?, ?)",
            (usuario.id, monto, interes, total, "activo", str(fecha_limite))
        )
        self.conn.commit()

        # 📩 Embed
        embed = discord.Embed(
            title="💸 Préstamo aprobado",
            color=0x2ECC71
        )

        embed.add_field(name="👤 Cliente", value=usuario.mention, inline=False)
        embed.add_field(name="💰 Monto", value=f"€{monto}", inline=True)
        embed.add_field(name="📈 Interés", value=f"{int(interes*100)}%", inline=True)
        embed.add_field(name="💵 Total a pagar", value=f"€{total}", inline=False)
        embed.add_field(name="📅 Límite", value=fecha_limite.strftime("%d/%m/%Y"), inline=False)

        await interaction.response.send_message(embed=embed)

        # 📩 Enviar MD al cliente
        try:
            dm_embed = discord.Embed(
                title="🏦 Préstamo aprobado",
                description="Tu solicitud de préstamo ha sido aprobada.",
                color=0x2ECC71
            )

            log_channel = discord.utils.get(
                interaction.guild.text_channels,
                name="💰・𝐥𝐨𝐠𝐬-𝐩𝐫𝐞𝐬𝐭𝐚𝐦𝐨𝐬"
            )

            if log_channel:
                embed_log = discord.Embed(
                    title="💰 Prestamo registrado",
                    color=0x3498DB
                )

            dm_embed.add_field(name="💰 Monto", value=f"€{monto}", inline=True)
            dm_embed.add_field(name="📈 Interés", value=f"{int(interes*100)}%", inline=True)
            dm_embed.add_field(name="💵 Total a pagar", value=f"€{total}", inline=False)
            dm_embed.add_field(name="📅 Fecha límite", value=fecha_limite.strftime("%d/%m/%Y"), inline=False)

            dm_embed.set_footer(text="Aurum Bank")

            embed.add_field(
                name="📩 Notificación",
                value="Se ha enviado un mensaje privado al cliente.",
                inline=False,
                ephemeral=True
            )

            await usuario.send(embed=dm_embed)

        except:
            await interaction.followup.send(
                    f"⚠️ No se pudo enviar MD a {usuario.mention}.",
                    ephemeral=True
                )


async def setup(bot):
    await bot.add_cog(Prestamos(bot))
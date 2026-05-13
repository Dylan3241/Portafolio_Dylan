import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

CANAL_PAGOS = "💸・pagos-prestamo"

ROLES_PERMITIDOS = [
    "𝐂𝐄𝐎 | Director General",
    "𝐂𝐅𝐎 | Director Financiero",
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]

class Pagos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= PAGAR PRESTAMO =================
    @app_commands.command(name="pagar_prestamo", description="Registrar pago de préstamo")
    @app_commands.describe(usuario="Cliente", monto="Cantidad a pagar")
    async def pagar_prestamo(self, interaction: discord.Interaction, usuario: discord.Member, monto: int):

        # 🔒 Verificar canal
        if interaction.channel.name != CANAL_PAGOS:
            await interaction.response.send_message(
                "❌ Este comando solo se puede usar en el canal de pagos.",
                ephemeral=True
            )
            return

        # 🔒 Verificar roles (STAFF)
        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.response.send_message(
                "❌ No tienes permisos.",
                ephemeral=True
            )
            return

        # 📊 Buscar préstamo activo
        self.cursor.execute(
            "SELECT id, total_pagar FROM prestamos WHERE user_id = ? AND estado = 'activo'",
            (usuario.id,)
        )
        prestamo = self.cursor.fetchone()

        if not prestamo:
            await interaction.response.send_message(
                "❌ El usuario no tiene préstamos activos.",
                ephemeral=True
            )
            return

        prestamo_id, total_pagar = prestamo

        # 💰 Validar pago
        monto_real = min(monto, total_pagar)
        restante = total_pagar - monto_real

        estado = "pagado" if restante <= 0 else "activo"

        # 💾 Actualizar préstamo
        self.cursor.execute(
            "UPDATE prestamos SET total_pagar = ?, estado = ? WHERE id = ?",
            (restante, estado, prestamo_id)
        )

        # 💾 Actualizar saldo interno
        self.cursor.execute(
            "UPDATE clientes SET saldo = saldo - ? WHERE user_id = ?",
            (monto_real, usuario.id)
        )

        self.conn.commit()

        # 📩 Embed staff
        embed = discord.Embed(
            title="💸 Pago registrado",
            color=0x3498DB
        )

        log_channel = discord.utils.get(
        interaction.guild.text_channels,
        name="📤・𝐥𝐨𝐠𝐬-𝐩𝐚𝐠𝐨𝐬"
    )

        if log_channel:
            embed_log = discord.Embed(
                title="📤 Pago de préstamo registrado",
                color=0x3498DB
            )

        embed.add_field(name="👤 Cliente", value=usuario.mention, inline=False)
        embed.add_field(name="💰 Pagado", value=f"€{monto_real}", inline=True)
        embed.add_field(name="📉 Restante", value=f"€{restante}", inline=True)
        embed.add_field(name="📊 Estado", value=estado.capitalize(), inline=False)

        await interaction.response.send_message(embed=embed)

        # 📩 MD cliente
        try:
            dm = discord.Embed(
                title="🏦 Pago procesado",
                description="Tu pago ha sido registrado por el banco.",
                color=0x3498DB
            )

            dm.add_field(name="💰 Pagado", value=f"€{monto_real}", inline=True)
            dm.add_field(name="📉 Restante", value=f"€{restante}", inline=True)
            dm.add_field(name="📊 Estado", value=estado.capitalize(), inline=False)

            await usuario.send(embed=dm)

        except:
            pass

async def setup(bot):
    await bot.add_cog(Pagos(bot))
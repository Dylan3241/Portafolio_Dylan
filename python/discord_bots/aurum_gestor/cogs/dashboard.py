import discord
from discord.ext import commands
from discord import app_commands
import sqlite3

ROLES_PERMITIDOS = [
    "𝐂𝐄𝐎 | Director General",
    "𝐂𝐅𝐎 | Director Financiero",
    "𝐀𝐠𝐞𝐧𝐭𝐞 Bancario"
]

class Dashboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

    # ================= DASHBOARD =================
    @app_commands.command(name="dashboard", description="Panel financiero del banco Aurum")
    async def dashboard(self, interaction: discord.Interaction):

        if not any(role.name in ROLES_PERMITIDOS for role in interaction.user.roles):
            await interaction.response.send_message("❌ No tienes permisos.", ephemeral=True)
            return

        # 📊 CLIENTES
        self.cursor.execute("SELECT COUNT(*) FROM clientes")
        clientes = self.cursor.fetchone()[0]

        # 💸 PRÉSTAMOS ACTIVOS
        self.cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'activo'")
        prestamos_activos = self.cursor.fetchone()[0]

        # 🚨 MOROSOS
        self.cursor.execute("SELECT COUNT(*) FROM prestamos WHERE estado = 'moroso'")
        morosos = self.cursor.fetchone()[0]

        # 💰 DINERO PRESTADO
        self.cursor.execute("SELECT SUM(total_pagar) FROM prestamos WHERE estado = 'activo'")
        prestado = self.cursor.fetchone()[0] or 0

        # 💵 INGRESOS (pagados)
        self.cursor.execute("SELECT SUM(total_pagar) FROM prestamos WHERE estado = 'pagado'")
        ingresos = self.cursor.fetchone()[0] or 0

        # 🚨 ALERTA AUTOMÁTICA
        alerta = "🟢 Sistema estable"

        if morosos > 5:
            alerta = "🔴 ALERTA: muchos morosos activos"
        elif prestamos_activos > 20:
            alerta = "🟡 Alto volumen de préstamos"

        # 🏆 TOP CLIENTES (mejores pagadores)
        self.cursor.execute("""
            SELECT user_id, SUM(total_pagar)
            FROM prestamos
            WHERE estado = 'pagado'
            GROUP BY user_id
            ORDER BY SUM(total_pagar) DESC
            LIMIT 5
        """)
        top = self.cursor.fetchall()

        top_texto = ""
        for i, (user_id, total) in enumerate(top, 1):
            top_texto += f"{i}. <@{user_id}> — €{total}\n"

        if not top_texto:
            top_texto = "Sin datos aún"

        # 📈 EMBED
        embed = discord.Embed(
            title="🏦 AURUM BANK — DASHBOARD",
            description="Panel financiero avanzado del sistema",
            color=0x2ECC71
        )

        embed.add_field(name="👥 Clientes", value=clientes, inline=True)
        embed.add_field(name="💸 Préstamos activos", value=prestamos_activos, inline=True)
        embed.add_field(name="🚨 Morosos", value=morosos, inline=True)

        embed.add_field(name="💰 Dinero prestado", value=f"€{prestado}", inline=False)
        embed.add_field(name="💵 Ingresos (pagados)", value=f"€{ingresos}", inline=False)

        embed.add_field(name="🚨 Estado del sistema", value=alerta, inline=False)

        embed.add_field(name="🏆 Top clientes", value=top_texto, inline=False)

        embed.set_footer(text="Aurum Bank • Financial Core System")

        await interaction.response.send_message(embed=embed)

async def setup(bot):
    await bot.add_cog(Dashboard(bot))
import discord
from discord.ext import commands, tasks
import sqlite3
import datetime

ROLES_BLACKLIST = "🚫 Blacklist"

INTERES_MORA = 0.05  # +5% extra por atraso

class Morosos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.conn = sqlite3.connect("aurum.db")
        self.cursor = self.conn.cursor()

        self.verificar_morosos.start()

    # ================= TAREA AUTOMATICA =================
    @tasks.loop(hours=1)
    async def verificar_morosos(self):
        ahora = datetime.datetime.now()

        self.cursor.execute(
            "SELECT id, user_id, total_pagar, fecha_limite FROM prestamos WHERE estado = 'activo'"
        )
        prestamos = self.cursor.fetchall()

        for prestamo_id, user_id, total, fecha_limite in prestamos:

            fecha_limite_dt = datetime.datetime.fromisoformat(fecha_limite)

            if ahora > fecha_limite_dt:

                # 💰 aplicar interés por mora
                nuevo_total = int(total + (total * INTERES_MORA))

                self.cursor.execute(
                    "UPDATE prestamos SET total_pagar = ? WHERE id = ?",
                    (nuevo_total, prestamo_id)
                )

                self.conn.commit()

                guild = self.bot.guilds[0]
                usuario = guild.get_member(user_id)

                # 🚫 marcar blacklist (opcional)
                role = discord.utils.get(guild.roles, name=ROLES_BLACKLIST)
                if usuario and role:
                    await usuario.add_roles(role)

                # 🧾 LOGS
                log = discord.utils.get(guild.text_channels, name="🧾・logs-aurum")
                if log:
                    await log.send(
                        f"⚠️ {usuario.mention if usuario else user_id} entró en MORA | Nuevo total: €{nuevo_total}"
                    )

                # 📩 DM usuario
                if usuario:
                    try:
                        embed = discord.Embed(
                            title="⚠️ Préstamo en mora",
                            description="Has incumplido la fecha de pago.",
                            color=0xE74C3C
                        )

                        embed.add_field(
                            name="📈 Nuevo monto",
                            value=f"€{nuevo_total}",
                            inline=True
                        )

                        embed.add_field(
                            name="⚠️ Penalización",
                            value=f"+{int(INTERES_MORA*100)}% interés",
                            inline=True
                        )

                        embed.add_field(
                            name="🚨 Advertencia",
                            value="Si no regularizas tu situación, podrías ser sancionado o denunciado en el sistema del servidor.",
                            inline=False
                        )

                        await usuario.send(embed=embed)

                    except:
                        pass

    @verificar_morosos.before_loop
    async def before(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Morosos(bot))
import discord
from discord.ext import commands

class Bienvenida(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_join(self, member):
        role_civil = discord.utils.get(member.guild.roles, name="🙍 Civil")
        role_user = discord.utils.get(member.guild.roles, name="---- Cliente ----")

        if role_civil:
            await member.add_roles(role_civil)
        if role_user:
            await member.add_roles(role_user)

        canal = discord.utils.get(member.guild.text_channels, name="📜・𝐛𝐢𝐞𝐧𝐯𝐞𝐧𝐢𝐝𝐚")

        if canal:
            embed = discord.Embed(
                title="🏦 Bienvenido a Aurum Bank",
                description=f"Bienvenido {member.mention} al sistema financiero del servidor.",
                color=0xFFD700
            )

            embed.add_field(
                name="💼 Crear Cuenta",
                value="Dirígete a `📨・soporte-bancario` y abre un ticket con el botón correspondiente.",
                inline=False
            )

            embed.add_field(
                name="📥 Préstamos",
                value="Solicita préstamos mediante tickets. Nuestro equipo evaluará tu solicitud.",
                inline=False
            )

            embed.add_field(
                name="📊 Tasas y Servicios",
                value="Consulta todas las tasas en `📊・tasas-y-servicios`.",
                inline=False
            )

            embed.add_field(
                name="📖 Normativa",
                value="Lee las reglas en `📖・normativa` para evitar sanciones.",
                inline=False
            )

            embed.set_footer(text="Aurum Bank • Sistema Financiero")
            embed.set_thumbnail(url=member.avatar.url if member.avatar else member.default_avatar.url)

            await canal.send(embed=embed)

        # Log
        log_channel = discord.utils.get(member.guild.text_channels, name="🧾・logs-aurum")
        if log_channel:
            await log_channel.send(f"👤 {member.mention} se unió al servidor.")

async def setup(bot):
    await bot.add_cog(Bienvenida(bot))
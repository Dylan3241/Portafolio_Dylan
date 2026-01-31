import discord
from discord import app_commands
from discord.ext import commands

LOG_CHANNEL_ID = 1443062286502727691  # Canal de logs


class AdminCommands(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    # ----------------------------------------------------
    # KICK
    # ----------------------------------------------------
    @app_commands.command(name="kick", description="Expulsa a un usuario del servidor.")
    @app_commands.describe(usuario="Usuario a expulsar", razon="Razón del kick")
    async def kick(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "No especificada"):
        if not interaction.user.guild_permissions.kick_members:
            return await interaction.response.send_message("❌ No tenés permisos para usar este comando.", ephemeral=True)

        embed = discord.Embed(
            title="🔨 Usuario Expulsado",
            description=f"**Usuario:** {usuario.mention}\n**Razón:** {razon}",
            color=discord.Color.orange()
        )
        embed.set_footer(text=f"Acción ejecutada por {interaction.user}", icon_url=interaction.user.display_avatar.url)

        try:
            await usuario.send(f"Fuiste expulsado de **{interaction.guild.name}**.\nRazón: **{razon}**")
        except:
            pass

        await usuario.kick(reason=razon)
        await interaction.response.send_message(embed=embed)

        # Logs
        await self.send_log(embed)

    # ----------------------------------------------------
    # BAN
    # ----------------------------------------------------
    @app_commands.command(name="ban", description="Banea a un usuario del servidor.")
    @app_commands.describe(usuario="Usuario a banear", razon="Razón del ban")
    async def ban(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "No especificada"):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ No tenés permisos para usar este comando.", ephemeral=True)

        embed = discord.Embed(
            title="⛔ Usuario Baneado",
            description=f"**Usuario:** {usuario.mention}\n**Razón:** {razon}",
            color=discord.Color.red()
        )
        embed.set_footer(text=f"Baneado por {interaction.user}", icon_url=interaction.user.display_avatar.url)

        try:
            await usuario.send(f"Fuiste baneado de **{interaction.guild.name}**.\nRazón: **{razon}**")
        except:
            pass

        await usuario.ban(reason=razon)
        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    # ----------------------------------------------------
    # UNBAN
    # ----------------------------------------------------
    @app_commands.command(name="unban", description="Desbanea a un usuario por ID.")
    @app_commands.describe(user_id="ID del usuario a desbanear")
    async def unban(self, interaction: discord.Interaction, user_id: str):
        if not interaction.user.guild_permissions.ban_members:
            return await interaction.response.send_message("❌ No tenés permisos para usar este comando.", ephemeral=True)

        try:
            user_id = int(user_id)
            user = await self.bot.fetch_user(user_id)
            await interaction.guild.unban(user)

            embed = discord.Embed(
                title="🔓 Usuario Desbaneado",
                description=f"**Usuario:** {user} (ID: {user_id})",
                color=discord.Color.green()
            )
            embed.set_footer(text=f"Acción realizada por {interaction.user}")

            await interaction.response.send_message(embed=embed)
            await self.send_log(embed)

        except:
            await interaction.response.send_message("❌ No se pudo desbanear. ¿El ID es correcto?", ephemeral=True)

    # ----------------------------------------------------
    # CLEAR
    # ----------------------------------------------------
    @app_commands.command(name="clear", description="Elimina mensajes del chat.")
    @app_commands.describe(cantidad="Número de mensajes a borrar.")
    async def clear(self, interaction: discord.Interaction, cantidad: int):
        
        await interaction.response.defer(ephemeral=True)

        deleted = await interaction.channel.purge(limit=cantidad)

        embed = discord.Embed(
            title="🧹 Mensajes eliminados",
            description=f"Se eliminaron **{len(deleted)}** mensajes.",
            color=discord.Color.blue()
        )

        await interaction.followup.send(embed=embed)

    # ----------------------------------------------------
    # MUTE (con rol Muted)
    # ----------------------------------------------------
    @app_commands.command(name="mute", description="Mutea a un usuario.")
    @app_commands.describe(usuario="Usuario a mutear", razon="Razón del mute")
    async def mute(self, interaction: discord.Interaction, usuario: discord.Member, razon: str = "No especificada"):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ No tenés permisos para mutear.", ephemeral=True)

        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if mute_role is None:
            return await interaction.response.send_message("❌ No existe el rol **Muted**.", ephemeral=True)

        await usuario.add_roles(mute_role, reason=razon)

        embed = discord.Embed(
            title="🔇 Usuario Muteado",
            description=f"**Usuario:** {usuario.mention}\n**Razón:** {razon}",
            color=discord.Color.dark_gray()
        )
        embed.set_footer(text=f"Acción realizada por {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    # ----------------------------------------------------
    # UNMUTE
    # ----------------------------------------------------
    @app_commands.command(name="unmute", description="Desmutea a un usuario.")
    async def unmute(self, interaction: discord.Interaction, usuario: discord.Member):
        if not interaction.user.guild_permissions.moderate_members:
            return await interaction.response.send_message("❌ No tenés permisos para desmutear.", ephemeral=True)

        mute_role = discord.utils.get(interaction.guild.roles, name="Muted")
        if mute_role is None:
            return await interaction.response.send_message("❌ No existe el rol **Muted**.", ephemeral=True)

        await usuario.remove_roles(mute_role)

        embed = discord.Embed(
            title="🔊 Usuario Desmuteado",
            description=f"**Usuario:** {usuario.mention}",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Acción realizada por {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    # ----------------------------------------------------
    # SLOWMODE
    # ----------------------------------------------------
    @app_commands.command(name="slowmode", description="Activa slowmode en el canal.")
    @app_commands.describe(segundos="Segundos de slowmode (0 para desactivar)")
    async def slowmode(self, interaction: discord.Interaction, segundos: int):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ No tenés permisos para usar slowmode.", ephemeral=True)

        await interaction.channel.edit(slowmode_delay=segundos)

        embed = discord.Embed(
            title="⏳ Slowmode Ajustado",
            description=f"Slowmode: **{segundos} segundos**",
            color=discord.Color.purple()
        )
        embed.set_footer(text=f"Acción realizada por {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    # ----------------------------------------------------
    # LOCK
    # ----------------------------------------------------
    @app_commands.command(name="lock", description="Cierra un canal (impide enviar mensajes).")
    async def lock(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ No tenés permisos para cerrar canales.", ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = False
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔐 Canal Cerrado",
            description=f"{interaction.channel.mention} ahora está cerrado.",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"Acción realizada por {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    # ----------------------------------------------------
    # UNLOCK
    # ----------------------------------------------------
    @app_commands.command(name="unlock", description="Abre un canal (permite enviar mensajes).")
    async def unlock(self, interaction: discord.Interaction):
        if not interaction.user.guild_permissions.manage_channels:
            return await interaction.response.send_message("❌ No tenés permisos para abrir canales.", ephemeral=True)

        overwrite = interaction.channel.overwrites_for(interaction.guild.default_role)
        overwrite.send_messages = True
        await interaction.channel.set_permissions(interaction.guild.default_role, overwrite=overwrite)

        embed = discord.Embed(
            title="🔓 Canal Abierto",
            description=f"{interaction.channel.mention} ahora está abierto.",
            color=discord.Color.green()
        )
        embed.set_footer(text=f"Acción realizada por {interaction.user}")

        await interaction.response.send_message(embed=embed)
        await self.send_log(embed)

    async def send_log(self, embed: discord.Embed):
        channel = self.bot.get_channel(LOG_CHANNEL_ID)
        if channel:
            await channel.send(embed=embed)


async def setup(bot):
    await bot.add_cog(AdminCommands(bot))

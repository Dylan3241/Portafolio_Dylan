import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import os
import re

DB_PATH = "database.db"

class Cedulas(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db_init()

    # Crear base de datos
    def db_init(self):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS cedulas (
            user_id INTEGER PRIMARY KEY,
            nombre TEXT,
            apellido TEXT,
            nacimiento TEXT,
            nacionalidad TEXT,
            lugar TEXT,
            dni TEXT,
            tipo_sangre TEXT,
            genero TEXT,
            roblox TEXT,
            foto_url TEXT
        );
        """)
        
        conn.commit()
        conn.close()

    # ===========================
    # COMANDO: CREAR / ACTUALIZAR CÉDULA
    # ===========================
    @app_commands.command(name="crear_cedula", description="Crear o actualizar tu cédula")
    @app_commands.describe(
        nombre="Indica el nombre",
        apellido="Indica el apellido",
        nacimiento="Indica el nacimiento, DD/MM/AAAA",
        lugar="Indica el lugar de nacimiento",
        nacionalidad="Indica tu nacionalidad",
        dni="Indica tu dni, pon 10 numeros aleatorios",
        tipo_sangre="Pon tu tipo de sangre",
        genero="Indica tu género, Masculino o Femenino",
        roblox="Indica el usuario de Roblox",
        foto="Foto para la cédula"
    )
    async def crear_cedula(
        self,
        interaction: discord.Interaction,
        nombre: str,
        apellido: str,
        nacimiento: str,
        nacionalidad: str,
        dni: str,
        tipo_sangre: str,
        genero: str,
        lugar: str,
        roblox: str,
        foto: discord.Attachment
    ):

        # Valida la imagen
        if not foto.content_type.startswith("image/"):
            return await interaction.response.send_message("❌ El archivo debe ser una imagen.", ephemeral=True)
        
        # Valida que sea formato DD/AA/MMMM
        if not re.match(r"^\d{2}/\d{2}/\d{4}$", nacimiento):
            return await interaction.response.send_message("❌ El nacimiento debe tener el formato DD/MM/AAAA.", ephemeral=True)
        
        # Valida que el DNI tenga solamente 10 digitos
        if not (dni.isdigit() and len(dni) == 10):
            return await interaction.response.send_message("❌ El DNI debe tener exactamente 10 números.", ephemeral=True)


        foto_url = foto.url  

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("""
        INSERT INTO cedulas (user_id, nombre, apellido, nacimiento, dni, tipo_sangre, genero, lugar, nacionalidad, roblox, foto_url)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(user_id) DO UPDATE SET
            nombre = excluded.nombre,
            apellido = excluded.apellido,
            nacimiento = excluded.nacimiento,
            nacionalidad = excluded.nacionalidad,
            dni = excluded.dni,
            tipo_sangre = excluded.tipo_sangre,
            genero = excluded.genero,
            lugar = excluded.lugar,
            roblox = excluded.roblox,
            foto_url = excluded.foto_url
        """, (interaction.user.id, nombre, apellido, nacimiento, dni, tipo_sangre, genero, lugar, nacionalidad, roblox, foto_url))
            
        conn.commit()
        conn.close()

        await interaction.response.send_message("✅ Tu cédula fue creada/actualizada correctamente.", ephemeral=True)

    # ===========================
    # COMANDO: VER CÉDULA
    # ===========================
    @app_commands.command(name="ver_cedula", description="Ver tu cédula o la de un usuario")
    async def ver_cedula(
        self,
        interaction: discord.Interaction,
        usuario: discord.User = None
    ):

        usuario = usuario or interaction.user

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT nombre, apellido, nacimiento, dni, tipo_sangre, genero, lugar, nacionalidad, roblox, foto_url FROM cedulas WHERE user_id = ?", (usuario.id,))
        data = cursor.fetchone()

        if not data:
            return await interaction.response.send_message("⚠️ Este usuario no tiene cédula registrada.", ephemeral=True)

        nombre, apellido, nacimiento, dni, tipo_sangre, genero, lugar, nacionalidad, roblox, foto_url = data

        embed = discord.Embed(
            title="🪪 Documento Nacional de Identidad",
            color=discord.Color.green()
        )
        embed.add_field(name="\u200b", value="―"*24, inline=False)

        embed.set_image(url=foto_url)

        embed.add_field(
            name="NOMBRE COMPLETO:",
            value=f"```{nombre} {apellido}```",
            inline=False
        )

        embed.add_field(name="\u200b", value="―"*24, inline=False)

        embed.add_field(
            name="IDENTIFICACIÓN:",
            value=f"```{dni}```",
            inline=False
        )

        embed.add_field(name="\u200b", value="―"*24, inline=False)

        embed.add_field(name="**Información Personal y Datos Vitales:**",value=" ",inline=True)
        
        embed.add_field(name=" ",value=f"> **Nacimiento:** `{nacimiento}`",inline=False)
        embed.add_field(name=" ",value=f"> **Lugar:** `{lugar}`",inline=False)

        embed.add_field(name=" ",value=f"> **Nacionalidad:** `{nacionalidad}`",inline=False)
        embed.add_field(name=" ",value=f"> **Género:** `{genero}`",inline=False)

        embed.add_field(name=" ",value=f"> **Tipo de Sangre:** `{tipo_sangre}`",inline=False)

        embed.add_field(name="\u200b", value="―"*24, inline=False)
        
        embed.add_field(name=" ", value=f"*Discord:* `{usuario.name}` | *Roblox:* `{roblox}`", inline=True)
        
        await interaction.response.send_message(embed=embed)

    # ===========================
    # COMANDO: ELIMINAR CEDULA
    # ===========================
    @app_commands.command(name="eliminar_cedula", description="Elimina tu cedula del sistema")
    async def eliminar_cedula(self, interaction: discord.Interaction):

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("DELETE FROM cedulas WHERE user_id = ?", (interaction.user.id))

        conn.commit
        conn.close

        await interaction.response.send_message("🗑️ Tu cédula fue eliminada del sistema.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Cedulas(bot))

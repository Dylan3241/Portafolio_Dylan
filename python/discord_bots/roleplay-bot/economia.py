import discord
from discord import app_commands
from discord.ext import commands
import sqlite3
import datetime
import math
from typing import Optional, List, Tuple

DB_PATH = "database.db"
ECONOMIA_LOGS_CHANNEL = 1413761905323151371
CANAL_SUELDOS = 1395513742699004034


def now_str() -> str:
    return datetime.datetime.now().strftime("%d/%m/%Y %H:%M")


class TiendaView(discord.ui.View):
    """
    Vista con botones para paginar la lista de items.
    - author_id: id del usuario que invocó /tienda (solo ese usuario puede usar los botones)
    - items: lista de tuplas (id, nombre, precio, descripcion)
    - items_por_pagina: cuantos items mostrar por página
    """

    def __init__(self, author_id: int, items: List[Tuple[int, str, int, str]], items_por_pagina: int = 8):
        super().__init__(timeout=None)
        self.author_id = author_id
        self.items = items
        self.pagina = 0
        self.items_por_pagina = items_por_pagina

    def obtener_pagina(self) -> List[Tuple[int, str, int, str]]:
        inicio = self.pagina * self.items_por_pagina
        fin = inicio + self.items_por_pagina
        return self.items[inicio:fin]

    def total_paginas(self) -> int:
        if len(self.items) == 0:
            return 1
        return max(1, math.ceil(len(self.items) / self.items_por_pagina))

    def crear_embed(self) -> discord.Embed:
        embed = discord.Embed(
            title=f"🛍️ Tienda — Página {self.pagina + 1}/{self.total_paginas()}",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )

        pagina_items = self.obtener_pagina()
        if not pagina_items:
            embed.description = "No hay objetos en esta página."
            return embed

        for iid, nombre, precio, desc in pagina_items:
            embed.add_field(
                name=f"{nombre} — €{precio:,}",
                value={desc},
                inline=False
            )

        embed.set_footer(text=f"Total de objetos: {len(self.items)}")
        return embed

    async def _check_user(self, interaction: discord.Interaction) -> bool:
        """Permitir solo al usuario que abrió la tienda usar los botones (envía mensaje ephemeral si no)."""
        if interaction.user.id != self.author_id:
            await interaction.response.send_message("❌ Solo quien abrió la tienda puede usar estos botones.", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="« Anterior", style=discord.ButtonStyle.blurple)
    async def anterior(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_user(interaction):
            return

        if self.pagina > 0:
            self.pagina -= 1
            await interaction.response.edit_message(embed=self.crear_embed(), view=self)
        else:
            await interaction.response.send_message("Ya estás en la primera página.", ephemeral=True)

    @discord.ui.button(label="Siguiente »", style=discord.ButtonStyle.blurple)
    async def siguiente(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not await self._check_user(interaction):
            return

        if self.pagina < self.total_paginas() - 1:
            self.pagina += 1
            await interaction.response.edit_message(embed=self.crear_embed(), view=self)
        else:
            await interaction.response.send_message("Ya estás en la última página.", ephemeral=True)


class Economia(commands.Cog):
    """Cog: economía (saldo, tienda, inventario, compras y administración)."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = sqlite3.connect(DB_PATH, check_same_thread=False)
        self.cursor = self.db.cursor()
        self.db_init()

        self.roles_dinero = {
            "〡👮〢Policía Nacional": 2300, 
            "〡🚔〢Guardia Civil": 2500, 
            "〡⛑️〢S.A.M.U.R": 1300, 
            "〡💼〢Abogado": 1800, 
            "〡🔨〢Presidente del consejo judicial": 10800,
            "〡🧑‍⚖️〢Juez": 1800, 
            "〡🕵️〢Centro Nacional Inteligencia": 3000, 
            "〡🔎〢Unidad de Asuntos Internos": 2200, 
            "〡🧑‍🚒〢Cuerpo de Bomberos": 1450,
            "〡🚧〢Conservación de carreteras": 1250,
            "〡💎〢Inversionista Diamante": 3500,
            "〡🥇〢Inversionista Oro": 3000, 
            "〡🥈〢Inversionista plata": 2000,
            "〡🥉〢Inversionista Bronce": 1000,
            "〡🎋〢Ultra Booster": 1500,
            "〡♦️〢Server Booster": 1000, 
            "〡🏦〢Casa Real": 50000, 
            "〡👤〢Ciudadano": 500, 
            "〡🪪〢Licencia de Conducir": -75, 
            "〡🪪〢Licencia de Armas": -100
        }

    #==========================================================
    # ENVIAR SUELDOS A UN CANAL EN ESPECIFICO
    #==========================================================

    async def enviar_roles_dinero(self, CANAL_SUELDOS: int):
        canal = self.bot.get_channel(CANAL_SUELDOS)
        if not canal:
            print(f"No se encontró el canal con ID {CANAL_SUELDOS}")
            return

        roles_ordenados = sorted(self.roles_dinero.items(), key=lambda x: x[1], reverse=True)

        embed = discord.Embed(
            title="💼 Sueldos de roles",
            description="Listado de todos los roles que generan dinero en el servidor.",
            color=discord.Color.gold(),
            timestamp=datetime.datetime.now()
        )

        # Armamos toda la tabla
        tabla = "```diff\n"
        tabla += "{:<35} {:>10}\n".format("ROL", "SUELDO")
        tabla += "-"*47 + "\n"

        for rol, dinero in roles_ordenados:
            signo = "+" if dinero >= 0 else "-"
            emoji = "🟢" if dinero >= 0 else "🔴"
            tabla += "{:<35} {} {:>10}\n".format(rol, emoji+signo, abs(dinero))

        tabla += "```"

        # ============================
        # DIVIDIR TABLA SI ES NECESARIO
        # ============================
        MAX = 1024
        partes = []

        while len(tabla) > MAX:
            corte = tabla.rfind("\n", 0, MAX)
            partes.append(tabla[:corte])
            tabla = tabla[corte:]

        partes.append(tabla)

        # Añadimos campos al embed
        for i, parte in enumerate(partes, start=1):
            embed.add_field(
                name=f"Roles y sueldos (parte {i})" if len(partes) > 1 else "Roles y sueldos",
                value=parte,
                inline=False
            )

        await canal.send(embed=embed)


    @commands.Cog.listener()
    async def on_ready(self):
        try:
            await self.enviar_roles_dinero(CANAL_SUELDOS)
        except Exception as e:
            print("Error enviando roles de dinero:", e)


    def db_init(self):
        """Crear tablas necesarias si no existen."""
        # tabla usuarios
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios (
                user_id INTEGER PRIMARY KEY,
                saldo INTEGER DEFAULT 0,
                ultima_recoleccion TEXT DEFAULT NULL
            );
        """)
        # tabla tienda
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS tienda (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT UNIQUE,
                precio INTEGER,
                descripcion TEXT DEFAULT 'Sin descripción'
            );
        """)
        # tabla inventario
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS inventario (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                item TEXT,
                fecha_compra TEXT
            );
        """)

        self.db.commit()

    #==========================================================
    # HELPERS
    #==========================================================
    def ensure_user(self, user_id: int):
        self.cursor.execute("SELECT 1 FROM usuarios WHERE user_id = ?", (user_id,))
        if not self.cursor.fetchone():
            self.cursor.execute("INSERT INTO usuarios (user_id, saldo) VALUES (?, ?)", (user_id, 0))
            self.db.commit()

    def get_saldo(self, user_id: int) -> int:
        self.ensure_user(user_id)
        self.cursor.execute("SELECT saldo FROM usuarios WHERE user_id = ?", (user_id,))
        row = self.cursor.fetchone()
        return row[0] if row else 0

    def set_saldo(self, user_id: int, amount: int):
        self.ensure_user(user_id)
        self.cursor.execute("UPDATE usuarios SET saldo = ? WHERE user_id = ?", (amount, user_id))
        self.db.commit()

    def add_saldo(self, user_id: int, amount: int):
        self.ensure_user(user_id)
        self.cursor.execute("UPDATE usuarios SET saldo = saldo + ? WHERE user_id = ?", (amount, user_id))
        self.db.commit()

    def remove_saldo(self, user_id: int, amount: int):
        self.ensure_user(user_id)
        self.cursor.execute("UPDATE usuarios SET saldo = saldo - ? WHERE user_id = ?", (amount, user_id))
        self.db.commit()

    def format_money(self, amount: int) -> str:
        return f"{amount:,}€"

    def is_staff(self, member: discord.Member) -> bool:
        try:
            return member.guild_permissions.manage_guild or member.guild_permissions.manage_messages
        except Exception:
            return False

    async def enviar_log(self, embed: discord.Embed):
        canal = self.bot.get_channel(ECONOMIA_LOGS_CHANNEL)
        if canal:
            try:
                await canal.send(embed=embed)
            except Exception:
                # no hacer crash si no se puede enviar
                pass

    #==========================================================
    # COMANDO: SALDO
    #==========================================================

    @app_commands.command(name="saldo", description="Ver tu saldo o el saldo de otro usuario (staff puede ver a cualquiera).")
    @app_commands.describe(usuario="Usuario a consultar (opcional)")
    async def saldo(self, interaction: discord.Interaction, usuario: Optional[discord.User] = None):
        target = usuario or interaction.user

        if usuario and usuario.id != interaction.user.id and not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tienes permisos para ver el saldo de otros usuarios.", ephemeral=True)
            return

        saldo = self.get_saldo(target.id)
        embed = discord.Embed(
            title="💰 Balance",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now()
        )
        embed.add_field(name="Usuario", value=f"{target.mention} ({target.id})", inline=False)
        embed.add_field(name="Saldo", value=self.format_money(saldo), inline=False)

        await interaction.response.send_message(embed=embed)
        await self.enviar_log(embed)

    #==========================================================
    # COMANDO: TRANSFERENCIA
    #==========================================================

    @app_commands.command(name="transferencia", description="Transferir dinero a otro usuario.")
    @app_commands.describe(usuario="Usuario receptor", cantidad="Cantidad a transferir")
    async def transferencia(self, interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        sender = interaction.user
        receiver = usuario

        if receiver.id == sender.id:
            await interaction.response.send_message("❌ No podés transferirte a vos mismo.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message("❌ La cantidad debe ser mayor a 0.", ephemeral=True)
            return

        sender_saldo = self.get_saldo(sender.id)
        if sender_saldo < cantidad:
            await interaction.response.send_message("❌ No tenés saldo suficiente.", ephemeral=True)
            return

        self.remove_saldo(sender.id, cantidad)
        self.add_saldo(receiver.id, cantidad)

        embed_sender = discord.Embed(
            title="💸 Transferencia realizada",
            description=f"Transferiste {self.format_money(cantidad)} a {receiver.mention}.",
            color=discord.Color.green(),
            timestamp=datetime.datetime.now()
        )
        embed_sender.add_field(name="Saldo anterior", value=self.format_money(sender_saldo))
        embed_sender.add_field(name="Saldo actual", value=self.format_money(self.get_saldo(sender.id)))

        await interaction.response.send_message(embed=embed_sender)

        try:
            embed_receiver = discord.Embed(
                title="💰 Has recibido dinero",
                description=f"Has recibido {self.format_money(cantidad)} de {sender.mention}.",
                color=discord.Color.green()
            )
            embed_receiver.add_field(name="Saldo actual", value=self.format_money(self.get_saldo(receiver.id)))
            await receiver.send(embed=embed_receiver)
        except discord.Forbidden:
            pass

    #==========================================================
    # COMANDO: TIENDA
    #==========================================================

    @app_commands.command(name="tienda", description="Mostrar los objetos disponibles.")
    async def tienda(self, interaction: discord.Interaction):

        await interaction.response.defer(ephemeral=False)

        self.cursor.execute("SELECT id, nombre, precio, descripcion FROM tienda ORDER BY precio ASC")
        items = self.cursor.fetchall()

        if not items:
            embed = discord.Embed(
                title="🛍️ Tienda",
                description="La tienda está vacía.",
                color=discord.Color.gold(),
                timestamp=datetime.datetime.now()
            )
            await interaction.followup.send(embed=embed, ephemeral=False)
            return

        view = TiendaView(author_id=interaction.user.id, items=items, items_por_pagina=8)

        embed = view.crear_embed()

        await interaction.followup.send(embed=embed, view=view, ephemeral=False)


    #==========================================================
    # COMANDO: COMPRAR OBJETO
    #==========================================================

    @app_commands.command(name="comprar_objeto", description="Comprar un objeto por nombre.")
    async def comprar_objeto(self, interaction: discord.Interaction, nombre: str):
        user = interaction.user
        self.cursor.execute("SELECT id, precio FROM tienda WHERE nombre = ?", (nombre,))
        row = self.cursor.fetchone()

        if not row:
            await interaction.response.send_message("❌ Ese objeto no existe.", ephemeral=True)
            return

        item_id, precio = row
        saldo = self.get_saldo(user.id)

        if saldo < precio:
            await interaction.response.send_message("❌ No tenés saldo suficiente.", ephemeral=True)
            return

        self.remove_saldo(user.id, precio)
        fecha = now_str()
        self.cursor.execute("INSERT INTO inventario (user_id, item, fecha_compra) VALUES (?, ?, ?)",
                            (user.id, nombre, fecha))
        self.db.commit()

        embed = discord.Embed(
            title="✅ Compra realizada",
            description=f"Compraste **{nombre}** por {self.format_money(precio)}.",
            color=discord.Color.green()
        )
        embed.add_field(name="Saldo restante", value=self.format_money(self.get_saldo(user.id)))

        await interaction.response.send_message(embed=embed)

    #==========================================================
    # COMANDO: INVENTARIO
    #==========================================================

    @app_commands.command(name="inventario", description="Ver tu inventario.")
    async def inventario(self, interaction: discord.Interaction):
        user = interaction.user
        self.cursor.execute("SELECT id, item, fecha_compra FROM inventario WHERE user_id = ? ORDER BY id DESC",
                            (user.id,))
        filas = self.cursor.fetchall()

        embed = discord.Embed(
            title=f"🎒 Inventario - {user.name}",
            color=discord.Color.blurple(),
            timestamp=datetime.datetime.now()
        )

        if not filas:
            embed.description = "No tenés objetos."
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

        texto = ""
        for i, (iid, item, fecha) in enumerate(filas, start=1):
            texto += f"**{i}.** {item} (ID: {iid}) — {fecha}\n"

        embed.description = texto
        await interaction.response.send_message(embed=embed)

    #==========================================================
    # COMANDO: USAR ITEM
    #==========================================================

    @app_commands.command(name="usar_item", description="Usar un objeto del inventario (si coincide con un rol, te lo asigna).")
    async def usar_item(self, interaction: discord.Interaction, nombre: str):
        user = interaction.user

        self.cursor.execute(
            "SELECT id FROM inventario WHERE user_id = ? AND item = ? LIMIT 1",
            (user.id, nombre)
        )
        fila = self.cursor.fetchone()

        if not fila:
            await interaction.response.send_message("❌ No tenés ese objeto.", ephemeral=True)
            return

        item_id = fila[0]

        role = discord.utils.find(lambda r: r.name.lower() == nombre.lower(), interaction.guild.roles)
        if not role:
            await interaction.response.send_message("❌ No existe un rol con ese nombre.", ephemeral=True)
            return

        try:
            await user.add_roles(role, reason="Uso de item")
        except discord.Forbidden:
            await interaction.response.send_message("❌ No tengo permisos para asignar roles.", ephemeral=True)
            return

        self.cursor.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
        self.db.commit()

        await interaction.response.send_message(f"✅ Se te asignó el rol **{role.name}** y se consumió el objeto.")
    
    #==========================================================
    # COMANDO: REGALAR UN ITEM
    #==========================================================

    @app_commands.command(name="regalar_item", description="Regala un objeto del inventario a otro usuario.")
    @app_commands.describe(usuario="Usuario receptor", nombre="Nombre del objeto a regalar")
    async def regalar_item(self, interaction: discord.Interaction, usuario: discord.User, nombre: str):
        if usuario.id == interaction.user.id:
            await interaction.response.send_message("❌ No podés regalarte a vos mismo.", ephemeral=True)
            return

        self.cursor.execute(
            "SELECT id FROM inventario WHERE user_id = ? AND item = ? LIMIT 1",
            (interaction.user.id, nombre)
        )
        fila = self.cursor.fetchone()
        if not fila:
            await interaction.response.send_message("❌ No tenés ese objeto.", ephemeral=True)
            return

        item_id = fila[0]

        fecha = now_str()
        self.cursor.execute(
            "INSERT INTO inventario (user_id, item, fecha_compra) VALUES (?, ?, ?)",
            (usuario.id, nombre, fecha)
        )

        self.cursor.execute("DELETE FROM inventario WHERE id = ?", (item_id,))
        self.db.commit()

        await interaction.response.send_message(f"✅ Regalaste **{nombre}** a {usuario.mention}.")
        try:
            await usuario.send(f"🎁 Recibiste **{nombre}** de {interaction.user.mention}.")
        except discord.Forbidden:
            pass

    #==========================================================
    # COMANDO: RECOLECTAR DINERO
    #==========================================================
    @app_commands.command(name="recolectar", description="Recolección diaria de dinero según tus roles.")
    async def recolectar(self, interaction: discord.Interaction):

        user = interaction.user
        ahora = datetime.datetime.now()

        # Roles, dinero y cooldown en segundos
        rol_dinero = {
            "〡👮〢Policía Nacional": (2300, 86400),
            "〡🚔〢Guardia Civil": (2500, 86400),
            "〡⛑️〢S.A.M.U.R": (1300, 86400),
            "〡💼〢Abogado": (1800, 86400),
            "〡🔨〢Presidente del consejo judicial": (10800, 86400),
            "〡🧑‍⚖️〢Juez": (1800, 86400),
            "〡🕵️〢Centro Nacional Inteligencia": (3000, 86400),
            "〡🔎〢Unidad de Asuntos Internos": (2200, 86400),
            "〡🧑‍🚒〢Cuerpo de Bomberos": (1450, 86400),
            "〡🚧〢Conservación de carreteras": (950, 86400),
            "〡💎〢Inversionista Diamante": (3500, 86400),
            "〡🥇〢Inversionista Oro": (3000, 86400),
            "〡🥈〢Inversionista plata": (2000, 86400),
            "〡🥉〢Inversionista Bronce": (1000, 86400),
            "〡🎋〢Ultra Booster": (1500, 86400),
            "〡♦️〢Server Booster": (1000, 86400),
            "〡🏦〢Casa Real": (50000, 86400),
            "〡👤〢Ciudadano": (500, 86400),
            "〡🪪〢Licencia de Conducir": (-75, 86400),
            "〡🪪〢Licencia de Armas": (-100, 86400)
        }


        # Obtenemos roles que aplican
        cantidad_total = 0
        cooldown_max = 0
        roles_validos = []

        for role in user.roles:
            if role.name in rol_dinero:
                dinero, cooldown = rol_dinero[role.name]
                cantidad_total += dinero
                cooldown_max = max(cooldown_max, cooldown)
                roles_validos.append(role.name)

        if not roles_validos:
            await interaction.response.send_message("❌ No tenés roles que generen dinero.", ephemeral=True)
            return

        # Verificar cooldown
        self.cursor.execute("SELECT ultima_recoleccion FROM usuarios WHERE user_id = ?", (user.id,))
        fila = self.cursor.fetchone()
        if fila and fila[0]:
            ultima_fecha = datetime.datetime.fromisoformat(fila[0])
            diferencia = ahora - ultima_fecha
            if diferencia.total_seconds() < cooldown_max:
                restante = cooldown_max - diferencia.total_seconds()
                horas = int(restante // 3600)
                minutos = int((restante % 3600) // 60)
                segundos = int(restante % 60)
                await interaction.response.send_message(
                    f"❌ Ya recolectaste tu dinero. Intenta de nuevo en {horas}h {minutos}m {segundos}s.",
                    ephemeral=True
                )
                return

        # Agregar dinero al saldo
        self.add_saldo(user.id, cantidad_total)
        # Actualizar fecha de última recolección
        self.cursor.execute("UPDATE usuarios SET ultima_recoleccion = ? WHERE user_id = ?", (ahora.isoformat(), user.id))
        self.db.commit()

        embed = discord.Embed(
            title="💰 Recolección de dinero",
            color=discord.Color.green() if cantidad_total >= 0 else discord.Color.red(),
            timestamp=ahora
        )

        # Separar roles positivos y negativos
        detalle_roles = ""
        for role_name in roles_validos:
            dinero = rol_dinero[role_name][0]
            emoji = "🟢" if dinero >= 0 else "🔴"
            signo = "+" if dinero >= 0 else ""
            detalle_roles += f"{emoji} {role_name}: {signo}{self.format_money(dinero)}\n"

        embed.description = "Has recolectado dinero de tus roles:\n" + detalle_roles
        embed.add_field(name="Saldo recolectado", value=self.format_money(cantidad_total))
        embed.add_field(name="Saldo total", value=self.format_money(self.get_saldo(user.id)))

        await interaction.response.send_message(embed=embed)


    #==========================================================
    # COMANDO: AGREGAR DINERO
    #==========================================================

    @app_commands.command(name="agregar_dinero", description="Agregar dinero (solo staff).")
    async def agregar_dinero(self, interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message("❌ Cantidad inválida.", ephemeral=True)
            return

        self.add_saldo(usuario.id, cantidad)

        embed = discord.Embed(
            title="✅ Dinero agregado",
            color=discord.Color.green()
        )
        embed.add_field(name="Usuario", value=usuario.mention)
        embed.add_field(name="Cantidad agregada", value=self.format_money(cantidad))
        embed.add_field(name="Nuevo saldo", value=self.format_money(self.get_saldo(usuario.id)))

        await interaction.response.send_message(embed=embed)

        try:
            await usuario.send(f"💰 Te agregaron {self.format_money(cantidad)}.")
        except Exception:
            pass

    #==========================================================
    # COMANDO: REMOVER DINERO
    #==========================================================

    @app_commands.command(name="remover_dinero", description="Quitar dinero (solo staff).")
    async def remover_dinero(self, interaction: discord.Interaction, usuario: discord.User, cantidad: int):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
            return

        if cantidad <= 0:
            await interaction.response.send_message("❌ Cantidad inválida.", ephemeral=True)
            return

        saldo_actual = self.get_saldo(usuario.id)
        nuevo = max(0, saldo_actual - cantidad)

        self.set_saldo(usuario.id, nuevo)

        embed = discord.Embed(
            title="⚠️ Dinero removido",
            color=discord.Color.orange()
        )
        embed.add_field(name="Usuario", value=usuario.mention)
        embed.add_field(name="Cantidad removida", value=self.format_money(cantidad))
        embed.add_field(name="Nuevo saldo", value=self.format_money(nuevo))

        await interaction.response.send_message(embed=embed)

    #==========================================================
    # COMANDO: GESTIONAR TIENDA
    #==========================================================
    gestionar_tienda = app_commands.Group(
        name="gestionar-tienda",
        description="Administración de la tienda"
    )

    @gestionar_tienda.command(name="agregar", description="Agregar un objeto a la tienda (solo staff).")
    async def gestionar_agregar(self, interaction: discord.Interaction, nombre: str, descripcion: str, precio: int):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
            return

        if precio < 0:
            await interaction.response.send_message("❌ Precio inválido.", ephemeral=True)
            return

        try:
            self.cursor.execute(
                "INSERT INTO tienda (nombre, precio, descripcion) VALUES (?, ?, ?)",
                (nombre, precio, descripcion)
            )
            self.db.commit()
        except sqlite3.IntegrityError:
            await interaction.response.send_message("❌ Ese objeto ya existe.", ephemeral=True)
            return

        await interaction.response.send_message(f"✅ Agregado **{nombre}** a la tienda.")

    #==========================================================
    # COMANDO: ELIMINAR OBJETO DE LA TIENDA
    #==========================================================

    @gestionar_tienda.command(name="eliminar", description="Eliminar objeto de la tienda (solo staff).")
    async def gestionar_eliminar(self, interaction: discord.Interaction, nombre: str):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
            return

        # elimina por nombre
        self.cursor.execute("DELETE FROM tienda WHERE nombre = ?", (nombre,))
        if self.cursor.rowcount == 0:
            self.db.commit()
            await interaction.response.send_message("❌ Ese objeto no existe.", ephemeral=True)
            return

        self.db.commit()
        await interaction.response.send_message(f"🗑️ Eliminado **{nombre}**.")

    #==========================================================
    # COMANDO: EDITAR OBJETO DE LA TIENDA
    #==========================================================

    @gestionar_tienda.command(name="editar", description="Editar objeto de la tienda (solo staff).")
    async def gestionar_editar(
        self,
        interaction: discord.Interaction,
        nombre: str,
        nuevo_nombre: Optional[str] = None,
        nuevo_precio: Optional[int] = None,
        nueva_descripcion: Optional[str] = None
    ):
        if not self.is_staff(interaction.user):
            await interaction.response.send_message("❌ No tenés permisos.", ephemeral=True)
            return

        self.cursor.execute("SELECT id, nombre, precio, descripcion FROM tienda WHERE nombre = ?", (nombre,))
        row = self.cursor.fetchone()

        if not row:
            await interaction.response.send_message("❌ Ese objeto no existe.", ephemeral=True)
            return

        item_id, nombre_actual, precio_actual, descripcion_actual = row

        updates = []
        params = []
        cambios = []

        if nuevo_nombre:
            updates.append("nombre = ?")
            params.append(nuevo_nombre)
            cambios.append(f"**Nombre:** `{nombre_actual}` → `{nuevo_nombre}`")

        if nuevo_precio is not None:
            if nuevo_precio < 0:
                await interaction.response.send_message("❌ Precio inválido.", ephemeral=True)
                return
            updates.append("precio = ?")
            params.append(nuevo_precio)
            cambios.append(f"**Precio:** {self.format_money(precio_actual)} → {self.format_money(nuevo_precio)}")

        if nueva_descripcion:
            updates.append("descripcion = ?")
            params.append(nueva_descripcion)
            cambios.append(f"**Descripción:** `{descripcion_actual}` → `{nueva_descripcion}`")

        if not updates:
            await interaction.response.send_message("❌ No especificaste cambios.", ephemeral=True)
            return

        params.append(item_id)
        sql = f"UPDATE tienda SET {', '.join(updates)} WHERE id = ?"
        self.cursor.execute(sql, tuple(params))
        self.db.commit()

        embed = discord.Embed(title="🛠️ Objeto editado", color=discord.Color.green())
        embed.description = "\n".join(cambios)
        await interaction.response.send_message(embed=embed)

    # -------------------------
    # COMANDO: TOP
    # -------------------------
    @app_commands.command(name="top", description="Mostrar el top 10 de jugadores por saldo.")
    async def top(self, interaction: discord.Interaction):
        self.cursor.execute("SELECT user_id, saldo FROM usuarios ORDER BY saldo DESC LIMIT 10")
        filas = self.cursor.fetchall()
        if not filas:
            await interaction.response.send_message("No hay datos aún.", ephemeral=True)
            return

        embed = discord.Embed(title="🏆 Top 10 por saldo", color=discord.Color.gold(), timestamp=datetime.datetime.now())
        desc = ""
        for i, (uid, saldo) in enumerate(filas, start=1):
            member = self.bot.get_user(uid)

            if member is None:

                try:
                    member = await self.bot.fetch_user(uid)
                except:
                    member = None
            name = member.name if member else str(uid)

            desc += f"**{i}.** {name} — {self.format_money(saldo)}\n"
        embed.description = desc
        await interaction.response.send_message(embed=embed, ephemeral=False)

async def setup(bot: commands.Bot):
    await bot.add_cog(Economia(bot))

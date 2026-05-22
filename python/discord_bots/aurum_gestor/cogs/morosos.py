import discord
from discord.ext import commands, tasks
import sqlite3
import datetime

# --- CONFIGURACIÓN ---
ROLES_BLACKLIST = "🚫 Moroso"
INTERES_MORA = 0.05  

# ID de tu canal 
ID_CANAL_LOGS = 1498698174498476174

class Morosos(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_db(self):
        return sqlite3.connect("aurum.db", timeout=10)

    async def cog_load(self):
        print("[⚙️ CONFIG] Cargando módulo de morosos... Iniciando loop automático.")
        self.check_morosos_loop.start()

    def cog_unload(self):
        self.check_morosos_loop.cancel()

    @tasks.loop(hours=1)
    async def check_morosos_loop(self):
        ahora = datetime.datetime.now()
        print(f"\n[🔄 EJECUCIÓN] Comprobando vencimientos: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
        
        conn = self.get_db()
        cursor = conn.cursor()
        
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute(
                "SELECT id, user_id, total_pagar, fecha_limite FROM prestamos WHERE estado IN ('activo', 'mora')"
            )
            prestamos = cursor.fetchall()

            for p_id, u_id, total, f_limite in prestamos:
                try:
                    fecha_limpia_lectura = str(f_limite).replace("T", " ").strip()
                    fecha_limite_dt = datetime.datetime.fromisoformat(fecha_limpia_lectura)

                    if ahora < fecha_limite_dt:
                        continue 

                    print(f"    🚨 ¡PLAZO VENCIDO! Aplicando penalización al Préstamo ID {p_id}...")

                    recargo = int(total * INTERES_MORA)
                    nuevo_total = total + recargo
                    
                    fecha_objeto = fecha_limite_dt + datetime.timedelta(days=5)
                    nueva_fecha_limite = fecha_objeto.strftime('%Y-%m-%d %H:%M:%S') 
                    fecha_actual_str = ahora.strftime('%Y-%m-%d %H:%M:%S') 

                    # Localizamos al usuario primero para no congelar transacciones de BD
                    usuario = None
                    guild_actual = None
                    
                    for guild in self.bot.guilds:
                        try:
                            usuario = await guild.fetch_member(int(u_id))
                            guild_actual = guild
                            break 
                        except discord.NotFound:
                            continue
                        except Exception as e:
                            print(f"    ❌ Error buscando usuario en Discord: {e}")

                    cursor.execute(
                        "UPDATE prestamos SET total_pagar = ?, fecha_limite = ?, ultima_mora = ?, estado = 'mora' WHERE id = ?",
                        (nuevo_total, nueva_fecha_limite, fecha_actual_str, p_id)
                    )
                    conn.commit()
                    print(f"    ✅ BD Actualizada: €{nuevo_total} | Próximo control guardado: {nueva_fecha_limite}")

                    if guild_actual and usuario:
                        # 1. Aplicar el Rol Blacklist
                        role = discord.utils.get(guild_actual.roles, name=ROLES_BLACKLIST)
                        if role:
                            try:
                                await usuario.add_roles(role)
                                print(f"    ✅ Rol '{ROLES_BLACKLIST}' asignado a {usuario.name}.")
                            except discord.Forbidden:
                                print(f"    ❌ Sin permisos para dar rol. Sube el rol del Bot por encima de '{ROLES_BLACKLIST}'.")

                        # 2. Enviar Log al Canal por ID
                        log_channel = guild_actual.get_channel(ID_CANAL_LOGS) or self.bot.get_channel(ID_CANAL_LOGS)
                        if log_channel:
                            try:
                                embed_log = discord.Embed(
                                    title="🚨 SISTEMA DE MORA AUTOMÁTICA",
                                    color=0xE74C3C,
                                    timestamp=ahora
                                )
                                embed_log.description = "Se ha aplicado un recargo financiero por vencimiento de plazo."
                                embed_log.add_field(name="👤 Usuario afectado", value=usuario.mention, inline=False)
                                embed_log.add_field(name="🆔 Préstamo ID", value=f"#{p_id}", inline=True)
                                embed_log.add_field(name="📈 Penalización (5%)", value=f"+€{recargo}", inline=True)
                                embed_log.add_field(name="💰 Saldo Actualizado", value=f"€{nuevo_total}", inline=True)
                                embed_log.add_field(name="📅 Próximo Control", value=nueva_fecha_limite, inline=False)
                                
                                await log_channel.send(embed=embed_log)
                                print("    ✅ Registro enviado correctamente al canal de morosos.")
                            except Exception as e:
                                print(f"    ❌ Error de escritura al enviar el log al canal: {e}")
                        else:
                            print(f"    ❌ Error crítico: No se encontró ningún canal con el ID {ID_CANAL_LOGS}.")

                        # 3. Enviar Mensaje Directo (DM) al Cliente afectado
                        try:
                            embed_dm = discord.Embed(
                                title="⚠️ AVISO DE MORA BANCARIA", 
                                color=0xE74C3C,
                                timestamp=ahora
                            )
                            embed_dm.description = "Has superado la fecha límite de pago de tu crédito activo en Aurum."
                            embed_dm.add_field(name="📈 Recargo aplicado", value=f"€{recargo} (5%)", inline=True)
                            embed_dm.add_field(name="💰 Total a pagar ahora", value=f"€{nuevo_total}", inline=True)
                            embed_dm.set_footer(text="Se aplicará un 5% extra cada 5 días si no liquidas la deuda.")
                            await usuario.send(embed=embed_dm)
                            print("    ✅ Mensaje Directo (DM) enviado al cliente.")
                        except discord.Forbidden:
                            print("    ⚠️ El usuario tiene los DMs cerrados. No se le pudo notificar en privado.")
                    else:
                        print(f"    ⚠️ El usuario {u_id} no se localizó en Discord. Datos salvados en BD.")

                except Exception as e:
                    print(f"  ❌ Error procesando el préstamo ID {p_id}: {e}")
                    continue
                    
        except Exception as e:
            print(f"❌ CRÍTICO - Error en la ejecución del ciclo general: {e}")
        finally:
            conn.close()

    @check_morosos_loop.before_loop
    async def before_check_morosos(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(Morosos(bot))
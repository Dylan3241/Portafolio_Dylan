import aiosqlite

DATABASE_NAME = "canarias.db"

async def create_tables():
    async with aiosqlite.connect(DATABASE_NAME) as db:
        await db.execute(""" CREATE TABLE IF NOT EXISTS cedulas ( 
                        user_id INTEGER PRIMARY KEY,
                        nombre TEXT,
                        identificacion TEXT,
                        nacimiento TEXT,
                        lugar TEXT,
                        nacionalidad TEXT,
                        genero TEXT,
                        sangre TEXT,
                        roblox TEXT
                        );
                """)

        
        await db.execute(""" CREATE TABLE IF NOT EXISTS economia (
                         user_id INTEGER PRIMARY KEY,
                         saldo INTEGER DEFAULT 0
                        );
                    """)
        
        await db.execute(""" CREATE TABLE IF NOT EXISTS inventario (
                         user_id INTEGER,
                         objeto TEXT,
                         PRIMARY KEY(user_id, objeto)
                        );
                    """)
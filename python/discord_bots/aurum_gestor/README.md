# 🏦 Aurum Bank - Sistema de Gestión Financiera

Aurum Bank es un sistema integral de gestión financiera desarrollado en Python y diseñado originalmente para entornos de Discord. A diferencia de un bot convencional, este proyecto está enfocado en la lógica de negocio, el control de bases de datos relacionales y la automatización de procesos bancarios.

## 🚀 Funcionalidades Principales

* **Gestión de Préstamos (`prestamos.py`):** Sistema completo de solicitud, aprobación y amortización de créditos con cálculo de intereses.
* **Control de Morosidad (`morosos.py`):** Algoritmo de detección automática de deudas vencidas y aplicación de multas, optimizado para mantener la salud financiera del sistema.
* **Módulo de Clientes (`cliente.py`):** Registro y administración de perfiles financieros únicos, saldos y transacciones en tiempo real.
* **Soporte Técnico (`tickets.py`):** Sistema de tickets para la gestión de incidencias y atención personalizada al cliente.
* **Panel de Control (`dashboard.py`):** Visualización de estadísticas globales para la toma de decisiones administrativas.

## 🛠️ Stack Tecnológico

* **Lenguaje:** Python 3.x
* **Base de Datos:** SQLite (diseño relacional robusto)
* **Librerías principales:**
* `discord.py` para la interfaz de usuario.
* `python-dotenv` para la seguridad de credenciales.
* `sqlite3` para la persistencia de datos.



## 🔒 Seguridad y Arquitectura

Este proyecto sigue las mejores prácticas de desarrollo:

1. **Seguridad de Credenciales:** Uso de variables de entorno para proteger tokens sensibles.
2. **Mantenibilidad:** Arquitectura basada en **Cogs** (módulos independientes) para facilitar la escalabilidad del código.
3. **Integridad de Datos:** Uso de esquemas SQL definidos para asegurar que cada transacción financiera se registre correctamente.
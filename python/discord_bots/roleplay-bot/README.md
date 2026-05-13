# 🤖 Discord Bot: Sistema de Gestión Integrado

Este repositorio contiene un sistema modular desarrollado en **Python** para la automatización de funciones avanzadas en Discord, enfocado en la gestión de bases de datos y lógica de procesos.

## 🛠️ Arquitectura Técnica

El proyecto está organizado en módulos independientes para garantizar un código limpio y escalable:

* **`database.py`**: Gestión de la persistencia de datos mediante **SQLite**. Implementa la conexión y las consultas necesarias para mantener la integridad de la información.
* **`economia.py`**: Motor de transacciones financieras virtuales. Incluye lógica para el manejo de saldos y operaciones monetarias entre usuarios.
* **`cedulas.py`**: Sistema de identificación y registro de usuarios, permitiendo un control administrativo detallado.
* **`multas_arrestos.py`**: Módulo especializado en la gestión de infracciones y estados de usuario, integrando validaciones lógicas para la aplicación de sanciones.
* **`__init__.py`**: Archivo esencial para el manejo del paquete de Python, permitiendo la importación eficiente de los módulos.

## 🚀 Habilidades Demostradas

A través de este desarrollo, se aplican conceptos fundamentales de ingeniería de software aprendidos en la **UTU**:

1. **Programación Orientada a Objetos:** Organización del código en componentes reutilizables.
2. **Manejo de SQL:** Diseño y manipulación de bases de datos relacionales con **SQLite**.
3. **Lógica de Negocio:** Implementación de reglas complejas para sistemas de economía y administración.
4. **Seguridad:** Uso de archivos `.env` (gestionados localmente) para la protección de credenciales sensibles.

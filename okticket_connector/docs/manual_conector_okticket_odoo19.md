# Conector Okticket para Odoo — Manual de usuario (Odoo 19)

> Integración entre la app de digitalización de tickets **Okticket** y la gestión de gastos de **Odoo**:
> los empleados fotografían sus tickets en el móvil y los gastos aparecen en Odoo con su imagen, su
> producto y su centro de coste, listos para aprobar y contabilizar.

| | |
|---|---|
| **Versión Odoo** | 19.0 |
| **Módulos** | connector-okticket 19.0 (rama `19.0-mig-okticket-connector`) |
| **Entorno de pruebas** | http://localhost:7000 · BD `devel` · `admin / admin` |
| **Fecha** | 30 de julio de 2026 |
| **Preparado por** | Alia Technologies |

> ⚠️ **Qué cambia respecto a Odoo 18** — Odoo 19 **eliminó las hojas de gasto** (los «informes de gastos»,
> modelo `hr.expense.sheet`): el circuito de presentación, aprobación y contabilización se hace ahora
> **directamente sobre cada gasto**. En consecuencia, esta versión del conector **no incluye** los módulos
> `okticket_connector_hr_expense_sheet`, `okticket_connector_hr_expense_sheet_grouping` ni
> `okticket_hr_expense_reporting`. Desaparecen la agrupación automática en hojas, la sincronización y los
> dos informes PDF con imágenes. Por decisión funcional, el conector **no comunica ningún estado a
> Okticket** (ni informes ni el indicador «contabilizado» del gasto): si Odoo 19 ya no tiene hojas,
> gestionar estados desde fuera puede provocar desajustes contables. La integración es de **solo lectura**
> hacia Odoo en cuanto a gastos, más la publicación de centros de coste. Detalle en la sección 8.

---

## 1. Qué hace el conector

Tres flujos de datos entre Okticket y Odoo, más la publicación de centros de coste.

- **Okticket** — App móvil y plataforma web donde los empleados capturan tickets, kilometraje y facturas.
  El equipo de Okticket revisa los gastos.
- ⬇ usuarios · productos · gastos ⬆ centros de coste
- **Odoo** — Recibe los gastos con imagen y datos fiscales, listos para el circuito estándar de aprobación
  y contabilización de Odoo 19, y publica en Okticket los centros de coste de sus cuentas analíticas.

### Los módulos instalados

| Módulo | Función |
|---|---|
| `okticket_connector` | Núcleo: conexión con la API, importación de gastos con su imagen, logs y permisos. |
| `okticket_connector_user_synchronization` | Importa los usuarios de Okticket y los empareja con empleados de Odoo por email. |
| `okticket_connector_product_synchronization` | Importa los tipos de gasto de Okticket como productos, con variantes refacturable y facturable. |
| `okticket_connector_cost_center` | Sincroniza cuentas analíticas de Odoo con centros de coste de Okticket. |
| `okticket_hr_timesheet_cost_center` | Evita que los proyectos internos autogenerados al crear una compañía generen centros de coste en Okticket. Sin pantallas propias. |

---

## 2. Acceso y permisos

El conector añade la categoría de permisos **Okticket Connector Management** con dos niveles:

| Grupo | Qué permite |
|---|---|
| User | Ver el menú Okticket, consultar backends (solo lectura), ver logs y vínculos (bindings). |
| Manager | Todo lo anterior y además crear y modificar la configuración del backend. |

1. Asigna el grupo al usuario que vaya a administrar el conector:
   `Ajustes › Usuarios y compañías › Usuarios › (usuario)`. En la pestaña de permisos, busca **Okticket
   Connector Management** y selecciona *Manager*.
2. Comprueba que aparece el menú del conector: `Conectores › Okticket`.
   - ✓ Verás dos entradas: **Backends** y **Logs**.

> **Nota** — En el entorno de pruebas el usuario `admin` ya tiene asignados ambos grupos (y el de
> *Connector Manager*, necesario para ver las credenciales). La instalación también crea un usuario técnico
> `okticket_connector_user` que usan los procesos automáticos; no lo desactives.

---

## 3. Configurar la conexión (backend)

El backend es la ficha que guarda las credenciales y opciones de conexión con la API de Okticket.

1. Abre la lista de backends: `Conectores › Okticket › Backends`.
   - ✓ En el entorno de pruebas ya existen dos backends configurados y verificados: **Okticket Producción**
     (My Company) y **Empresa III** (ALIA TECHNOLOGIES).

   > **Multi-empresa** — Cada compañía de Odoo necesita **su propio backend**, aunque la cuenta de Okticket
   > sea la misma (mismas credenciales): el conector añade en cada llamada la cabecera de compañía con el
   > **Company_id** de la compañía del backend (sección 4), y así cada backend solo ve los datos de su
   > empresa en Okticket. Empleados, productos y gastos se sincronizan por compañía.

2. Ábrelo (o crea uno nuevo con *Nuevo*) y revisa los parámetros. Estos son los valores del entorno de
   producción de Okticket:

   | Campo en pantalla | Valor |
   |---|---|
   | HTTP connection url | `api.okticket.es` |
   | Base url | `https://api.okticket.es/v2/public` |
   | Image Base url | `https://api.okticket.es/v2/public` |
   | Oauth path | `/oauth/token` |
   | Operations path | `/api` |
   | Grant type | `password` |
   | Scope | `*` |
   | HTTPS protocol | Activado |
   | User | `«usuario facilitado por Okticket»` |
   | Pass | `«contraseña facilitada por Okticket»` (se muestra enmascarada) |
   | Oauth client id | `«client id facilitado por Okticket»` |
   | Oauth secret | `«secreto facilitado por Okticket»` |

   > **Nota** — Los parámetros técnicos vienen **rellenos por defecto** al crear un backend nuevo: en la
   > práctica solo hay que introducir las cuatro credenciales (**User**, **Pass**, **Oauth client id** y
   > **Oauth secret**).

   > ⚠️ **Confidencial** — Estas credenciales dan acceso a la cuenta de Okticket de la empresa. No compartas
   > este documento fuera del equipo autorizado.

3. Pulsa el botón **Prueba de autenticación** (barra superior del formulario).
   - ✓ Aparece una notificación verde **«Prueba de conexión correcta — Todo parece configurado
     correctamente»**. Si ves un error, revisa usuario, contraseña, client id y secret.

4. Revisa el bloque **Configuración de importación de gastos**:
   - **Import Expenses since** *(fecha y hora)* — Solo se importan gastos modificados en Okticket después de
     esta fecha. Se actualiza sola tras cada importación.
   - **Importar solo gastos revisados** *(activado por defecto)* — Solo entran los gastos marcados como
     revisados en Okticket. Ten en cuenta que la revisión en Okticket se hace sobre **hojas de gastos
     enviadas**: un gasto suelto, sin hoja, no se puede revisar y nunca pasará este filtro. Desactívalo solo
     para importar todo sin filtro (útil en pruebas).
   - **Ignorar «Importar gastos desde fecha»** *(desactivado por defecto)* — Fuerza una reimportación
     completa. **Atención:** antes de reimportar, elimina los gastos en borrador que vinieron de Okticket.

   > **Importante** — No actives «Ignorar Importar gastos desde fecha» en el día a día. Úsalo solo para
   > resincronizaciones completas y controladas.

5. En la parte inferior tienes **⇒ See Hr Expense Bindings**, **⇒ See Backend Logs** y las pestañas de
   vínculos (empleados, productos, analíticas, gastos). Un *binding* es la pareja «registro de Odoo ↔
   registro de Okticket».

---

## 4. Configurar la compañía

La compañía de Odoo debe apuntar a su id de compañía en Okticket.

1. Abre la ficha de la compañía: `Ajustes › Usuarios y compañías › Compañías › (tu compañía)`.
2. Ve a la pestaña **OkTicket Conf.** y rellena **Company_id** con el identificador que facilita Okticket.
   - ✓ En el entorno de pruebas ya está configurado: **31965** en My Company y **62544** en ALIA
     TECHNOLOGIES.
3. En la misma pestaña puedes activar **Autocrear centro de coste del proyecto**: al crear un proyecto en
   Odoo se crea automáticamente su centro de coste en Okticket (sección 9).

> **Nota** — En Odoo 18 esta pestaña incluía además el método y el intervalo de agrupación en hojas de
> gasto. En Odoo 19 esos campos ya no existen porque no hay hojas de gasto.

---

## 5. Sincronizar empleados

Cada gasto de Okticket pertenece a un usuario; para importarlo, ese usuario debe estar emparejado con un
empleado de Odoo.

### Cómo empareja

La sincronización descarga los usuarios de Okticket y busca en Odoo un empleado cuyo **email de trabajo**
coincida con el email del usuario en Okticket (también entre empleados archivados, para no crear
duplicados). Si no lo encuentra, **crea el empleado**. Además, al **crear un empleado nuevo en Odoo** con
email de trabajo, el conector intenta vincularlo automáticamente con su usuario de Okticket.

### Ejecutar la sincronización a mano

1. Activa el modo desarrollador (`Ajustes › General › Herramientas de desarrollador`) y abre
   `Ajustes › Técnico › Automatización › Acciones planificadas`.
2. Busca **User Synchronization From Okticket**, ábrela y pulsa **Ejecutar manualmente**.
3. Verifica en el empleado: `Empleados › (empleado) › pestaña OkTicket Conf.` — el campo **Id de usuario de
   Okticket** está relleno.
4. También puedes ver todos los vínculos desde el backend: pestaña **Hr Employee Bindings**.

> **Consejo** — Si un gasto no se importa por «empleado no encontrado», comprueba que el email del usuario
> en Okticket coincida exactamente con el *email de trabajo* del empleado en Odoo, y relanza esta
> sincronización antes que la de gastos.

---

## 6. Sincronizar productos (tipos de gasto)

Los tipos de gasto de Okticket (restauración, alojamiento, gasolina…) se convierten en productos de Odoo.

### Qué crea exactamente

Por cada tipo de gasto, el conector busca un producto de Odoo con el mismo nombre (o lo crea como servicio
marcable como gasto) y genera dos variantes vinculadas:

| Producto | Sufijo | Para qué sirve |
|---|---|---|
| Base | — | El gasto normal del empleado. |
| Refacturable | `-Rebillable` | Se usa cuando el gasto viene marcado como refacturable al cliente en Okticket. |
| Facturable | `-Invoiceable` | Versión para gastos de tipo factura. |

### Ejecutar y comprobar

1. En `Ajustes › Técnico › Acciones planificadas` ejecuta manualmente **Product Synchronization From
   Okticket**.
2. Abre cualquiera en `Ventas › Productos` y mira la pestaña **OkTicket Conf.** — verás **Category_id**,
   **Type_id** y los enlaces a sus versiones **Rebillable** e **Invoiceable**.

> **Nota** — La instalación también precarga **Kilometres** y **Kilometres-Rebillable** para el kilometraje.

---

## 7. Importar gastos

El flujo principal: los tickets capturados en Okticket se convierten en gastos de Odoo con su imagen.

### Reglas de importación

- Se importan los gastos **modificados después** de «Import Expenses since» y, por defecto, **solo los
  revisados**.
- El gasto necesita resolver **empleado**, **producto** y **compañía**. Si falta alguno, se omite y queda en
  los logs.
- Si viene **refacturable**, se usa la variante «-Rebillable»; si es de tipo **factura**, la «-Invoiceable».
- Si el **NIF capturado** coincide exactamente con un único contacto de Odoo, se rellena el campo
  **Proveedor** del gasto.
- Si trae **centro de coste**, se asigna la cuenta analítica vinculada (100 %) y, si esa analítica tiene
  *cuenta contable por defecto para gastos*, también la cuenta contable.
- La **imagen del ticket** se descarga y se adjunta al chatter del gasto.
- Los gastos **borrados en Okticket** se marcan con una cinta roja «Deleted in Okticket»; si estaban en
  borrador, se eliminan.

### Ejecutar y comprobar

1. Asegúrate de haber sincronizado antes empleados y productos (en ese orden).
2. En `Ajustes › Técnico › Acciones planificadas` ejecuta manualmente **Import Expenses From Okticket**.
3. Abre `Gastos › Mis gastos / Todos`. Cada gasto trae su imagen, su **OkTicket ID** y su estado.
4. Dentro del gasto, fíjate en:
   - **Imagen del ticket** — Se adjunta **en el chatter** (mensaje «Imagen del ticket importada de
     OkTicket») y queda como adjunto principal, visible en el panel de previsualización.
   - **Cinta «Deleted in Okticket»** — En rojo si el gasto se borró en Okticket después de importarlo.
   - **Pestaña «Servidor Okticket»** — OkTicket ID, ID de informe, estado en Okticket
     (*Confirmado*/*Pendiente*), Es factura, modo de pago, NIF y nombre del contacto, la **distribución
     analítica** y el **nombre de la hoja de gastos de Okticket** de origen (permite filtrar y agrupar por
     hoja de origen, aunque las hojas ya no se gestionen en Odoo). La sección **«Respuesta JSON»** solo
     aparece con el **modo desarrollador** activo.

---

## 8. El flujo de gastos en Odoo 19 (sin hojas)

En Odoo 19 no existen las hojas de gasto: cada gasto sigue su propio circuito con los botones estándar de la
aplicación Gastos (presentar → aprobar → registrar asiento → pagar/reembolsar, o rechazar / restablecer a
borrador).

> ⚠️ **Odoo no comunica estados a Okticket** — Por decisión funcional, el conector **no envía ningún cambio
> de estado a Okticket**: ni el estado de las hojas/informes (que en Odoo 19 ya no existen y se gestionan
> íntegramente en Okticket), ni el indicador «contabilizado» del gasto. Todo el circuito de aprobación y
> contabilización vive solo en Odoo, y la revisión y ciclo de vida del informe, solo en Okticket. Esto
> evita desajustes contables entre ambos sistemas. El empleado no verá en la app el avance de sus gastos en
> Odoo.

---

## 9. Centros de coste

Las cuentas analíticas de Odoo se corresponden con los centros de coste de Okticket, para que cada ticket
llegue imputado a su proyecto.

### Creación automática desde proyectos

Con **Autocrear centro de coste del proyecto** activo en la compañía (sección 4): al **crear un proyecto** se
crea su centro de coste en Okticket; al **renombrarlo**, se renombra; al **archivarlo/desarchivarlo**, se
activa/desactiva; y al **eliminarlo** (si su analítica no tiene apuntes), se elimina también en Okticket. El
nombre es «Analítica – Cliente» y, si el proyecto viene de un pedido de venta, lleva su código.

> **Nota** — Los proyectos internos que Odoo genera solos al crear una compañía nueva **no** crean centro de
> coste (módulo `okticket_hr_timesheet_cost_center`).

### Creación manual desde cuentas analíticas

1. Abre `Contabilidad › Configuración › Cuentas analíticas`.
2. Selecciona las analíticas a publicar y ejecuta **Acción** → **Creación de centro de coste desde cuenta
   analítica**.
3. Confirma en el asistente. Se crea el centro de coste en Okticket y la analítica queda vinculada (campo
   **Cost_center_id**).

Casos especiales del asistente: si ya existe en Okticket un centro con el mismo nombre, pide confirmación con
**Confirm Duplicate**; si la analítica ya tiene centro de coste, avisa y no duplica. Para desvincular sin
borrar nada en Okticket, usa **Unlink Cost Center**. Además, en la pestaña OkTicket Conf. de cada analítica
puedes definir la **cuenta contable por defecto para gastos**.

---

## 10. Automatización (acciones planificadas)

Las tres sincronizaciones pueden ejecutarse solas de forma periódica. Vienen desactivadas de fábrica.

| Acción planificada | Qué hace | Intervalo por defecto | Estado inicial |
|---|---|---|---|
| User Synchronization From Okticket | Importa/empareja empleados | Cada 2 horas | Desactivada |
| Product Synchronization From Okticket | Importa tipos de gasto como productos | Cada 2 horas | Desactivada |
| Import Expenses From Okticket | Importa gastos (con imagen) | Cada 2 horas | Desactivada |

1. Con el modo desarrollador activo, abre `Ajustes › Técnico › Automatización › Acciones planificadas`.
2. Busca «Okticket», ábrelas y actívalas con el interruptor. Puedes ajustar el intervalo.
3. Para forzar una ejecución inmediata usa **Ejecutar manualmente**.
   - ✓ Orden recomendado la primera vez: **usuarios → productos → gastos**.

---

## 11. Logs y diagnóstico

Toda llamada a la API y todo incidente de importación queda registrado.

1. Abre `Conectores › Okticket › Logs`.
2. Cada línea indica tipo (Info / Success · Warning · Error), operación, backend, fecha y detalle.

### Incidencias típicas

| Síntoma | Causa probable | Solución |
|---|---|---|
| Un gasto no aparece tras importar | No está revisado en Okticket (¿hoja enviada y revisada?), o es anterior a «Import Expenses since» | Revisarlo en Okticket, o ajustar la fecha del backend y reimportar |
| Warning «empleado no encontrado» | El email del usuario de Okticket no coincide con ningún email de trabajo | Corregir el email del empleado y relanzar la sincronización de usuarios |
| Warning «producto no encontrado» | Tipos de gasto sin sincronizar | Ejecutar la sincronización de productos y reimportar gastos |
| Nada cambia en Okticket al aprobar/contabilizar en Odoo | Comportamiento esperado: por diseño, Odoo no comunica ningún estado a Okticket (sección 8) | Gestionar informes y revisión desde la propia web/app de Okticket |
| Error de autenticación | Credenciales o client id/secret incorrectos | Revisar la sección 3 y usar «Test Authentication» |

---

## 12. Checklist de pruebas

**Configuración**
- [ ] El menú **Conectores › Okticket** es visible con el usuario de pruebas
- [ ] El backend «Okticket Producción» tiene todos los parámetros de la sección 3
- [ ] **Test Authentication** muestra la notificación verde de conexión correcta
- [ ] Cada compañía tiene su **Company_id** (31965 My Company, 62544 ALIA TECHNOLOGIES) y su propio backend
- [ ] Con la segunda compañía activa, los gastos importados llevan el **empleado de su misma compañía** (sin errores de multicompañía en Logs)

**Sincronizaciones**
- [ ] Ejecutada **User Synchronization**: los empleados aparecen con su Id de usuario de Okticket
- [ ] Ejecutada **Product Synchronization**: existen los productos y sus variantes -Rebillable / -Invoiceable
- [ ] Ejecutada **Import Expenses**: los gastos aparecen con su imagen en el chatter y datos técnicos
- [ ] Los bindings se ven desde las pestañas del backend

**Flujo de gastos (Odoo 19)**
- [ ] Un gasto importado se puede **presentar** y **aprobar** con el circuito estándar de Gastos
- [ ] Al **registrar el asiento**, los gastos aprobados del empleado se agrupan en un asiento contable
- [ ] Al aprobar/contabilizar/rechazar/restablecer, **no se envía nada a Okticket** (sin llamadas de escritura en Logs)
- [ ] La imagen del ticket aparece **en el chatter** y en el panel de previsualización
- [ ] La pestaña **«Servidor Okticket»** es visible; su sección **«Respuesta JSON»** solo con modo desarrollador

**Centros de coste**
- [ ] La acción «Creación de centro de coste desde cuenta analítica» crea el CC y rellena Cost_center_id
- [ ] Con «Autocrear centro de coste del proyecto» activo, crear un proyecto crea su CC en Okticket
- [ ] Un gasto de Okticket con centro de coste llega con su cuenta analítica asignada

**Automatización y logs**
- [ ] Las tres acciones planificadas quedan **activadas** con el intervalo deseado
- [ ] La pantalla de **Logs** registra las operaciones de las pruebas anteriores sin errores

---

*Manual del conector Okticket ↔ Odoo 19 · Preparado por Alia Technologies · Entorno de referencia:
`odoo-19-dev`, base de datos `devel`, rama `19.0-mig-okticket-connector`.*

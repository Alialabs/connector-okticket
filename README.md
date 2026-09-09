<p align="center">
  <img src="okticket_connector/docs/img/alia-logo.png" height="52" alt="Alia Technologies"/>
  &nbsp;&nbsp;&nbsp;
  <img src="okticket_connector/docs/img/okticket-logo.png" height="46" alt="OkTicket"/>
</p>

<h1 align="center">Conector OkTicket para Odoo</h1>

<p align="center">
  <a href="https://www.odoo.com"><img src="https://img.shields.io/badge/Odoo-18.0-714B67" alt="Odoo 18.0"/></a>
  <a href="https://www.gnu.org/licenses/agpl-3.0"><img src="https://img.shields.io/badge/licencia-AGPL--3-FF9900" alt="AGPL-3"/></a>
  <a href="https://www.alialabs.com"><img src="https://img.shields.io/badge/mantenido%20por-Alia%20Technologies-777777" alt="Alia Technologies"/></a>
</p>

---

## Qué es esto

Integración entre **[OkTicket](https://www.okticket.es/)** y **Odoo**. OkTicket es una aplicación
móvil de gestión de gastos: el empleado fotografía el ticket y se acabó el papel. Este conector
lleva esos gastos a Odoo automáticamente, sin introducirlos a mano.

La sincronización va principalmente de **OkTicket a Odoo**:

- **Gastos** — importa tickets, facturas y kilometrajes con su importe, fecha, impuestos,
  empleado y compañía, adjuntando la fotografía del recibo y, cuando existe, el PDF de la factura.
- **Hojas de gasto** — agrupa los gastos importados en hojas de gasto según el método configurado
  en la compañía y mantiene sincronizados los estados de la hoja entre Odoo y OkTicket.
- **Usuarios** — empareja los usuarios de OkTicket con empleados de Odoo por correo electrónico.
- **Categorías** — crea en Odoo un producto de gasto por cada categoría de OkTicket, incluidas
  las variantes facturables.

Y en sentido inverso, de **Odoo a OkTicket**:

- **Centros de coste** — publica cuentas analíticas de Odoo como centros de coste, desde una acción
  en la lista de cuentas analíticas o automáticamente al crear un proyecto, para poder imputar un
  ticket desde el móvil.

Está construido sobre el framework [`connector`](https://github.com/OCA/connector) de la OCA:
cada entidad tiene un modelo *binding* que mantiene la correspondencia entre el registro de Odoo
y su identificador remoto.

## Manuales

| Documento | Para quién | Contenido |
|---|---|---|
| **[Manual técnico](okticket_connector/docs/manual-tecnico.md)** · [descargar PDF](https://gitlab.alialabs.com/odoo/connector-okticket/-/raw/18.0-fix-okticket_connector/okticket_connector/docs/manual-tecnico.pdf?inline=false) | Implantadores y administradores | Clonado del repositorio, dependencias, instalación de los módulos, grupos y permisos, configuración de la compañía y del backend, acciones planificadas, hojas de gasto y sincronización de estados, centros de coste, multi-compañía y resolución de problemas. |
| **[Manual de usuario](okticket_connector/docs/manual-usuario.md)** · [descargar PDF](https://gitlab.alialabs.com/odoo/connector-okticket/-/raw/18.0-fix-okticket_connector/okticket_connector/docs/manual-usuario.pdf?inline=false) | Usuarios finales | Cómo llegan los gastos, dónde consultarlos, qué añade el conector a la ficha del gasto, adjuntos, hojas de gasto, categorías, empleados, cuentas analíticas y centros de coste, y dudas frecuentes. |

Los enlaces del título se leen aquí mismo. El **PDF** es la versión maquetada, pensada para imprimir
o enviar al cliente. También existe el `.html` de cada manual
([técnico](okticket_connector/docs/manual-tecnico.html) ·
[usuario](okticket_connector/docs/manual-usuario.html)), que es la fuente con la que se genera el
PDF; los visores lo descargan en vez de renderizarlo.

## Módulos

| Módulo | Descripción |
|---|---|
| `okticket_connector` | Base del conector: backend de configuración, cliente HTTP con OAuth, registro de eventos e importación de gastos. **Obligatorio.** |
| `okticket_connector_user_synchronization` | Importa los usuarios de OkTicket y los vincula con empleados de Odoo. |
| `okticket_connector_product_synchronization` | Importa el árbol de categorías de OkTicket como productos de gasto. |
| `okticket_connector_cost_center` | Publica cuentas analíticas de Odoo como centros de coste en OkTicket. |
| `okticket_connector_hr_expense_sheet` | Agrupa los gastos importados en hojas de gasto y sincroniza sus estados con OkTicket. |
| `okticket_connector_hr_expense_sheet_grouping` | Métodos de agrupación de los gastos en hojas: por cuenta analítica, estándar, individual o sin agrupar. |
| `okticket_hr_expense_reporting` | Informes PDF de gastos y hojas de gasto con las imágenes de los recibos. |
| `okticket_hr_timesheet_cost_center` | Evita una sincronización espuria al crear una compañía nueva con `hr_timesheet`. Opcional. |

## Hojas de gasto

A diferencia de Odoo 19 —que eliminó `hr.expense.sheet`—, esta versión **conserva las hojas de
gasto**. Tres módulos añaden ese flujo por encima de la importación:

- **Agrupación** — los gastos importados se reúnen en hojas de gasto según el método elegido en la
  compañía (por cuenta analítica, estándar, hoja individual o sin agrupar) y el intervalo temporal
  configurado.
- **Sincronización de estados** — al enviar o aprobar una hoja en Odoo, el conector marca los
  gastos como contabilizados en OkTicket y actualiza el estado del informe; los cambios viajan en
  ambos sentidos.
- **Informes** — genera informes PDF de gastos y hojas incorporando las imágenes de los recibos.

## Instalación rápida

```bash
cd /opt/odoo/addons

# el conector
git clone --branch 18.0 https://github.com/Alialabs/connector-okticket.git

# dependencias OCA
git clone --branch 18.0 https://github.com/OCA/connector.git
git clone --branch 18.0 https://github.com/OCA/queue.git

# dependencia Python
pip install -r connector-okticket/requirements.txt
```

Añade las rutas a `addons_path`, reinicia Odoo e instala los módulos:

```bash
odoo -d <base_de_datos> --stop-after-init \
  -i okticket_connector,okticket_connector_user_synchronization,\
okticket_connector_product_synchronization,okticket_connector_cost_center,\
okticket_connector_hr_expense_sheet,okticket_connector_hr_expense_sheet_grouping,\
okticket_hr_expense_reporting
```

El módulo `okticket_hr_timesheet_cost_center` es opcional y solo hace falta si se crean compañías
nuevas con `hr_timesheet`.

Después hay que configurar el identificador de compañía, el backend con las credenciales que
facilita OkTicket, y activar las tres acciones planificadas —que se instalan **desactivadas** a
propósito. El [manual técnico](okticket_connector/docs/manual-tecnico.md) lo
detalla paso a paso.

> **Las credenciales de la API son secretos de producción.** No las escribas en documentación,
> capturas ni ficheros versionados.

## Ramas

Una rama por versión de Odoo: `19.0`, `18.0`, `17.0`, `16.0`, `15.0`, `14.0`, `12.0`, `10.0`.
Usa siempre la que corresponda a tu instancia.

## Contribuir

Las incidencias y propuestas se gestionan en el repositorio interno de Alia. Para cualquier
consulta, escribe a [contacto@alialabs.com](mailto:contacto@alialabs.com).

## Licencia

[AGPL-3](https://www.gnu.org/licenses/agpl-3.0). Copyright © Alia Technologies, S.L.

---

<p align="center">
  <b>Alia Technologies S.L.</b><br>
  Rúa Nova 8, Ourense · 988 319 612<br>
  <a href="mailto:contacto@alialabs.com">contacto@alialabs.com</a> ·
  <a href="https://www.alialabs.com">alialabs.com</a>
</p>

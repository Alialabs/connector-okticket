<p align="center">
  <img src="okticket_connector/docs/img/alia-logo.png" height="52" alt="Alia Technologies"/>
  &nbsp;&nbsp;&nbsp;
  <img src="okticket_connector/docs/img/okticket-logo.png" height="46" alt="OkTicket"/>
</p>

<h1 align="center">Conector OkTicket para Odoo</h1>

<p align="center">
  <a href="https://www.odoo.com"><img src="https://img.shields.io/badge/Odoo-19.0-714B67" alt="Odoo 19.0"/></a>
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
- **Usuarios** — empareja los usuarios de OkTicket con empleados de Odoo por correo electrónico.
- **Categorías** — crea en Odoo un producto de gasto por cada categoría de OkTicket, incluidas
  las variantes facturables.

Y en sentido inverso, de **Odoo a OkTicket**:

- **Centros de coste** — publica las cuentas analíticas de los proyectos de Odoo como centros de
  coste, para poder imputar un ticket a un proyecto desde el móvil.

Está construido sobre el framework [`connector`](https://github.com/OCA/connector) de la OCA:
cada entidad tiene un modelo *binding* que mantiene la correspondencia entre el registro de Odoo
y su identificador remoto.

## Manuales

| Documento | Para quién | Contenido |
|---|---|---|
| **[Manual técnico](okticket_connector/docs/manual-tecnico.html)** ([PDF](okticket_connector/docs/manual-tecnico.pdf)) | Implantadores y administradores | Clonado del repositorio, dependencias, instalación de los módulos, grupos y permisos, configuración de la compañía y del backend, acciones planificadas, multi-compañía y resolución de problemas. |
| **[Manual de usuario](okticket_connector/docs/manual-usuario.html)** ([PDF](okticket_connector/docs/manual-usuario.pdf)) | Usuarios finales | Cómo llegan los gastos, dónde consultarlos, qué añade el conector a la ficha del gasto, adjuntos, categorías, empleados, centros de coste y dudas frecuentes. |

> Los `.html` se ven mejor descargados y abiertos en el navegador: GitHub no renderiza HTML
> directamente desde el repositorio. Los `.pdf` se pueden previsualizar aquí mismo.

## Módulos

| Módulo | Descripción |
|---|---|
| `okticket_connector` | Base del conector: backend de configuración, cliente HTTP con OAuth, registro de eventos e importación de gastos. **Obligatorio.** |
| `okticket_connector_user_synchronization` | Importa los usuarios de OkTicket y los vincula con empleados de Odoo. |
| `okticket_connector_product_synchronization` | Importa el árbol de categorías de OkTicket como productos de gasto. |
| `okticket_connector_cost_center` | Publica cuentas analíticas de Odoo como centros de coste en OkTicket. |
| `okticket_hr_timesheet_cost_center` | Evita una sincronización espuria al crear una compañía nueva con `hr_timesheet`. Opcional. |

## Nota sobre Odoo 19

Odoo 19 **eliminó las hojas de gasto** (`hr.expense.sheet`) al rediseñar el flujo de gastos. Los
tres módulos que se apoyaban en ese modelo —`okticket_connector_hr_expense_sheet`,
`okticket_connector_hr_expense_sheet_grouping` y `okticket_hr_expense_reporting`— **no forman
parte de la rama 19.0**. Los gastos importados quedan como gastos individuales en estado
*Borrador* y se tramitan uno a uno por el circuito estándar de Odoo.

## Instalación rápida

```bash
cd /opt/odoo/addons

# el conector
git clone --branch 19.0 https://github.com/Alialabs/connector-okticket.git

# dependencias OCA
git clone --branch 19.0 https://github.com/OCA/connector.git
git clone --branch 19.0 https://github.com/OCA/queue.git

# dependencia Python
pip install -r connector-okticket/requirements.txt
```

Añade las rutas a `addons_path`, reinicia Odoo e instala los módulos:

```bash
odoo -d <base_de_datos> --stop-after-init \
  -i okticket_connector,okticket_connector_user_synchronization,\
okticket_connector_product_synchronization,okticket_connector_cost_center
```

Después hay que configurar el identificador de compañía, el backend con las credenciales que
facilita OkTicket, y activar las tres acciones planificadas —que se instalan **desactivadas** a
propósito. El [manual técnico](okticket_connector/docs/manual-tecnico.html) lo detalla paso a paso.

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

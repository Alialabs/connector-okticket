# OKticket Connector

### [Alia Technologies](http://www.alialabs.com/)

<img src="http://www.alialabs.com/images/logos/logo-full-big.png" width="215px">

---
### [Okticket](https://www.okticket.es/)
<img src="https://www.okticket.es/img/Okticket-saca-una-foto-tira-el-ticket-gw.svg" width="215px">

--- 
Gestiona tus gastos profesionales desde el móvil , sin tener que conservar tickets y facturas en papel. Utilizarla te resultará de lo más sencillo. Descárgala y úsala. ¡Es gratis!

<img src="https://www.okticket.es/img/icon-appstore-blanco.png" href="https://apps.apple.com/es/app/okticket-gesti%C3%B3n-de-gastos/id1352901020" width="100px">

<img src="https://www.okticket.es/img/icon-googleplay-blanco.png" href="https://play.google.com/store/apps/details?id=es.okticket.app&hl=es" width="100px">

---

#### Funcionalidades del conector de Odoo con Okticket

+ Sincronizar los **tickets** que hagas desde la app
+ Ver todos tus **gastos**
  - Ver información de un gasto específico
+ Crear **proyectos**
+ Ver detalles del **Centro de coste**
+ Ver detalles de la **Hoja de Gastos**
+ Ver los **usuarios** que se sincronizan directamente en base al mail

---



#### Proceso de creación de un ticket nuevo


Una vez dentro de la app de OKticket podremos ver los tickets introducidos en el mes actual

![view_all_icono](okticket_connector/static/images/view_all_icono.png)

---

Si presionamos en el icono de añadir nos desplegará 3 iconos; el primero para **editar** el ticket a mano, el segundo para **sacar una foto** de un ticket y el tercero para introducir el **kilometraje**.

![iconos](okticket_connector/static/images/iconos.png)

---

Al sacar la foto del ticket podremos introducir los datos (O si previamente has seleccionado el icono del lápiz)

![datos_iniciales](okticket_connector/static/images/datos_iniciales.png)

---

Si realizamos scroll vertical, veremos más datos a introducir. Cabe destacar que los campos **Hoja de gasto**, **Centro de gasto**, **Método de pago** y la **Categoría** son proporcionados por el conector de Odoo.

![datos_conector](okticket_connector/static/images/datos_conector.png)

---

Finalmente podremos seleccionar si es *REFACTURABLE* o el *REEMBOLSO* y podremos guardar la información del ticket

![datos_final](okticket_connector/static/images/datos_final.png)

---

#### Proceso de verificación de tickets creados y portal web

Una vez creado el ticket podremos acceder al portal web que nos permite gestionar los datos de los usuarios.

![view_all_web](okticket_connector/static/images/view_all_web.png)

---

En el caso de que no aparezca el ticket que hemos creado recientemente, deberemos sincronizar, utilizando la opción *Sincronizar* del menú lateral de la app

![menu_lateral](okticket_connector/static/images/menu_lateral.png)

---

#### Visualización de datos en Odoo

En la parte del ERP de Odoo tendremos acceder a la opción del menu *Gastos*

![mis_gastos](okticket_connector/static/images/mis_gastos.png)

---

También podremos ver los detalles del gasto deseado al pinchar. Esto nos muestra una vista detallada del mismo.

![gasto_view](okticket_connector/static/images/gasto_view.png)

---

#### Uso de los módulos de Odoo

- Crear *Proyecto*

![crear_proyecto](okticket_connector/static/images/crear_proyecto.png)

Podremos ver los detalles del mismo

![proyecto_view](okticket_connector/static/images/proyecto_view.png)

---

- Ver detalles de **Cost Center**: Para ello nos tenderemos que ir al presupuesto indicado y ver la información del proyecto

![ver_info_proyect](okticket_connector/static/images/ver_info_proyect.png)

Seguidamente pulsaremos en proyecto

![proyecto_edit](okticket_connector/static/images/proyecto_edit.png)

---

También podremos ver información general de un *Presupuesto*, si así lo deseamos

![centro_coste](okticket_connector/static/images/centro_costes.png)

---

- **Hoja de gastos** : Podremos encontrar la información en la vista del cliente

![expense_sheet](okticket_connector/static/images/expense_sheet.png)

---

- En **Empleados**, sección donde se ecuentra los RRHH  aparecerá el *user_id*, el cual se sincroniza automáticamente en base al mail del cliente.

![user_id](okticket_connector/static/images/user_id.png)

---
### Contacto

<p>
Alia Technologies S.L. <br>
Rúa Nova, Nº8, Ourense <br>
Phone: 988 319 612 - 698 155 774 <br>
Email: contacto@alialabs.com <br>
¡Estamos a tu disposición! <br>
</p>



window.FLOWS = {
  soporte: {
    primario:   { nombre: "Soporte IT (demo)", telefono: "600 000 000", correo: "soporte@ejemplo.com" },
    secundario: { nombre: "Soporte IT — Nivel 2 (demo)", telefono: "600 000 001", correo: "soporte2@ejemplo.com" },
  },
  "devices": [
    {
      "id": "tickets",
      "label": "Impresora de tickets",
      "emoji": "🧾",
      "keywords": ["ticket", "tickets", "epson", "tm-20", "recibo", "recibos", "comanda"],
      "problems": [
        {
          "id": "no_imprime",
          "label": "No imprime o da error al imprimir",
          "keywords": ["no imprime", "error", "imprimir", "no sale", "atasco", "no enciende", "no se enciende", "no arranca", "apagada", "apagado", "sin luz"],
          "intro": "Vamos a revisar la impresora de tickets paso a paso. Prueba una cosa cada vez y dime si se soluciona.",
          "steps": [
            {
              "text": "Comprueba que la impresora esté encendida. Si no tiene ninguna luz, pulsa el botón de encendido de la parte inferior derecha. Con la corriente correcta, la luz de arriba debe ponerse azul.",
              "image": { "file": "p13_2.jpeg", "caption": "Botón de encendido de la impresora de tickets (recuadro rojo)." }
            },
            {
              "text": "Comprueba el cable de alimentación (el que va de la impresora al enchufe). Si algún extremo está suelto, conéctalo bien.",
              "image": { "file": "p14_1.jpeg", "caption": "Cable de alimentación bien enchufado a la corriente." }
            },
            {
              "text": "Comprueba el cable de datos en la parte trasera de la impresora: debe ir del conector hasta el portátil, bien conectado por los dos extremos.",
              "image": { "file": "p14_2.jpeg", "caption": "Parte trasera: conector de alimentación (recuadro) y cable de datos al portátil." }
            },
            {
              "text": "Si la impresora sigue apagada, revisa el adaptador de corriente: que esté bien enchufado a la red y que sus dos cables estén bien conectados.",
              "image": { "file": "p15_1.jpeg", "caption": "Adaptador de corriente de la impresora de tickets (Epson PS-180)." }
            },
            {
              "text": "Si no imprime en Comerzzia, comprueba que el cable de datos vaya conectado DIRECTAMENTE a un puerto USB del portátil, sin pasar por el HUB USB o repetidor. Si está en el HUB, cámbialo a un puerto del portátil.",
              "image": { "file": "p16_1.jpeg", "caption": "No conectes el cable al HUB/repetidor USB (marcado con la ✗): debe ir directo a un puerto del portátil." }
            },
            {
              "text": "Comprueba que la impresora esté como predeterminada: pulsa la tecla Windows, escribe \"Impresoras y escáneres\", abre la EPSON TM-T20… y pulsa \"Establecer como predeterminado\". Después cierra Comerzzia y vuelve a abrirlo.",
              "image": { "file": "p18_2.png", "caption": "Ajustes de la impresora en Windows: botón \"Establecer como predeterminado\" y \"Abrir cola de impresión\"." }
            },
            {
              "text": "Si aun así no imprime, en esa misma pantalla pulsa \"Abrir cola de impresión\", pulsa los tres puntos (···) arriba a la derecha y elige \"Cancelar todas\". Luego reinicia el ordenador.",
              "image": { "file": "p19_2.png", "caption": "En la cola de impresión: tres puntos (···) → \"Cancelar todas\"." }
            }
          ]
        }
      ]
    },
    {
      "id": "multifuncion",
      "label": "Impresora multifunción (Canon)",
      "emoji": "🖨️",
      "keywords": ["multifuncion", "multifunción", "canon", "pixma", "sin conexion", "sin conexión", "documento"],
      "problems": [
        {
          "id": "sin_conexion",
          "label": "Aparece \"Sin conexión\" o no imprime",
          "keywords": ["sin conexion", "sin conexión", "no imprime", "offline", "desconectada", "no enciende", "no se enciende", "no arranca", "apagada", "apagado", "sin luz"],
          "intro": "Vamos a revisar la impresora multifunción. Primero mira su estado en Windows y luego probamos paso a paso.",
          "steps": [
            {
              "text": "En el portátil, escribe \"Impresoras y escáneres\" en el buscador de Windows y ábrelo. Selecciona tu impresora para ver el estado.",
              "image": { "file": "p08_1.jpeg", "caption": "Buscar 'Impresoras y escáneres' en Windows." }
            },
            {
              "text": "Comprueba que la impresora esté encendida. Si no tiene ninguna luz, pulsa el botón de encendido de la parte superior izquierda.",
              "image": { "file": "p09_1.jpeg", "caption": "Botón de encendido de la impresora multifunción Canon (recuadro rojo)." }
            },
            {
              "text": "Comprueba el cable de alimentación (impresora ↔ enchufe). Si algún extremo está suelto, conéctalo y enciende la impresora.",
              "image": null
            },
            {
              "text": "Comprueba el cable de datos USB que conecta la impresora con el portátil. Asegúrate de que ambos extremos están bien conectados.",
              "image": { "file": "p10_1.jpeg", "caption": "Cable de datos USB de la multifunción conectado al portátil." }
            }
          ]
        }
      ]
    },
    {
      "id": "tpv",
      "label": "Portátil / TPV de venta",
      "emoji": "💻",
      "keywords": ["portatil", "portátil", "tpv", "ordenador", "comerzzia", "internet", "wifi", "venta", "caja"],
      "problems": [
        {
          "id": "sin_internet",
          "label": "No hay internet / no se conecta",
          "keywords": ["internet", "wifi", "conexion", "conexión", "red", "no navega"],
          "intro": "Vamos a intentar recuperar la conexión a internet del portátil.",
          "steps": [
            { "text": "Apaga el ordenador y vuelve a encenderlo.", "image": null },
            { "text": "Comprueba que el WiFi aparece en las conexiones y, si te la pide, introduce la clave.", "image": null }
          ]
        },
        {
          "id": "comerzzia",
          "label": "No se abre Comerzzia (el programa de venta)",
          "keywords": ["comerzzia", "no abre", "no arranca", "programa venta", "jpos"],
          "intro": "Vamos a abrir Comerzzia (el TPV de venta).",
          "steps": [
            { "text": "Busca el \"Explorador de Aplicaciones\" en el escritorio y haz doble clic para abrirlo.", "image": null },
            {
              "text": "Si no se abre pero parece que \"está ejecutando\", estará minimizado en la barra de tareas: mira en la flecha de iconos ocultos (abajo a la derecha).",
              "image": { "file": "p17_4.png", "caption": "Flecha de iconos ocultos en la barra de tareas de Windows." }
            },
            {
              "text": "Abre el Explorador de Aplicaciones y haz clic en \"Comerzzia JPOS\".",
              "image": { "file": "p17_1.jpeg", "caption": "Explorador de Aplicaciones: icono 'comerzzia JPOS'." }
            }
          ]
        }
      ]
    },
    {
      "id": "lector",
      "label": "Lector de códigos de barras",
      "emoji": "🔦",
      "keywords": ["lector", "codigo", "código", "codigos", "códigos", "barras", "escaner", "escáner", "pistola", "tera", "inateck"],
      "problems": [
        {
          "id": "no_enciende",
          "label": "No enciende / no da ninguna señal",
          "keywords": ["no enciende", "apagado", "no da señal", "sin luz", "no responde"],
          "intro": "Vamos a revisar el lector de códigos.",
          "steps": [
            {
              "text": "Deja pulsado el botón del lector unos segundos para encenderlo.",
              "image": { "file": "p18_1.jpeg", "caption": "Lector de códigos (Tera). La luz azul indica que está encendido." }
            },
            { "text": "Comprueba que tenga batería (déjalo un rato en su base de carga si hace falta).", "image": null }
          ]
        },
        {
          "id": "no_escanea",
          "label": "Enciende pero no escanea",
          "keywords": ["no escanea", "no lee", "no pita", "no coge"],
          "intro": "Vamos a revisar por qué no escanea.",
          "steps": [
            { "text": "Comprueba que el lector esté conectado correctamente (cable o receptor USB en su sitio).", "image": null },
            { "text": "Deja pulsado el botón y espera a que el lector aparezca en la sección Bluetooth del ordenador.", "image": null }
          ]
        }
      ]
    },
    {
      "id": "fiscal",
      "label": "Impresora fiscal (Italia)",
      "emoji": "🇮🇹",
      "flag": "it",
      "keywords": ["fiscal", "italia", "italiana", "fp-81", "fp81", "registrazione", "stato"],
      "problems": [
        {
          "id": "no_imprime",
          "label": "No imprime tickets",
          "keywords": ["no imprime", "error", "no saca ticket"],
          "intro": "Vamos a revisar la impresora fiscal. Prueba una cosa cada vez.",
          "steps": [
            { "text": "Apaga la impresora y vuelve a encenderla; espera unos segundos.", "image": null },
            { "text": "Comprueba que todas las conexiones estén correctas.", "image": null },
            { "text": "Comprueba que esté conectada al router y que tenga internet.", "image": null },
            {
              "text": "Mira la pantalla: debe poner \"STATO REGISTRAZIONE\". Si no lo está, pulsa la tecla \"Chiave\" del teclado de la impresora y vuelve a apagar y encender.",
              "image": { "file": "p20_1.jpeg", "caption": "La pantalla debe mostrar 'STATO REGISTRAZIONE'. Tecla 'Chiave' para activarlo." }
            }
          ],
          "escalate_note": "Si sigue sin funcionar, es un tema de reinstalación de drivers que hace el Departamento IT."
        }
      ]
    },
    {
      "id": "altavoz",
      "label": "Altavoz / música de la tienda",
      "emoji": "🔊",
      "keywords": ["altavoz", "musica", "música", "sonido", "audio", "bluetooth", "no se escucha", "defunc"],
      "problems": [
        {
          "id": "no_suena",
          "label": "No se escucha",
          "keywords": ["no suena", "no se escucha", "sin sonido", "no va la musica", "no va la música"],
          "intro": "Vamos a revisar el altavoz.",
          "steps": [
            {
              "text": "Enciende el Bluetooth del altavoz pulsando el botón trasero (Mode) y búscalo en los ajustes Bluetooth del ordenador para vincularlo.",
              "image": { "file": "p32_1.jpeg", "caption": "Parte trasera del altavoz: Reset, Mode (Bluetooth), Power y Aux." }
            },
            { "text": "En el ordenador, selecciona el altavoz como dispositivo de salida de audio predeterminado.", "image": null },
            { "text": "Si sigue sin sonar: quítalo de los ajustes Bluetooth, resetéalo con el botón de reset, reinicia el ordenador y vuelve a conectarlo.", "image": null },
            { "text": "Como alternativa, instala la app \"Defunc Home\" en el móvil y sigue los pasos para conectar el altavoz a la red WiFi de la tienda.", "image": null }
          ]
        }
      ]
    },
    {
      "id": "pinpad",
      "label": "PINPAD (pago con tarjeta)",
      "emoji": "💳",
      "keywords": ["pinpad", "datafono", "datáfono", "tarjeta", "pago", "cobrar", "no cobra", "verifone", "tpv tarjeta"],
      "problems": [
        {
          "id": "no_funciona",
          "label": "No funciona / no lo reconoce el equipo / falla el pago",
          "keywords": ["no funciona", "no reconoce", "pago", "no cobra", "error de pago", "tarjeta", "no lee tarjeta"],
          "intro": "Vamos a revisar el PINPAD (solo tiendas de España).",
          "steps": [
            {
              "text": "Comprueba que el PINPAD esté conectado DIRECTAMENTE a un puerto USB del portátil (✓), sin pasar por el HUB USB o repetidor.",
              "image": { "file": "p37_3.jpeg", "caption": "Conecta el cable directo a un puerto USB del portátil (✓), no al HUB/repetidor." }
            },
            {
              "text": "Desconéctalo y vuelve a conectarlo en su puerto USB. Espera a que se inicialice del todo.",
              "image": { "file": "p37_1.jpeg", "caption": "PINPAD (Verifone) de pago con tarjeta." }
            },
            {
              "text": "Cierra Comerzzia y vuelve a abrirlo.",
              "image": null
            }
          ],
          "escalate_note": "Si el error persiste, contacta con soporte y, mientras tanto, usa el Datáfono Inalámbrico."
        }
      ]
    },
    {
      "id": "backoffice",
      "label": "Backoffice (Comerzzia admin)",
      "emoji": "🌐",
      "keywords": ["backoffice", "back office", "citees", "comerzzia admin", "admin", "pos.citees", "gestion online", "panel de administracion", "nordlayer", "vpn"],
      "problems": [
        {
          "id": "no_abre",
          "label": "No abre / da error 404",
          "keywords": ["error 404", "404", "no abre", "no carga", "no se ve", "no entra", "pagina no disponible", "backoffice"],
          "intro": "Vamos a revisar el acceso a Backoffice.",
          "steps": [
            {
              "text": "Entra en Backoffice desde https://pos.citees.es/comerzzia-admin/login e introduce el usuario y la contraseña de la tienda.",
              "image": { "file": "p38_1.jpeg", "caption": "Página de acceso a Backoffice: introduce Usuario y Contraseña y pulsa Entrar." }
            },
            {
              "text": "Si aparece error 404 o no se ve la página, comprueba que estás conectado a la red WiFi de la tienda (y no a otra red).",
              "image": null
            },
            {
              "text": "Comprueba que la aplicación NordLayer esté abierta: busca su icono en el escritorio y ejecútala. Si te pide datos de inicio de sesión, contacta con soporte IT.",
              "image": null
            },
            {
              "text": "En NordLayer, selecciona la opción \"CMZ Pampling\" y espera a que se ponga en verde (Connected). Después vuelve a probar a entrar en Backoffice.",
              "image": { "file": "p39_1.png", "caption": "En NordLayer, selecciona 'CMZ Pampling' y espera a que aparezca en verde (Connected)." }
            }
          ],
          "escalate_note": "Si NordLayer te pide iniciar sesión o sigue sin cargar, contacta con soporte IT."
        }
      ]
    },
    {
      "id": "conexion",
      "label": "Conexión y cableado del equipo",
      "emoji": "🔌",
      "keywords": ["cable", "cables", "cableado", "conexion", "conexiones", "conectar", "conectado", "desconectado", "enchufar", "enchufe", "puerto", "usb", "hub", "montar equipo", "instalar equipo", "donde va cada cable", "que cable"],
      "problems": [
        {
          "id": "como_conectar",
          "label": "Cómo conectar el equipo (dónde va cada cable)",
          "keywords": ["cable", "cables", "cableado", "conexion", "conexiones", "conectar", "donde va", "que cable", "hub", "usb", "puerto", "enchufar", "montar", "instalar equipo", "desconectado"],
          "intro": "Así se coloca y se conecta el equipo del mostrador. Revisa que cada cable esté en su sitio.",
          "steps": [
            {
              "text": "El equipo del mostrador se compone de: 1) Portátil, 2) Impresora de tickets, 3) Lector de billetes, 4) Lector de códigos de barras, 5) Ratón USB, 6) HUB USB y 7) Impresora multifunción (debajo del mostrador). En tiendas de España, además, 8) PINPAD.",
              "image": { "file": "p05_1.jpeg", "caption": "Equipo del mostrador: portátil, impresora de tickets, lector de billetes, lector de códigos y ratón." }
            },
            {
              "text": "Conecta los cables al portátil tal y como se ve en la imagen: el cable USB de la impresora de tickets a la izquierda; el cable de corriente del portátil a la derecha; el cable USB de la impresora multifunción a la izquierda; y el cable USB del PINPAD (solo tiendas de España), también a la izquierda.",
              "image": { "file": "p06_1.jpeg", "caption": "Distribución del cableado: cada cable en su puerto (tickets, corriente, multifunción, PINPAD y HUB USB)." }
            },
            {
              "text": "El HUB USB va conectado al puerto USB Tipo C del portátil. En el HUB se conectan dos cosas: 1º el USB del ratón y 2º el USB Bluetooth del lector de códigos de barras.",
              "image": null
            },
            {
              "text": "Con todo conectado, enciende el portátil y comprueba que cada dispositivo responde. Si uno concreto no funciona, búscalo en el menú (impresora de tickets, multifunción, lector, PINPAD…).",
              "image": null
            }
          ],
          "escalate_note": "Si tras revisar el cableado algo sigue sin funcionar, contacta con soporte."
        }
      ]
    }
  ]
}
;

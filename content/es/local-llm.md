---
title: Abrir el LLM local
status: machine
reviewer: null
reviewed_on: null
source_inputs:
  content/en/local-llm.md: da11451a858817b6374abd0e49e5d36eb5412aea38fb02651b360b9d0f2f5ee7
---

{{ local_llm.warning_es }} [@project_spec]

## Computadora portátil

Abre **9_LOCAL_LLM**. Abre **Start Local LLM** para tu sistema: Windows, Mac o Linux. Mantén conectada la unidad. El iniciador abre una página en el navegador. [@project_spec]

Elige **English** o **Español** para el texto de START. Escribe una pregunta corta. Lee la sección de START que indique la respuesta antes de actuar. [@project_spec]

Mantén abierta la ventana del iniciador mientras lo uses. Cierra esa ventana para detenerlo. Si falla, usa START y las tarjetas impresas. [@project_spec]

[[VERIFY: probar la apertura con doble clic y el funcionamiento sin conexión en Windows, Mac y Linux, incluida una computadora con solo puertos USB-A y un adaptador]]

## Android — opcional

Abre **9_LOCAL_LLM → android → PocketPal.apk**. Sigue las indicaciones del teléfono para instalar. [@project_spec]

[[VERIFY: probar la instalación y la importación del modelo local en un teléfono con al menos 6 GB de RAM]]

En PocketPal, abre **Menu → Models → +**. Elige un archivo del almacenamiento local. Selecciona **9_LOCAL_LLM → Model.gguf** en la unidad, o una copia en el teléfono. Carga el modelo. [@pocketpal_local]

Abre la página **Chat**. Mantén START a mano. Para usar las instrucciones del proyecto, crea un **Assistant Pal** y copia el texto de **ui → system-en.txt** o **system-es.txt** en sus instrucciones del sistema. [@pocketpal_local]

[[VERIFY: probar la selección del modelo y las instrucciones del sistema en el APK fijado con todas las conexiones apagadas]]

Usa el archivo local. No uses descargas de modelos ni herramientas en línea durante una interrupción. Si la aplicación no puede abrirlo, usa START. [@project_spec]

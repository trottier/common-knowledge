---
title: Abrir el LLM local
status: machine
reviewer: null
reviewed_on: null
source_inputs:
  content/en/local-llm.md: a13ef1b03393f8390774556a205c940b3e81796214abbff6a815e15920bbe7c6
---

{{ local_llm.warning_es }} [@project_spec]

## Computadora portátil

Abre **9_LOCAL_LLM**. Abre **Start Local LLM** para tu sistema: Windows, Mac o Linux. Mantén conectada la unidad. El iniciador abre una página en el navegador. [@project_spec]

Elige **English** o **Español** para el texto de START. Escribe una pregunta corta. Lee la sección de START que indique la respuesta antes de actuar. [@project_spec]

Mantén abierta la ventana del iniciador mientras lo uses. Cierra esa ventana para detenerlo. Si falla, usa START y las tarjetas impresas. [@project_spec]

[[VERIFY: probar la apertura con doble clic y el funcionamiento sin conexión en Windows, Mac y Linux, incluida una computadora con solo puertos USB-A y un adaptador]]

## Android — opcional

Esta aplicación de desarrollo necesita Android {{ local_llm.android.minimum_android_version }} o posterior y un teléfono {{ local_llm.android.abi }}. Si no se instala o no carga el modelo, usa START y las tarjetas impresas. [@offlinellm_build] [@project_spec]

1. Abre **9_LOCAL_LLM → android → {{ local_llm.android.apk_filename }}**. Sigue las indicaciones del teléfono para instalar. No descargues un modelo ni crees una cuenta. [@project_spec]
2. En {{ local_llm.android.app_name }}, abre **Settings → Import GGUF Model**. Selecciona **9_LOCAL_LLM → {{ local_llm.model_filename }}** en la unidad, o una copia en el teléfono. Espera a que termine la copia. Detente si no hay espacio o falla la importación. [@offlinellm_import]
3. Toca **Use** junto al modelo si aparece. En **Performance**, deja {{ "activado" if local_llm.android.gpu_acceleration else "desactivado" }} **GPU Acceleration (Vulkan)**. Pon **CPU Threads** en {{ local_llm.threads }} si está disponible. Si faltan los controles necesarios, usa START. [@offlinellm_settings] [@project_spec]
4. En **Sampling Parameters**, pon **Context Size** en {{ local_llm.android.context_tokens }} y **Max Tokens** en {{ local_llm.max_output_tokens }}. Ajusta la pantalla de **Temperature** a {{ "%.2f" | format(local_llm.temperature) }}. [@offlinellm_settings] [@project_spec]
5. En **System Prompt**, elige **Custom**. Abre **9_LOCAL_LLM → android → system-en.txt** o **system-es.txt**. Copia todo el texto en **Custom System Prompt**. No copies las instrucciones de la computadora desde **ui**. [@offlinellm_settings] [@project_spec]
6. Vuelve a la página de conversación y toca **New Chat**. Lee START antes de actuar. Las instrucciones de Android solo incluyen los títulos de las secciones de START, no el texto completo. [@offlinellm_chat] [@project_spec]
7. Inicia una conversación nueva si la aplicación indica que el contexto está lleno o que hay un error del modelo. No acortes instrucciones médicas para que quepan. Si el problema continúa, usa START. [@project_spec]

Usa texto. Deja desactivada la lectura en voz alta. Si el texto no funciona sin descargar una fuente o una voz, usa START. [@project_spec]

{{ local_llm.warning_es }} [@project_spec]

[[VERIFY: probar la instalación, los controles exactos, la copia completa de instrucciones, ambos GGUF seleccionados, texto legible sin descargar fuentes ni voces, errores de contexto, y funcionamiento sin conexión incluidos los servicios delegados de fuentes de emojis y voz, en un teléfono con al menos 6 GB de RAM. Siguen pendientes las revisiones de fuentes, avisos de dependencias y dispositivos; no se afirma ausencia total de tráfico ni calidad del modelo.]]

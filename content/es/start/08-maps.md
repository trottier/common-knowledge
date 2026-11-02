---
title: Mapas y lugares
status: machine
reviewer: null
reviewed_on: null
source_inputs: {"content/en/start/08-maps.md": "2fffb1013f905708a800f69c564e9f9914c0792b3d6956e7e798e6587b13b0f5"}
review_required: []
---

## Encuentre sus coordenadas

En iPhone, abra Brújula para ver su ubicación actual, cuando esté disponible. [@apple_compass]
[[VERIFY: probar la presentación en grados, minutos y segundos y los permisos de ubicación en iPhone actuales.]]

Busque su estado y condado en `3_MAPS_AND_PLACES`.
Compare la latitud y longitud con las etiquetas de la cuadrícula.
Use la página y casilla del directorio para encontrar un lugar. [@project_spec]

Una entrada del directorio no garantiza que el lugar esté abierto.
Cada página indica que podría ayudar, pero no se ha confirmado que esté abierto. [@project_spec]

## Si el GPS falla o no está disponible

Las señales GPS pueden bloquearse o falsificarse. [@gps_interference]
Compare la posición del teléfono con las señales de las calles y el índice de lugares. [@project_spec]
Si no coinciden, deje de confiar en la posición del teléfono y compruebe las señales. [@project_spec]
Use la brújula integrada en la unidad para orientar el mapa. [@project_spec]
No siga el punto de ubicación por una ruta peligrosa o cerrada. [@project_spec]
[[VERIFY: probar la orientación de mapas en papel/PDF con la brújula de la unidad, el norte verdadero/de cuadrícula/magnético y las instrucciones seguras cuando las señales y el GPS no coincidan.]]

## Mapa de Android

La aplicación opcional y la guía de importación están en `3_MAPS_AND_PLACES/android`. [@project_spec]
[[VERIFY: añadir los pasos de instalación de OsmAnd e importación del mapa estatal comprobados en teléfonos.]]

## Mapa de computadora portátil

El mapa está en la variante cuya colección de conocimientos detallados lo incluye.
Consulte **¿En qué se diferencia mi unidad?** para encontrar esa variante. [@project_spec]
[[VERIFY: probar el visor y su iniciador en cada sistema operativo de computadora.]]

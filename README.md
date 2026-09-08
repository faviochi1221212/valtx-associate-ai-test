# Asistente de consultas comerciales — Valtx

Prototipo para la prueba técnica **Associate AI Engineer** (Valtx).
Autor: Favio Chavarry Minaya.

## Qué hace

Recibe una consulta (de correo, chat, formulario o teléfono) y decide automáticamente
qué hacer con ella:

- Si puede responderla con la información ya documentada, responde directo.
- Si depende de un dato que cambia con el tiempo (precio, stock, promoción), avisa que
  eso se confirma en el sistema comercial.
- Si el tema no es del área comercial (RRHH, IT), lo redirige.
- Si necesita el criterio de una persona (excepción, reclamo, negociación), genera un
  ticket para el equipo comercial.
- Si no logra entender la consulta, pide que se reformule.

No es un chatbot que "conversa" ni genera texto libre: es un sistema de clasificación y
enrutamiento. La única pieza de IA que usa es un modelo de embeddings para comparar
significado — nunca para redactar respuestas.

## El problema y el valor real

El área comercial recibe cada semana consultas repetitivas de otras áreas, y hoy las
responde un equipo pequeño que está saturado. El encargo pedía un asistente que
"responda todas las consultas, nunca se equivoque, esté listo rápido, corra on-premise
y no cueste mucho" — requisitos que chocan entre sí si se toman literales.

El valor real no está en cubrir el 100% de las preguntas, sino en **quitarle carga al
equipo comercial**: que el sistema resuelva solo lo que puede resolver con certeza y
derive bien todo lo demás. Priorizar "nunca equivocarse" sobre "responder siempre" es
la decisión de diseño que atraviesa todo el proyecto.

## Arquitectura

```
Consulta → Normalizer (limpieza de texto, typos comunes)
         → Motor de similitud (embeddings) contra ~20 preguntas canónicas verificadas
                ├─ score ≥ 0.85 → categoría "a" → responde con el texto documentado, tal cual
                └─ score < 0.85 → reglas por palabras clave →
                        ├─ "b" (precio, stock, promoción, SLA, cuotas...) → plantilla de derivación
                        ├─ "c" (RRHH, IT...) → plantilla de redirección
                        ├─ "d" (excepción, reclamo, negociación...) → genera ticket
                        └─ "e" (no reconocido) → pide reformular
Todo pasa por el Logger (consulta, categoría, respuesta, canal, timestamp) → insumo para medir valor
```

Expuesto vía API (FastAPI) con validación de payload, límite de solicitudes (rate
limiting) y manejo de errores sin exponer detalles internos al cliente.

## Qué construí y qué decidí NO construir

**Construí:** el flujo completo de arriba, con normalización, comparación semántica,
reglas de respaldo, registro, API, un script de medición contra datos reales, y dos
páginas de demo (`/medicion` y `/chat`).

**Decidí NO construir, a propósito:**

- **RAG con base de datos vectorial.** El corpus de referencia son un par de páginas y
  ~20 preguntas reales; no hay ninguna señal en los datos entregados de que vaya a
  crecer. Montar esa infraestructura ahora sería resolver un problema que todavía no
  existe.
- **Un LLM generativo para redactar las respuestas.** Devuelvo el texto documentado tal
  cual, sin parafrasear, porque un modelo podría alterar sin querer un dato verificado
  (ej. "12 meses" → "un año").
- **Sub-clasificar la categoría "c"** entre RRHH e IT específicamente, o **conectar el
  sistema a un correo/chat real.** Son límites de alcance conscientes, documentados
  como tales, no huecos que se me pasaron.
- **Desplegar en la nube** (Vercel, Render, etc.). Iría directamente en contra del
  requisito de que corra on-premise.

## Supuestos

- El usuario final es alguien de las áreas internas de Valtx, no un cliente externo.
- El volumen real de consultas es bajo, consistente con la muestra entregada (80
  consultas).
- "On-premise" se interpreta como: sin dependencia de una API externa cobrada por uso.
- La forma de derivar un caso depende del canal: correo o formulario genera un ticket;
  chat o teléfono responde de inmediato con el contacto adecuado.
- El material de prueba (CSV y documentos) no contiene datos reales de producción — el
  propio documento de Valtx los describe como "extractos parciales... pueden estar
  desactualizados".

## Criterios para usar IA

El único modelo de IA en el sistema es `paraphrase-multilingual-MiniLM-L12-v2`
(`sentence-transformers`), que corre local, sin GPU, y solo compara qué tan parecidas
son dos frases en significado — nunca genera texto.

El umbral de similitud (0.85) no salió de una elección arbitraria: se ajustó después de
auditar el sistema contra las 80 consultas reales. Con un umbral más bajo (0.75)
aparecían coincidencias que sonaban parecidas pero eran de otro tema (por ejemplo,
confundir una pregunta sobre tiempo de entrega con una de garantía). Prefiero perder
algo de cobertura —esos casos quedan pidiendo que se reformule— antes que arriesgarme a
responder con confianza algo incorrecto.

Para todo lo que no necesita este tipo de comparación semántica (excepciones, temas
fuera de alcance, datos que cambian seguido) uso reglas simples de palabras clave: son
más baratas, más fáciles de auditar y no tienen riesgo de inventar nada.

## Cómo se mide el valor

- Qué porcentaje de consultas se resuelve solo, sin que nadie del equipo intervenga.
- Si el sistema deriva bien los casos que no puede resolver (sin confundir categorías).
- Auditoría manual periódica de una muestra de respuestas ya dadas, para confirmar que
  el dato entregado sigue siendo correcto.
- Tiempo de respuesta del sistema comparado con el tiempo actual del equipo.

**Resultado medido contra las 80 consultas reales del CSV** (reproducible con
`python tests/test_pipeline.py`):

| Categoría | Cantidad | % | Baseline | Diferencia | Estado |
|---|---|---|---|---|---|
| a | 31 | 38.75% | 37.50% | +1.25pp | dentro |
| b | 18 | 22.50% | 21.25% | +1.25pp | dentro |
| c | 7 | 8.75% | 10.00% | -1.25pp | dentro |
| d | 11 | 13.75% | 16.25% | -2.50pp | dentro |
| e | 13 | 16.25% | 15.00% | +1.25pp | dentro |
| **Total** | **80** | **100%** | — | — | — |

Baseline = porcentaje esperado por categoría, calculado a mano revisando las 80
consultas una por una antes de construir el sistema. Las 5 categorías quedan dentro del
margen de tolerancia definido (3 puntos porcentuales).

## Limitaciones conocidas

- La categoría "c" no distingue entre RRHH e IT; usa un mensaje genérico de
  redirección.
- Las reglas de palabras clave usan coincidencia literal, no de raíz gramatical —
  variantes muy alejadas de la palabra exacta pueden no matchear y caer en "e".
- El sistema es más conservador que la clasificación manual de referencia: algunas
  consultas que un evaluador humano reconocería por contexto (SLA, cuotas, envíos)
  pueden caer en "e" si no contienen una keyword configurada. Esto nunca deriva en una
  respuesta incorrecta, solo en pedir reformulación.
- No hay integración real con Gmail, chat corporativo o telefonía — el prototipo simula
  la consulta ya identificada por canal.

## Estructura del repositorio

```
valtx-associate-ai-test/
├── data/
│   ├── qa_canonico.json      # ~20 preguntas canónicas verificadas, con sus variantes
│   └── consultas.csv          # las 80 consultas reales entregadas para la prueba
├── src/
│   ├── normalizer.py          # limpieza de texto (minúsculas, typos comunes)
│   ├── similarity_engine.py   # comparación semántica contra qa_canonico.json
│   ├── reglas_clasificacion.py # reglas por palabras clave (b/c/d/e)
│   ├── router.py               # integra todo lo anterior en un único flujo de decisión
│   └── logger.py               # registro estructurado en logs/consultas.jsonl
├── app.py                      # API (FastAPI): /consulta, /medicion, /chat
├── tests/                      # pruebas unitarias e integración de cada módulo
│   └── test_pipeline.py        # corre el sistema contra consultas.csv y mide el resultado
├── requirements.txt
└── README.md
```

## Cómo correrlo

```bash
git clone https://github.com/faviochi1221212/valtx-associate-ai-test.git
cd valtx-associate-ai-test
python -m venv venv
venv\Scripts\activate        # Windows (usar source venv/bin/activate en Linux/Mac)
pip install -r requirements.txt
```

**Correr las pruebas:**
```bash
python -m pytest tests\ -v
```

**Correr el sistema de medición contra las 80 consultas reales:**
```bash
python tests/test_pipeline.py
# o contra un CSV distinto:
python tests/test_pipeline.py --csv otra_ruta.csv
```

**Levantar la API:**
```bash
uvicorn app:app --reload
```

Con el servidor corriendo:
- `POST /consulta` — endpoint real: recibe `{"texto": "...", "canal": "..."}` y devuelve
  `{"categoria": "...", "respuesta": "..."}`.
- `GET /medicion` — panel visual con el resultado de las 80 consultas, para revisión y
  demo.
- `GET /chat` — página simple para probar consultas individuales en vivo, sin usar la
  terminal.

## Proceso de construcción

El proyecto se construyó por historias de usuario (HU1 a HU9), cada una con su propio
ciclo de auditoría, QA manual y commit — el historial de Git conserva la evidencia de
varios hallazgos reales encontrados y corregidos durante el desarrollo (por ejemplo, el
ajuste del umbral de similitud de 0.75 a 0.85 después de detectar falsos positivos, y
la corrección de dos entradas de `qa_canonico.json` que trataban como "hecho
documentado" algo que en realidad debía escalarse a una persona). Ese historial es
consultable con `git log --oneline`.

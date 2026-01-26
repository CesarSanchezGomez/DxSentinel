## Estructura del Proyecto

```
DxSentinel/
│
├── backend/
│   ├── __init__.py
│   │
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   │
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   └── v1/
│   │   │       ├── __init__.py
│   │   │       ├── router.py
│   │   │       └── endpoints/
│   │   │           ├── __init__.py
│   │   │           ├── upload.py
│   │   │           ├── process.py
│   │   │           └── health.py
│   │   │
│   │   ├── core/
│   │   │   ├── __init__.py
│   │   │   ├── config.py
│   │   │   └── storage.py
│   │   │
│   │   ├── models/
│   │   │   ├── __init__.py
│   │   │   ├── upload.py
│   │   │   └── process.py
│   │   │
│   │   └── services/
│   │       ├── __init__.py
│   │       ├── file_service.py
│   │       └── parser_service.py
│   │
│   ├── core/
│   │   ├── __init__.py
│   │   │
│   │   ├── parsing/
│   │   │   ├── __init__.py
│   │   │   ├── xml_loader.py
│   │   │   ├── xml_parser.py
│   │   │   ├── xml_normalizer.py
│   │   │   ├── xml_elements.py
│   │   │   └── exceptions.py
│   │   │
│   │   └── generators/
│   │       └── golden_record/
│   │           ├── __init__.py
│   │           ├── csv_generator.py
│   │           ├── element_processor.py
│   │           ├── field_filter.py
│   │           ├── field_finder.py
│   │           ├── language_resolver.py
│   │           └── exceptions.py
│   │
│   └── storage/
│       ├── uploads/
│       └── outputs/
│
├── frontend/
│   ├── static/
│   │   └── js/
│   │       ├── upload.js
│   │       └── process.js
│   │
│   └── templates/
│       ├── base.html
│       ├── index.html
│       ├── upload.html
│       └── result.html
│
├── .env
├── requirements.txt
└── README.md
```



### Descripción General

- **backend/**: API y lógica de negocio basada en FastAPI.
- **frontend/**: Interfaz web con HTML + JavaScript.
- **core/parsing**: Motor de parsing XML desacoplado del API.
- **generators/golden_record**: Generación estructurada de salidas CSV.
- **storage/**: Persistencia local de archivos y resultados.

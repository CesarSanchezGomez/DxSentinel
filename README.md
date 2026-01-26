## Estructura del Proyecto

```
DxSentinel/
│
├── backend/
│ ├── init.py
│ │
│ ├── app/
│ │ ├── init.py
│ │ ├── main.py
│ │ │
│ │ ├── api/
│ │ │ ├── init.py
│ │ │ ├── deps.py
│ │ │ └── v1/
│ │ │ ├── init.py
│ │ │ ├── router.py
│ │ │ └── endpoints/
│ │ │ ├── init.py
│ │ │ ├── upload.py
│ │ │ ├── process.py
│ │ │ └── health.py
│ │ │
│ │ ├── core/
│ │ │ ├── init.py
│ │ │ ├── config.py
│ │ │ └── storage.py
│ │ │
│ │ ├── models/
│ │ │ ├── init.py
│ │ │ ├── upload.py
│ │ │ └── process.py
│ │ │
│ │ └── services/
│ │ ├── init.py
│ │ ├── file_service.py
│ │ └── parser_service.py
│ │
│ ├── core/
│ │ ├── init.py
│ │ │
│ │ ├── parsing/
│ │ │ ├── init.py
│ │ │ ├── xml_loader.py
│ │ │ ├── xml_parser.py
│ │ │ ├── xml_normalizer.py
│ │ │ ├── xml_elements.py
│ │ │ └── exceptions.py
│ │ │
│ │ └── generators/
│ │ └── golden_record/
│ │ ├── init.py
│ │ ├── csv_generator.py
│ │ ├── element_processor.py
│ │ ├── field_filter.py
│ │ ├── field_finder.py
│ │ ├── language_resolver.py
│ │ └── exceptions.py
│ │
│ └── storage/
│ ├── uploads/
│ └── outputs/
│
├── frontend/
│ ├── static/
│ │ └── js/
│ │ ├── upload.js
│ │ └── process.js
│ │
│ └── templates/
│ ├── base.html
│ ├── index.html
│ ├── upload.html
│ └── result.html
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

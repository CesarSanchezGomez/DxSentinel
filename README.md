## Estructura del Proyecto

```
DxSentinel/
│
.
├── .env
├── .gitignore
├── README.md
├── requirements.txt
│
├── backend
│   ├── __init__.py
│   │
│   ├── app
│   │   ├── main.py
│   │   ├── __init__.py
│   │   │
│   │   ├── api
│   │   │   └── v1
│   │   │       ├── router.py
│   │   │       ├── extract_counties.py
│   │   │       ├── health.py
│   │   │       ├── process.py
│   │   │       ├── split.py
│   │   │       └── upload.py
│   │   │
│   │   ├── auth
│   │   │   ├── dependencies.py
│   │   │   ├── router.py
│   │   │   └── supabase_client.py
│   │   │
│   │   ├── core
│   │   │   ├── config.py
│   │   │   └── storage.py
│   │   │
│   │   ├── models
│   │   │   ├── process.py
│   │   │   └── upload.py
│   │   │
│   │   └── services
│   │       ├── file_service.py
│   │       └── parser_service.py
│   │
│   ├── core
│   │   ├── generators
│   │   │   ├── golden_record
│   │   │   │   ├── csv_generator.py
│   │   │   │   ├── element_processor.py
│   │   │   │   ├── exceptions.py
│   │   │   │   ├── field_filter.py
│   │   │   │   ├── field_finder.py
│   │   │   │   └── language_resolver.py
│   │   │   │
│   │   │   ├── metadata
│   │   │   │   ├── business_key_resolver.py
│   │   │   │   ├── field_categorizer.py
│   │   │   │   ├── field_identifier_extractor.py
│   │   │   │   └── metadata_generator.py
│   │   │   │
│   │   │   └── splitter
│   │   │       └── layout_splitter.py
│   │   │
│   │   └── parsing
│   │       ├── main.py
│   │       ├── orchestrator.py
│   │       ├── metadata_manager.py
│   │       │
│   │       ├── exceptions
│   │       │   └── xml_exceptions.py
│   │       │
│   │       ├── loaders
│   │       │   └── xml_loader.py
│   │       │
│   │       ├── models
│   │       │   └── xml_elements.py
│   │       │
│   │       ├── normalizers
│   │       │   └── xml_normalizer.py
│   │       │
│   │       ├── parsers
│   │       │   └── xml_parser.py
│   │       │
│   │       └── utils
│   │           └── xml_merger.py
│   │
│   └── storage
│       ├── metadata
│       │   └── process_1769928382_USA
│       │       └── 004622_v1
│       │           ├── document.json
│       │           ├── document.pkl
│       │           └── metadata.json
│       │
│       ├── outputs
│       │   ├── golden_record_template_en-us_USA.csv
│       │   ├── golden_record_template_en-us_USA_metadata.json
│       │   ├── golden_record_template_en-us_MEX.csv
│       │   ├── golden_record_template_en-us_MEX_metadata.json
│       │   ├── golden_record_template_es-mx_USA.csv
│       │   └── golden_record_template_es-mx_USA_metadata.json
│       │
│       └── uploads
│           └── *.xml
│
├── frontend
│   ├── static
│   │   ├── css
│   │   │   └── *.css
│   │   ├── js
│   │   │   ├── auth-callback.js
│   │   │   ├── auth-login.js
│   │   │   ├── split.js
│   │   │   └── upload.js
│   │   └── images
│   │       ├── favicon.ico
│   │       └── logo-*.png
│   │
│   └── templates
│       ├── base.html
│       ├── home.html
│       ├── login.html
│       ├── callback.html
│       ├── split.html
│       └── upload.html
│
└── .git
    └── (repositorio git interno)



### Descripción General

- **backend/**: API y lógica de negocio basada en FastAPI.
- **frontend/**: Interfaz web con HTML + JavaScript.
- **core/parsing**: Motor de parsing XML desacoplado del API.
- **generators/golden_record**: Generación estructurada de salidas CSV.
- **storage/**: Persistencia local de archivos y resultados.

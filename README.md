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
│   │   │           ├── extract_counties.py
│   │   │           ├── upload.py
│   │   │           ├── process.py
│   │   │           ├── split.py
│   │   │           └── health.py
│   │   │
│   │   ├── auth/
│   │   │   ├── __init__.py
│   │   │   ├── dependencies.py
│   │   │   ├── router.py
│   │   │   └── supabase_client.py
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
│   │       ├─── golden_record/
│   │       │   ├── __init__.py
│   │       │   ├── csv_generator.py
│   │       │   ├── element_processor.py
│   │       │   ├── field_filter.py
│   │       │   ├── field_finder.py
│   │       │   ├── language_resolver.py
│   │       │   └── exceptions.py
│   │       │
│   │       ├─── metadata/
│   │       │   ├── __init__.py
│   │       │   ├── business_ket_resolver.py
│   │       │   ├── field_categorizer.py
│   │       │   ├── field_identifier_extractor.py
│   │       │   └── metadata_generator.py
│   │       │
│   │       └─── golden_record/
│   │           ├── __init__.py
│   │           └── layout_splitter.py   
│   │
│   └── storage/
│       ├── uploads/
│       └── outputs/
│
├── frontend/
│   ├── static/
│   │   ├── css/
│   │   │   ├── auth.css
│   │   │   ├── base.css
│   │   │   ├── buttons.css
│   │   │   ├── cards.css
│   │   │   ├── editors.css
│   │   │   ├── footer.css
│   │   │   ├── forms.css
│   │   │   ├── header.css
│   │   │   ├── layout.css
│   │   │   ├── modals.css
│   │   │   └── responsive.css
│   │   │
│   │   ├── js/
│   │   │   ├── auth-callback.js
│   │   │   ├── auth-login.js
│   │   │   ├── split.js
│   │   │   └── upload.js
│   │   │
│   │   └── images/
│   │       ├── favicon.ico
│   │       ├── logo-dxgrow-300x180.png
│   │       └── logo-dxgrow-inverted-300-180.png
│   │
│   └── templates/
│       ├── base.html
│       ├── callback.html
│       ├── home.html
│       ├── login.html
│       ├── split.html
│       └── upload.html
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

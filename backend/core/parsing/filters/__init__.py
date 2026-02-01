# backend/core/parsing/filters/__init__.py
"""
Módulo de filtros XML para el parser.
Filtra elementos manteniendo estructura del árbol.
"""

from .xml_filter import XMLFilter, create_hris_filter

__all__ = ['XMLFilter', 'create_hris_filter']
# comparator/validators/base_rule.py - CORREGIDO
"""
Contrato base para todas las reglas de validación.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from ..models import (
    ValidationError, ValidationContext, ValidationScope,
    FieldMetadata, EntityMetadata
)


class BaseRule(ABC):
    """Interfaz base para reglas de validación."""
    
    def __init__(self, rule_id: str, description: str):
        self.rule_id = rule_id
        self.description = description
        self.enabled = True
    
    @property
    @abstractmethod
    def scope(self) -> ValidationScope:
        """Ámbito de aplicación de la regla."""
        pass
    
    @abstractmethod
    def validate(
        self, 
        context: ValidationContext,
        entity_id: Optional[str] = None,
        field_metadata: Optional[FieldMetadata] = None,
        value: Optional[str] = None,
        row_index: Optional[int] = None,
        csv_row_index: Optional[int] = None,
        column_name: Optional[str] = None,
        person_id_external: Optional[str] = None  # <-- NUEVO PARÁMETRO
    ) -> List[ValidationError]:
        """
        Ejecuta la validación.
        
        Args:
            context: Contexto de validación
            entity_id: ID de entidad (opcional dependiendo del scope)
            field_metadata: Metadata del campo (opcional)
            value: Valor a validar (opcional)
            row_index: Índice de fila en datos (opcional)
            csv_row_index: Índice real en CSV (opcional)
            column_name: Nombre original de columna (opcional)
            person_id_external: Identificador único del registro (opcional)
            
        Returns:
            Lista de errores de validación
        """
        pass
    
    def should_skip(
        self, 
        field_metadata: Optional[FieldMetadata] = None,
        value: Optional[str] = None
    ) -> bool:
        """
        Determina si la regla debe saltarse para este campo/valor.
        
        Args:
            field_metadata: Metadata del campo
            value: Valor a validar
            
        Returns:
            True si la regla debe saltarse
        """
        # Por defecto, no saltar
        return False
    
    def __repr__(self) -> str:
        return f"<Rule {self.rule_id}: {self.description}>"
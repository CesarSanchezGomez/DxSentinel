# src/vstructure/comparator/orchestrator.py - MEJORADO
"""
Punto de entrada principal del comparator.
"""

from typing import Any, Dict, Tuple, Optional, List
import time

from .models import ValidationContext, BatchValidationResult, ValidationError
from .rule_registry import RuleRegistry
from .rule_engine import RuleEngine
from .context_adapter import MetadataAdapter
from .errors import ComparatorErrors


class ComparisonOrchestrator:
    """Orquestador principal del comparator."""
    
    def __init__(self):
        self.rule_registry = RuleRegistry()
        self.rule_engine = RuleEngine(self.rule_registry)
    
    def create_validation_context(
        self,
        transform_context,
        metadata_instance_id: str = None,
        metadata_version: Optional[str] = None,
        parsed_metadata: Dict[str, Any] = None
    ) -> Tuple[Optional[ValidationContext], Optional[str]]:
        """
        Crea contexto de validación combinando transform y metadata.
        
        Args:
            transform_context: Contexto del transformer
            metadata_instance_id: ID de instancia metadata (opcional si parsed_metadata se proporciona)
            metadata_version: Versión de metadata (opcional)
            parsed_metadata: Metadata ya parseada (alternativa a cargarla)
            
        Returns:
            Tupla (ValidationContext, mensaje_error)
        """
        try:
            # 1. Cargar/adaptar metadata - SIEMPRE usar parsed_metadata si está disponible
            if parsed_metadata is not None:
                print(f"📥 Adaptando metadata parseada proporcionada...")
                metadata_context = MetadataAdapter.adapt_parsed_metadata(
                    parsed_metadata=parsed_metadata
                )
                
                # Verificar si la adaptación fue exitosa
                if metadata_context and hasattr(metadata_context, 'stats'):
                    if metadata_context.stats.get("error"):
                        print(f"   ⚠ Error en metadata adaptada: {metadata_context.stats['error']}")
                        # No fallar inmediatamente, intentar cargar desde instancia
                    else:
                        print(f"   ✓ Metadata parseada adaptada exitosamente")
                        source_ok = True
                else:
                    print(f"   ⚠ Metadata context no creado correctamente")
                    source_ok = False
                
                # Si la adaptación de parsed_metadata falló, intentar cargar desde instancia
                if not source_ok and metadata_instance_id is not None:
                    print(f"   ⚠ Fallback: cargando metadata desde instancia...")
                    metadata_context = MetadataAdapter.load_and_adapt_metadata(
                        instance_id=metadata_instance_id,
                        version=metadata_version
                    )
            elif metadata_instance_id is not None:
                # Cargar desde instancia
                print(f"📥 Cargando metadata: {metadata_instance_id} v{metadata_version or 'latest'}")
                metadata_context = MetadataAdapter.load_and_adapt_metadata(
                    instance_id=metadata_instance_id,
                    version=metadata_version
                )
            else:
                return None, "Se requiere metadata_instance_id o parsed_metadata"
            
            # Verificar si hubo error
            if hasattr(metadata_context, 'stats') and metadata_context.stats.get("error"):
                error_msg = metadata_context.stats.get("error", "Error desconocido en metadata")
                print(f"❌ Error con metadata: {error_msg}")
                return None, f"Error con metadata: {error_msg}"
            
            print(f"   ✓ Metadata cargada: {len(metadata_context.entities)} entidades, "
                f"{len(metadata_context.field_by_full_path)} campos")
            
            # 2. Crear contexto de validación
            validation_context = ValidationContext(
                transform_context=transform_context,
                metadata_context=metadata_context
            )
            
            # 3. Configurar estadísticas iniciales
            validation_context.validation_stats = {
                "start_time": time.time(),
                "metadata_source": f"{metadata_context.source_instance}_{metadata_context.source_version}",
                "csv_columns": len(transform_context.parsed_columns),
                "csv_entities": len(transform_context.entities),
                "metadata_entities": len(metadata_context.entities),
                "metadata_fields": len(metadata_context.field_by_full_path)
            }
            
            return validation_context, None
            
        except Exception as e:
            print(f"❌ Error creando contexto de validación: {str(e)}")
            import traceback
            traceback.print_exc()
            return None, f"Error creando contexto de validación: {str(e)}"
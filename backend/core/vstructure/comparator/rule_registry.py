# comparator/rule_registry.py
"""
Registro central de reglas.
"""

from typing import Dict, Type, List, Optional
from .models import RuleConfiguration
from .validators import ALL_RULES, BaseRule


class RuleRegistry:
    """Registro y gestión de reglas de validación."""
    
    def __init__(self):
        self._rules: Dict[str, Type[BaseRule]] = {}
        self._rule_instances: Dict[str, BaseRule] = {}
        self._configurations: Dict[str, RuleConfiguration] = {}
        
        # Registrar reglas por defecto
        self.register_default_rules()
    
    def register_default_rules(self):
        """Registra todas las reglas por defecto."""
        for rule_id, rule_class in ALL_RULES.items():
            self.register_rule(rule_id, rule_class)
    
    def register_rule(self, rule_id: str, rule_class: Type[BaseRule]):
        """Registra una nueva regla."""
        if rule_id in self._rules:
            raise ValueError(f"Regla ya registrada: {rule_id}")
        
        self._rules[rule_id] = rule_class
        
        # Crear instancia por defecto
        instance = rule_class()
        self._rule_instances[rule_id] = instance
        
        # Configuración por defecto
        self._configurations[rule_id] = RuleConfiguration(
            rule_id=rule_id,
            enabled=True,
            scope=instance.scope
        )
    
    def get_rule(self, rule_id: str) -> Optional[BaseRule]:
        """Obtiene una instancia de regla."""
        if rule_id not in self._rule_instances:
            return None
        
        instance = self._rule_instances[rule_id]
        
        # Aplicar configuración si existe
        config = self._configurations.get(rule_id)
        if config:
            instance.enabled = config.enabled
        
        return instance
    
    def get_enabled_rules(self, scope: Optional[str] = None) -> List[BaseRule]:
        """Obtiene todas las reglas habilitadas, opcionalmente filtradas por scope."""
        enabled_rules = []
        
        for rule_id, instance in self._rule_instances.items():
            config = self._configurations.get(rule_id)
            
            if config and config.enabled:
                if scope is None or instance.scope.value == scope:
                    enabled_rules.append(instance)
        
        return enabled_rules
    
    def configure_rule(self, rule_id: str, enabled: bool = None, **params):
        """Configura una regla específica."""
        if rule_id not in self._configurations:
            raise ValueError(f"Regla no encontrada: {rule_id}")
        
        config = self._configurations[rule_id]
        
        if enabled is not None:
            config.enabled = enabled
        
        if params:
            config.params.update(params)
    
    def list_rules(self) -> List[Dict]:
        """Lista todas las reglas registradas con su estado."""
        rules_info = []
        
        for rule_id, instance in self._rule_instances.items():
            config = self._configurations.get(rule_id, RuleConfiguration(rule_id=rule_id))
            
            rules_info.append({
                "rule_id": rule_id,
                "description": instance.description,
                "scope": instance.scope.value,
                "enabled": config.enabled,
                "class": instance.__class__.__name__
            })
        
        return rules_info
from typing import Dict


class ModuleRegistry:

    def __init__(self):

        self.modules = {}

    def register(
        self,
        name: str,
        version: str,
        description: str,
    ):

        self.modules[name] = {
            "name": name,
            "version": version,
            "description": description,
            "status": "active",
        }

    def list_modules(self):

        return list(self.modules.values())

    def module_count(self):

        return len(self.modules)


registry = ModuleRegistry()

registry.register(
    "Document Intelligence",
    "1.0",
    "Document understanding",
)

registry.register(
    "Entity Intelligence",
    "1.0",
    "Entity extraction",
)

registry.register(
    "Entity Database",
    "1.0",
    "Business entities",
)

registry.register(
    "Product Profiles",
    "1.0",
    "Product knowledge",
)

registry.register(
    "Tender Profiles",
    "1.0",
    "Tender knowledge",
)

registry.register(
    "Tender Comparison",
    "1.0",
    "Tender comparison",
)

registry.register(
    "Executive Decision",
    "1.0",
    "Decision engine",
)

registry.register(
    "Business Memory",
    "1.0",
    "Long-term business memory",
)
"""Project domain services shared by HTTP, MCP, and workflow adapters.

Import concrete services from their modules. Keeping package initialisation free
of service imports prevents schema modules from forming circular dependencies.
"""

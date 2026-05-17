"""framework — Núcleo genérico del sistema multi-asset de alerta temprana.

Las funciones aquí son agnósticas respecto al asset concreto. Cada asset
(cobalt, copper, …) vive bajo `assets/<asset>/` y reutiliza este framework
parametrizando un `AssetConfig` con su diccionario y umbrales.
"""

"""JakselScript v0.1 — bahasa pemrograman gaul Jaksel."""

from .lexer import lex
from .parser import parse
from .interpreter import Interpreter
from .cli import VERSION

__version__ = VERSION
__all__ = ["lex", "parse", "Interpreter", "__version__"]

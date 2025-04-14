# -*- coding: utf-8 -*-
import importlib
try:
    importlib.reload(main)
except ImportError:
    from . import main
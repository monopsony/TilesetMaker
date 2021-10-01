import os
import re
from setuptools import setup, find_packages
from os import path

# Scripts
setup(
    name="Tilesetmaker",
    version="0.1.1",
    description="Make tilesets",
    author="Groog",
    py_modules=["table", "window", "run"],
    # scripts=["tsm.py"],
    entry_points={"console_scripts": ["tsm=run:main"]},
)

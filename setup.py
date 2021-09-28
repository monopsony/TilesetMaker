from distutils.core import setup
import setuptools
import os

setup(
    name="Tilesetmaker",
    version="0.1",
    description="Make tilesets",
    author="Groog",
    scripts=["tsm"],
    py_modules=["table", "window", "tsm"],
)


from pathlib import Path

from setuptools import find_packages, setup

import andesite

long_description = Path("README.md").read_text()

setup(
    name="andesite.py",
    version=andesite.__version__,
    description="Andesite client for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Giesela Inc.",
    packages=find_packages(exclude=("examples", "docs", "tests")),
    python_requires=">=3.7",
    install_requires=[
        "aiohttp",
        "lettercase",
        "websockets",
        "yarl",
    ],
)

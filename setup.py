from pathlib import Path

import setuptools

import andesite

long_description = Path("README.md").read_text()

setuptools.setup(
    name="andesite.py",
    version=andesite.__version__,
    description="Andesite client for Python",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Giesela Inc.",
    author_email="team@giesela.dev",
    url="https://github.com/gieseladev/andesite.py",

    packages=setuptools.find_packages(exclude=("examples", "docs", "tests")),
    python_requires="~=3.7",

    install_requires=[
        "aiobservable",
        "aiohttp",
        "lettercase",
        "websockets",
        "yarl",
    ],
)

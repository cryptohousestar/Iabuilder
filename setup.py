from setuptools import find_packages, setup

with open("requirements.txt") as f:
    requirements = [
        line.strip() for line in f if line.strip() and not line.startswith("#")
    ]

setup(
    name="iabuilder",
    version="0.1.0",
    description="IABuilder - Intelligent Architecture Builder with Multi-Provider LLM Support",
    author="Ivan Gonzalez",
    author_email="admin@iabuilder.app",
    packages=find_packages(),
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "iabuilder=iabuilder.main:main",
        ],
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)

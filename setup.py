from setuptools import setup, find_namespace_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="pypeeker-cli",
    version="1.2.0",
    author="Agent Tools",
    description="A zero-dependency Python CLI toolset designed for AI agents to analyze codebases with surgical precision.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_namespace_packages(include=["pypeeker*", "cg*"]),
    entry_points={
        "console_scripts": [
            "pypeeker=pypeeker.cli:main",
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=[
        "mcp>=0.1.0",
    ],
)

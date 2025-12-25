"""
Setup script for CpyTro
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="cpytro",
    version="1.0.0",
    author="CpyTro Team",
    author_email="dev@cpytro.net",
    description="Mobile Mining Cryptocurrency",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/cpytro/cpytro-coin",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.7",
    install_requires=[
        "cryptography>=3.4",
        "requests>=2.25",
        "flask>=2.0",  # สำหรับ API server
        "psutil>=5.8",  # สำหรับ monitoring
    ],
    entry_points={
        "console_scripts": [
            "cpytro=main:main",
            "cpytro-miner=mobile_miner:main",
            "cpytro-wallet=wallet_cli:main",
        ],
    },
)

"""
Setup configuration for FinSight Python SDK
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="finsight",
    version="1.0.0",
    author="FinSight",
    author_email="support@finsight.com",
    description="Official Python SDK for FinSight Financial Data API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/finsight/finsight-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "Intended Audience :: Financial and Insurance Industry",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Topic :: Office/Business :: Financial",
        "Topic :: Software Development :: Libraries :: Python Modules",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0",
        "aiohttp>=3.8.0",
    ],
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-asyncio>=0.20.0",
            "black>=22.0.0",
            "flake8>=5.0.0",
            "mypy>=0.990",
        ]
    },
    keywords="finance, financial data, SEC, stock market, API, SDK",
    project_urls={
        "Documentation": "https://docs.finsight.com",
        "Source": "https://github.com/finsight/finsight-python",
        "Tracker": "https://github.com/finsight/finsight-python/issues",
    },
)

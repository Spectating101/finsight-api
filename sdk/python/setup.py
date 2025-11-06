from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="finsight-api",
    version="1.0.0",
    author="FinSight",
    author_email="support@finsight.io",
    description="Official Python SDK for FinSight Financial Data API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/finsight-python",
    packages=find_packages(),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Office/Business :: Financial",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.25.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.0",
            "black>=21.0",
            "flake8>=3.9",
        ],
    },
    keywords="finance financial-data stock-market api sec-edgar",
    project_urls={
        "Documentation": "https://docs.finsight.io",
        "Source": "https://github.com/yourusername/finsight-python",
        "Bug Reports": "https://github.com/yourusername/finsight-python/issues",
    },
)

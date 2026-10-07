"""
Setup configuration for pompom-meta-publisher package.
"""
from pathlib import Path
from setuptools import find_packages, setup

readme = Path(__file__).parent / "README.md"
long_description = readme.read_text(encoding="utf-8") if readme.exists() else ""

setup(
    name="pompom-meta-publisher",
    version="0.1.0",
    description="Meta (Facebook + Instagram) publishing for Pompom Hills content",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Pompom Hills Team",
    author_email="",
    url="",
    packages=find_packages(),
    package_data={
        "pompom_meta_publisher": ["py.typed"],
        "pompom_publisher_common": ["py.typed"],
        "pompom_tiktok_publisher": ["py.typed"],
        "pompom_youtube_publisher": ["py.typed"],
    },
    python_requires=">=3.10",
    install_requires=[
        # Standard library only for core functionality
        # boto3 is optional, loaded dynamically if S3 storage is used
    ],
    extras_require={
        "s3": ["boto3>=1.26.0"],
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "ruff>=0.1.0",
            "mypy>=1.0.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "publish-pompom-reel=publish_pompom_reel:main",
        ],
    },
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Topic :: Multimedia :: Video",
        "Topic :: Internet :: WWW/HTTP :: Dynamic Content",
    ],
    zip_safe=False,
)

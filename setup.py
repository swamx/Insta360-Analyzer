"""Setup script for Insta360-Analyzer."""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="insta360-analyzer",
    version="0.1.0",
    author="Claude Code",
    description="Local-first Insta360 video analyzer with checkpoint/resume capability",
    long_description=long_description,
    long_description_content_type="text/markdown",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "torch>=2.1.2",
        "torchvision>=0.16.2",
        "transformers>=4.36.2",
        "bitsandbytes>=0.41.3",
        "opencv-python>=4.8.1",
        "Pillow>=10.0.1",
        "numpy>=1.24.3",
        "h5py>=3.10.0",
        "pyyaml>=6.0.1",
        "pydantic>=2.4.2",
        "click>=8.1.7",
        "tqdm>=4.66.1",
        "python-dotenv>=1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "insta360-analyzer=src.main:main",
        ],
    },
)

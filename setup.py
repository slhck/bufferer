# Always prefer setuptools over distutils
from setuptools import setup

# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# read version string
with open(path.join(here, "bufferer", "__init__.py")) as version_file:
    version = eval(version_file.read().split(" = ")[1].strip())

# Get the long description from the README file
with open(path.join(here, "README.md"), encoding="utf-8") as f:
    long_description = f.read()

setup(
    name="bufferer",
    version=version,
    description="Insert fake buffering events into video files.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/slhck/bufferer",
    author="Werner Robitza",
    author_email="werner.robitza@gmail.com",
    license="MIT",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Multimedia :: Video",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
    ],
    python_requires="~=3.5",
    package_data={"": ["spinners/*"]},
    packages=["bufferer"],
    install_requires=["docopt"],
    entry_points={
        "console_scripts": [
            "bufferer=bufferer.__main__:main",
        ],
    },
)
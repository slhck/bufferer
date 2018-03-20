"""Setup Module
"""

# Always prefer setuptools over distutils
from setuptools import setup, find_packages
# To use a consistent encoding
from codecs import open
from os import path

here = path.abspath(path.dirname(__file__))

# Get the long description from the README file
with open(path.join(here, 'README.md'), encoding='utf-8') as f:
    long_description = f.read()

try:
    import pypandoc
    long_description = pypandoc.convert_text(long_description, 'rst', format='md')
except ImportError:
    print("pypandoc module not found, could not convert Markdown to RST")

import bufferer

setup(
    name='bufferer',
    version=bufferer.__version__,
    description='Insert fake buffering events into video files.',
    long_description=long_description,
    url='https://github.com/slhck/bufferer',
    author='Werner Robitza',
    author_email='werner.robitza@gmail.com',
    license='MIT',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Multimedia :: Video',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    package_data={
        '': ['spinners/*']
    },
    packages=['bufferer'],
    install_requires=['docopt'],
    entry_points={
        'console_scripts': [
            'bufferer=bufferer.__main__:main',
        ],
    },
)
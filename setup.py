#!/usr/bin/env python

from setuptools import setup, find_packages

long_description = """
Quickly download videos from twitch.tv.

Works simliarly to youtube-dl but downloads multiple VODs in parallel which
makes it faster.
"""

setup(
    name="twitch-dl",
    version="2.1.4",
    description="Twitch downloader",
    long_description=long_description.strip(),
    author="Ivan Habunek",
    author_email="ivan@habunek.com",
    url="https://github.com/ihabunek/twitch-dl/",
    project_urls={
        "Documentation": "https://twitch-dl.bezdomni.net/"
    },
    keywords="twitch vod video download",
    license="GPLv3",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Environment :: Console",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Programming Language :: Python :: 3",
    ],
    packages=find_packages(),
    python_requires=">=3.7",
    install_requires=[
        "m3u8>=1.0.0,<4.0.0",
        "httpx>=0.17.0,<1.0.0",
    ],
    entry_points={
        "console_scripts": [
            "twitch-dl=twitchdl.console:main",
        ],
    }
)

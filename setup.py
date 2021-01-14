#!/usr/bin/env python

from setuptools import setup, find_packages

long_description = """
Quickly download videos from twitch.tv.

Works simliarly to youtube-dl but downloads multiple VODs in parallel which
makes it faster.
"""

setup(
    name='twitch-dl',
    version='1.14.0',
    description='Twitch downloader',
    long_description=long_description.strip(),
    author='Ivan Habunek',
    author_email='ivan@habunek.com',
    url='https://github.com/ihabunek/twitch-dl/',
    keywords='twitch vod video download',
    license='GPLv3',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    packages=find_packages(),
    python_requires='>=3.5',
    install_requires=[
        "m3u8>=0.3.12,<0.4",
        "requests>=2.13,<3.0",
    ],
    entry_points={
        'console_scripts': [
            'twitch-dl=twitchdl.console:main',
        ],
    }
)

#!/usr/bin/env python

from setuptools import setup


setup(
    name='twitch-dl',
    version='0.1.0',
    description='Twitch downloader',
    long_description="A simple script for downloading videos from Twitch",
    author='Ivan Habunek',
    author_email='ivan@habunek.com',
    url='https://github.com/ihabunek/twitch-dl/',
    keywords='twitch vod video download',
    license='GPLv3',
    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
    ],
    packages=['twitchdl'],
    install_requires=[
        "requests>=2.13,<3.0",
    ],
    entry_points={
        'console_scripts': [
            'twitch-dl=twitchdl.console:main',
        ],
    }
)

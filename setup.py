from setuptools import setup, find_packages

setup(
    name="scrapeer",
    version="1.0.1",
    description="Essential Python library that scrapes HTTP(S) and UDP trackers for torrent information.",
    author="tboy1337",
    author_email="obywhuie@anonaddy.com",
    url="https://github.com/tboy1337/scrapeer-py",
    download_url="https://github.com/tboy1337/scrapeer-py/releases/latest",
    license="MIT",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.6",
    keywords=[
        "torrent",
        "torrents",
        "scraper",
        "scrapeer",
        "torrent-scraper",
        "torrent-scraping"
    ],
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
)

from setuptools import setup, find_packages

setup(
    name="scrapeer-py",
    version="1.0.0",
    description="Essential Python library that scrapes HTTP(S) and UDP trackers for torrent information.",
    author="Python Port of TorrentPier's Scrapeer",
    author_email="tboy1337@users.noreply.github.com",
    url="https://github.com/tboy1337/scrapeer-py",
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

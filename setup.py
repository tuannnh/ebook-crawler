from setuptools import setup, find_packages

setup(
    name="ebook-crawler",
    version="1.0",
    packages=find_packages(),
    py_modules=["settings"],
    entry_points={"scrapy": ["settings = settings"]},
)

from setuptools import setup, find_packages


setup(
    name="cwfriend",
    version="0.0.1",
    author="bsmt",
    author_email="bsmt@krax.in",
    description="higher level API for ChipWhisperer",
    packages=find_packages(),
    install_requires=["plotly>=4.9.0",
                      "pandas>=1.1.0"],
)
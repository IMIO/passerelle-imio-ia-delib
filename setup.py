from setuptools import find_packages
from setuptools import setup

version = "1.0.5"

setup(
    name="passerelle-imio-ia-delib",
    version=version,
    author="iMio",
    author_email="support-ts@imio.be",
    packages=find_packages(),
    include_package_data=True,
    classifiers=[
        "Environment :: Web Environment",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.7",
    ],
    url="https://github.com/IMIO/passerelle-imio-ia-delib",
    install_requires=[
        "django>=3.2, <3.3",
    ],
    zip_safe=False,
)

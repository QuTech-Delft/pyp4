import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setuptools.setup(
    name="pyp4",
    version="0.0.0",
    description="Run P4 pipelines in Python",
    long_description=README,
    long_description_content_type="text/markdown",
    url="https://gitlab.tudelft.nl/qp4/pyp4",
    author="Wojciech Kozlowski",
    author_email="w.kozlowski@tudelft.nl",
    license="MIT",
    classifiers=[],
    packages=["pyp4"],
    include_package_data=True,
    install_requires=[],
    entry_points={},
)

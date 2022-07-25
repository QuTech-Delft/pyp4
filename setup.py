import pathlib
import setuptools

# The directory containing this file
HERE = pathlib.Path(__file__).parent

# The text of the README file
README = (HERE / "README.md").read_text()

# This call to setup() does all the work
setuptools.setup(
    name="pyp4",
    version="0.1.0",
    author="Wojciech Kozlowski",
    author_email="w.kozlowski@tudelft.nl",
    packages=["pyp4", "pyp4.processors"],
    url="https://gitlab.tudelft.nl/qp4/pyp4",
    license="Apache2.0",
    description="Run P4 pipelines in Python",
    long_description=README,
    long_description_content_type="text/markdown",
    install_requires=[],
)

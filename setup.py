from setuptools import setup, find_packages

setup(
    name='ushmm',
    version='0.0.2',  # Start with a small number and increase it with every change you make
    author='W.J.B. Mattingly',
    description='A suite of tools for working with data at the United States Holocaust Memorial Museum',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',  # This is important to render the README as markdown
    url='https://github.com/yourusername/your_package_name',  # Use the URL to the github repo if available
    packages=find_packages(),  # find_packages() is used to automatically find all packages and subpackages
    classifiers=[
        'Topic :: Software Development :: Build Tools',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.10',
        'Operating System :: Microsoft :: Windows',
    ],
    install_requires=[
        'pdf2image',
        'Pillow',
        'pytesseract',
        'unidecode',
        'opencv-python',
    ],
    python_requires='>=3.7',  # Your project's Python version compatibility
    keywords='pdf image testimonies',  # Descriptive meta-data
)


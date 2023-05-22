from setuptools import setup, find_packages

setup(
    name='aish',
    version='0.1.1',
    packages=find_packages(),
    install_requires=[
        'rich',
        'flask',
        'requests',
        'argparse'
    ],
    entry_points={
        'console_scripts': [
            'aish=aish.aish:main'
       ],
    },
    author='Toni Leino',
    author_email='toni@leino.net',
    description='A command-line application that interacts with the OpenAI ChatGPT API.',
    long_description=open('README.md').read(),
    long_description_content_type='text/markdown',
)

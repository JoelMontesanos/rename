from setuptools import setup

APP = ['app.py']  
DATA_FILES = ['op.icns']  
OPTIONS = {
    'argv_emulation': True,
    'iconfile': 'op.icns',  
    'packages': ['pdfplumber', 'xml', 'tkinter'],
}

setup(
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
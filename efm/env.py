import subprocess


class K2pdfoptNotFoundError(Exception):
    pass


k2pdf_install_instructions = """
To install k2pdfopt, go https://willus.org/k2pdfopt/download
Download the correct one and install globally.
"""


def ensure_k2pdfopt():
    proc = subprocess.run(
        ["command", "-v", "k2pdfopt"],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    if proc.returncode != 0:
        raise K2pdfoptNotFoundError(f"k2pdfopt not found. {k2pdf_install_instructions}")

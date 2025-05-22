"""
A package to collect information about films on letterboxd.com,
through the lists made on the website. (Note: does not use the
Letterboxd API, but web scraping techniques, so performance may
be slow.)
"""
from os.path import dirname, realpath

# make VALID_ATTRS available in the while module

# use the module root for absolute path
MODULE_ROOT = dirname(realpath(__file__))
VALID_ATTRS = []
with open(MODULE_ROOT+"/valid-lb-attrs.txt", "r", encoding="utf-8") as attr_file:
    VALID_ATTRS = attr_file.readlines()

VALID_ATTRS = [a.replace("\n", "") for a in VALID_ATTRS]

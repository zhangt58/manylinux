# Utility script to print the python tag + the abi tag for a Python
# See PEP 425 for exactly what these are, but an example would be:
#   cp27-cp27mu

from packaging.tags import sys_tags

# first tag is always the more specific tag
tag = next(sys_tags())
print(f"{tag.interpreter}-{tag.abi}")

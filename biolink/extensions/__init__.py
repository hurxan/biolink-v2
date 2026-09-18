import importlib
import os

extensionClasses = []

local_dir = os.path.dirname(__file__)
for name in os.listdir(local_dir):
    if os.path.isdir(os.path.join(local_dir, name)) and not name.startswith("_"):
        try:
            ext_package = importlib.import_module(__name__ + "." + name)
            extensionClasses.append(ext_package.extensionClass)
        except Exception as e:
            print("no valid extension package/folder:", name, e)

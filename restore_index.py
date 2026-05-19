import os
import shutil

# Path in the Recycle Bin
src = r"C:\$Recycle.Bin\S-1-5-21-3526881524-1725452648-2578559385-1001\$R6TGU3T.py"
dst = r"c:\Users\smile\OneDrive\Desktop\vtu project\index.py"

if os.path.exists(src):
    shutil.copy2(src, dst)
    print(f"Successfully restored: {dst}")
else:
    print(f"Source not found: {src}")
    # List all .py files in recycle bin for debugging
    bin_path = r"C:\$Recycle.Bin\S-1-5-21-3526881524-1725452648-2578559385-1001"
    print("\nAll .py files in Recycle Bin:")
    for f in os.listdir(bin_path):
        if f.endswith('.py'):
            print(f)

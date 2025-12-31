import os
import shutil
import subprocess

# Run PyInstaller
print("Building with PyInstaller...")
result = subprocess.run(['pyinstaller', 'main.spec'], capture_output=True, text=True)

if result.returncode != 0:
    print("PyInstaller failed:")
    print(result.stderr)
    exit(1)

print("PyInstaller completed successfully!")

# Copy additional files to the main dist directory
dist_dir = 'dist/Melodia'
files_to_copy = [
    'settings.json',
    'checkout.log',
    'invoice.html',
    'attmat.json',
    'matform.csv',
    'matform_content.csv',
    'matstor.csv',
    'matstor_content.csv',
    'saxeebi.csv',
    'saxeebi_content.csv'
]

folders_to_copy = [
    'ui',
    'invoices'
]

print(f"Copying files to {dist_dir}...")

# Copy individual files
for file in files_to_copy:
    if os.path.exists(file):
        dest_path = os.path.join(dist_dir, file)
        shutil.copy2(file, dest_path)
        print(f"✓ Copied {file}")
    else:
        print(f"⚠ Warning: {file} not found")

# Copy folders
for folder in folders_to_copy:
    if os.path.exists(folder):
        dest_folder = os.path.join(dist_dir, folder)
        if os.path.exists(dest_folder):
            shutil.rmtree(dest_folder)
        shutil.copytree(folder, dest_folder)
        print(f"✓ Copied folder {folder}/")
    else:
        print(f"⚠ Warning: folder {folder}/ not found")

print("\n🎉 Build completed!")
print(f"Your executable and files are in: {dist_dir}/")
print(f"Main executable: {dist_dir}/main.exe")
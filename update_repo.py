import os
import hashlib
import bz2
import subprocess

def get_hash(filepath, hash_type='md5'):
    h = hashlib.new(hash_type)
    with open(filepath, 'rb') as f:
        for chunk in iter(lambda: f.read(65536), b''):
            h.update(chunk)
    return h.hexdigest()

def extract_control(deb_path):
    try:
        # List files inside the ar archive
        files = subprocess.check_output(['ar', 't', deb_path]).decode('utf-8').splitlines()
        control_tar = [f for f in files if f.startswith('control.tar')][0]
        
        # Extract the control tarball using ar
        subprocess.run(['ar', 'x', deb_path, control_tar], check=True)
        
        # Parse using Python's tarfile module
        import tarfile
        control_content = None
        with tarfile.open(control_tar, 'r:*') as tar:
            members = tar.getnames()
            control_member = [m for m in members if m.endswith('control') or m == 'control'][0]
            control_content = tar.extractfile(control_member).read().decode('utf-8')
            
        # Clean up the extracted tarball
        if os.path.exists(control_tar):
            os.remove(control_tar)
            
        return control_content
    except Exception as e:
        print(f"Error extracting {deb_path}: {e}")
        if 'control_tar' in locals() and os.path.exists(control_tar):
            os.remove(control_tar)
        return None

def main():
    deb_dir = 'debs'
    packages_content = []
    
    if not os.path.exists(deb_dir):
        os.makedirs(deb_dir)
        
    debs = sorted([f for f in os.listdir(deb_dir) if f.endswith('.deb')])
    for deb in debs:
        path = os.path.join(deb_dir, deb)
        control = extract_control(path)
        if control:
            control = control.strip()
            size = os.path.getsize(path)
            md5 = get_hash(path, 'md5')
            sha1 = get_hash(path, 'sha1')
            sha256 = get_hash(path, 'sha256')
            
            filename = f"debs/{deb}"
            
            deb_entry = f"{control}\nFilename: {filename}\nSize: {size}\nMD5sum: {md5}\nSHA1: {sha1}\nSHA256: {sha256}\n\n"
            packages_content.append(deb_entry)
            
    packages_str = "".join(packages_content)
    
    # Write Packages
    with open('Packages', 'w', encoding='utf-8') as f:
        f.write(packages_str)
        
    # Write Packages.bz2
    packages_bz2 = bz2.compress(packages_str.encode('utf-8'))
    with open('Packages.bz2', 'wb') as f:
        f.write(packages_bz2)
        
    # Calculate hashes for Release file (required for Sileo to detect updates)
    from datetime import datetime, timezone
    
    pkg_bytes = packages_str.encode('utf-8')
    pkg_md5 = hashlib.md5(pkg_bytes).hexdigest()
    pkg_sha256 = hashlib.sha256(pkg_bytes).hexdigest()
    pkg_size = len(pkg_bytes)
    
    bz2_md5 = hashlib.md5(packages_bz2).hexdigest()
    bz2_sha256 = hashlib.sha256(packages_bz2).hexdigest()
    bz2_size = len(packages_bz2)
    
    date_str = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    
    # Write Release with Date and hashes so Sileo detects updates
    release_str = (
        "Origin: YuLitePro Repo\n"
        "Label: YuLitePro\n"
        "Suite: stable\n"
        "Version: 1.0\n"
        "Codename: yulitepro\n"
        "Architectures: iphoneos-arm iphoneos-arm64e\n"
        "Components: main\n"
        "Description: YuLite Pro Repository\n"
        f"Date: {date_str}\n"
        "MD5Sum:\n"
        f" {pkg_md5} {pkg_size} Packages\n"
        f" {bz2_md5} {bz2_size} Packages.bz2\n"
        "SHA256:\n"
        f" {pkg_sha256} {pkg_size} Packages\n"
        f" {bz2_sha256} {bz2_size} Packages.bz2\n"
    )
    with open('Release', 'w', encoding='utf-8') as f:
        f.write(release_str)
        
    print(f"Updated repository successfully with {len(debs)} debs.")

if __name__ == '__main__':
    main()

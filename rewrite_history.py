import subprocess
import re

# We use a list to store the last version to avoid scope issues in some Python environments
if 'state' not in globals():
    globals()['state'] = {'last_version': None}

def get_version(ts):
    if ts < 1771632000: return "0.1.0"
    if ts < 1771718400: return "0.5.0"
    if ts < 1772064000: return "0.8.0"
    if ts < 1773792000: return "1.0.0"
    return "2.0.0"

ts_bytes = commit.author_date.split(b' ')[0]
ts = int(ts_bytes)
version = get_version(ts).encode()

target_files = [b'build.sh', b'debian/control', b'debian/changelog']
changed_files = {change.filename for change in commit.file_changes}

# 1. Modify files that are already in file_changes
for change in commit.file_changes:
    if change.filename in target_files:
        try:
            content = subprocess.check_output(['git', 'cat-file', '-p', change.blob_id.decode()])
            new_content = content
            if change.filename == b'build.sh':
                new_content = re.sub(rb'VERSION=[0-9.]+', b'VERSION=' + version, content)
            elif change.filename == b'debian/control':
                new_content = re.sub(rb'Version: [0-9.]+', b'Version: ' + version, content)
            elif change.filename == b'debian/changelog':
                new_content = re.sub(rb'^(\w+) \([0-9.]+\)', rb'\1 (' + version + b')', content)
            
            if new_content != content:
                p = subprocess.Popen(['git', 'hash-object', '-w', '--stdin'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                stdout, _ = p.communicate(input=new_content)
                change.blob_id = stdout.strip()
        except Exception:
            pass

# 2. If version changed since last commit, check other target files that were NOT in file_changes
if version != globals()['state']['last_version']:
    globals()['state']['last_version'] = version
    for filename in target_files:
        if filename not in changed_files:
            try:
                # Check if the file exists in the original commit
                # We use rev-parse to get the blob_id
                res = subprocess.run(['git', 'rev-parse', '--verify', commit.original_id.decode() + ':' + filename.decode()], 
                                     capture_output=True)
                if res.returncode == 0:
                    blob_id = res.stdout.strip()
                    content = subprocess.check_output(['git', 'cat-file', '-p', blob_id.decode()])
                    
                    new_content = content
                    if filename == b'build.sh':
                        new_content = re.sub(rb'VERSION=[0-9.]+', b'VERSION=' + version, content)
                    elif filename == b'debian/control':
                        new_content = re.sub(rb'Version: [0-9.]+', b'Version: ' + version, content)
                    elif filename == b'debian/changelog':
                        new_content = re.sub(rb'^(\w+) \([0-9.]+\)', rb'\1 (' + version + b')', content)
                    
                    if new_content != content:
                        p = subprocess.Popen(['git', 'hash-object', '-w', '--stdin'], stdin=subprocess.PIPE, stdout=subprocess.PIPE)
                        stdout, _ = p.communicate(input=new_content)
                        new_blob_id = stdout.strip()
                        
                        # Get mode
                        mode_res = subprocess.run(['git', 'ls-tree', commit.original_id.decode(), filename.decode()], capture_output=True)
                        mode = mode_res.stdout.split()[0]
                        
                        # Add a new FileChange to force the update in this commit
                        commit.file_changes.append(FileChange(b'M', filename, new_blob_id, mode))
            except Exception:
                pass

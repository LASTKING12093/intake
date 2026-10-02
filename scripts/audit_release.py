"""Fail closed on local build-path leakage, private key material and token patterns.

Complements Gitleaks and human review; never prints matched values.
Examines Git's index, bundled files, ZIP members and frozen Python code.
"""
import hashlib
import json
import marshal
import os
from pathlib import Path
import re
import socket
import subprocess
import types
import zipfile
from PyInstaller.archive.readers import CArchiveReader

ROOT = Path(__file__).resolve().parents[1]
findings = []
count = 0
code_count = 0
needles = set()
for value in (str(ROOT), str(Path.home()), os.environ.get('USERPROFILE', ''), os.environ.get('AUDIT_PRIVATE_ROOT', '')):
    if len(value) > 5:
        for variant in (value, value.replace('\\', '/'), value.replace('\\', '\\\\')):
            for encoding in ('utf-8', 'utf-16-le'):
                needles.add(variant.lower().encode(encoding))
hostname = socket.gethostname()
if len(hostname) >= 8:
    needles.add(hostname.lower().encode())
patterns = {
    'private-key-material': re.compile(rb'-----BEGIN (?:RSA |EC |OPENSSH |ENCRYPTED )?PRIVATE KEY-----\s+[A-Za-z0-9+/=\r\n]{80,}'),
    'github-token': re.compile(rb'\b(?:gh[pousr]_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{60,})\b'),
    'slack-token': re.compile(rb'\bxox[baprs]-[A-Za-z0-9-]{30,}\b'),
    'aws-access-key': re.compile(rb'\bAKIA[0-9A-Z]{16}\b'),
}

def scan(name, data):
    global count
    count += 1
    lower = data.lower()
    if any(needle in lower for needle in needles):
        findings.append({'file': name, 'rule': 'private-build-context'})
    for rule, pattern in patterns.items():
        if pattern.search(data):
            findings.append({'file': name, 'rule': rule})

def inspect_code(name, code):
    global code_count
    if not isinstance(code, types.CodeType):
        return
    code_count += 1
    scan(name, code.co_filename.encode())
    if re.match(r'^(?:[A-Za-z]:[\\/]|/(?:Users|home)/)', code.co_filename):
        findings.append({'file': name, 'rule': 'absolute-frozen-code-filename'})
    for const in code.co_consts:
        if isinstance(const, types.CodeType):
            inspect_code(name, const)
        elif isinstance(const, (str, bytes)):
            scan(name, const.encode('utf-8') if isinstance(const, str) else const)

indexed = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
for name in filter(None, indexed):
    data = subprocess.check_output(['git', 'show', ':' + name], cwd=ROOT)
    scan('index/' + name, data)
    if re.search(r'(?:^|/)(?:\.env(?:\..*)?|cookies\.txt|.*\.(?:pfx|p12|pem|key|sqlite3|log))$', name, re.I):
        findings.append({'file': name, 'rule': 'unexpected-private-file'})

dist = ROOT / 'dist/INTAKE'
if not (dist / 'INTAKE.exe').is_file():
    raise SystemExit('Build INTAKE before auditing release artifacts')
for path in dist.rglob('*'):
    if not path.is_file():
        continue
    name = 'dist/' + path.relative_to(dist).as_posix()
    scan(name, path.read_bytes())
    if 'qtwebengine' in name.lower():
        findings.append({'file': name, 'rule': 'unused-webengine-resource'})
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as archive:
            for member in archive.namelist():
                scan(name + '/' + member, archive.read(member))
    if path.name == 'INTAKE.exe':
        archive = CArchiveReader(str(path))
        for member, entry in archive.toc.items():
            payload = archive.extract(member)
            scan(name + '/' + member, payload)
            if entry[-1] in ('s', 'm', 'M'):
                inspect_code(member, marshal.loads(payload))
            elif entry[-1] == 'z':
                pyz = archive.open_embedded_archive(member)
                for module in pyz.toc:
                    inspect_code(module, pyz.extract(module))
for path in (ROOT / 'release').glob('*'):
    if path.is_file():
        scan('release/' + path.name, path.read_bytes())
        if path.suffix == '.zip':
            with zipfile.ZipFile(path) as archive:
                expected = {'INTAKE/' + p.relative_to(dist).as_posix(): p for p in dist.rglob('*') if p.is_file()}
                members = {m.filename for m in archive.infolist() if not m.is_dir()}
                if members != set(expected):
                    findings.append({'file': path.name, 'rule': 'portable-file-list-mismatch'})
                for member in members & set(expected):
                    data = archive.read(member)
                    if hashlib.sha256(data).digest() != hashlib.sha256(expected[member].read_bytes()).digest():
                        findings.append({'file': member, 'rule': 'portable-content-mismatch'})
report = {'checks': count, 'frozen_code_objects': code_count, 'findings': findings,
          'source_files': len(list(filter(None, indexed)))}
target = ROOT / '.test-data/release-audit.json'
target.parent.mkdir(parents=True, exist_ok=True)
target.write_text(json.dumps(report, indent=2), 'utf-8')
print(json.dumps(report, indent=2))
raise SystemExit(bool(findings))

"""Export an allowlist of source files; never export workstation state or Git history."""
import argparse
from pathlib import Path
import re
import zipfile

ROOT=Path(__file__).resolve().parents[1]
FIXED=['README.md','LICENSE','SECURITY.md','CONTRIBUTING.md','pyproject.toml','.gitignore','launch.py']
PATTERNS=['aidev/**/*.py','aidev/scripts/*.ps1','scripts/*.py','scripts/*.ps1','tests/*.py','docs/*.md','docs/images/*.png','.github/workflows/*.yml']
SENSITIVE=[r'(?i)[A-Z]:[\\/]Users[\\/](?!Public\b)[^\s"\x27]+',
           r'\bgh[pousr]_[A-Za-z0-9]{20,}\b',r'\bgithub_pat_[A-Za-z0-9_]{20,}\b',
           r'\bsk-(?:proj-|ant-)?[A-Za-z0-9_-]{24,}\b',r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----']


def files():
    selected={ROOT/name for name in FIXED if (ROOT/name).is_file()}
    for pattern in PATTERNS:selected.update(ROOT.glob(pattern))
    return sorted(path for path in selected if path.is_file() and not path.is_symlink() and '__pycache__' not in path.parts)


def check(paths):
    issues=[]
    for path in paths:
        content=path.read_text('utf-8',errors='ignore')
        for expression in SENSITIVE:
            if re.search(expression,content):issues.append(str(path.relative_to(ROOT)))
    if issues:raise RuntimeError('Potential private data in: '+', '.join(sorted(set(issues))))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('output',type=Path)
    args=parser.parse_args()
    selected=files();check(selected)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(args.output,'w',zipfile.ZIP_DEFLATED) as archive:
        for path in selected:archive.write(path,'ai-dev-stream-deck/'+path.relative_to(ROOT).as_posix())
    print(f'Exported {len(selected)} source files. No local inventory, profile archive, missions, credentials, or Git history included.')


if __name__=='__main__':main()

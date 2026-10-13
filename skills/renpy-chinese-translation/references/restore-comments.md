# Restore Corrupted Comments from Git

If comment lines have been accidentally modified (Chinese characters in `#` lines), restore them from the previous git commit:

```python
import subprocess

orig = subprocess.check_output(['git', 'show', 'HEAD~1:<filepath>']).decode('utf-8')
orig_lines = orig.split('\n')

with open('<filepath>') as f:
    curr = f.read().split('\n')

restored = 0
for i in range(min(len(orig_lines), len(curr))):
    if orig_lines[i].lstrip().startswith('#') and orig_lines[i] != curr[i]:
        curr[i] = orig_lines[i]
        restored += 1

with open('<filepath>', 'w') as f:
    f.write('\n'.join(curr))

print(f"Restored {restored} comment lines")
```

This works because the file structure (line count and order) is identical between the original and translated versions — only the content of translated lines changes.

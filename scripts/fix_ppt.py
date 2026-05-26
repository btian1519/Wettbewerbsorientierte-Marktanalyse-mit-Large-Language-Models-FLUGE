path = r'c:\AAA_RWTH\Wettbewerbsorientierte Marktanalyse mit Large Language Models-FLUGE\generate_ppt.py'
with open(path, encoding='utf-8') as f:
    src = f.read()

# Fix all remaining bad patterns from the original source
fixes = {
    '作用：确定【为什么这个市场值得分析】"]),"}': '作用：确定【为什么这个市场值得分析】"]),',
}
for bad, good in fixes.items():
    src = src.replace(bad, good)

with open(path, 'w', encoding='utf-8') as f:
    f.write(src)

# Verify syntax
import py_compile, sys
try:
    py_compile.compile(path, doraise=True)
    print('Syntax OK')
except py_compile.PyCompileError as e:
    print('Error:', e)

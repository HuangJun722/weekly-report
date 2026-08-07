"""行内测试 runner：无 pytest 环境下跑单个测试文件。"""
import importlib.util
import inspect
import pathlib
import sys
import tempfile
import traceback


def run_tests(path):
    mod_name = 't' + pathlib.Path(path).stem
    spec = importlib.util.spec_from_file_location(mod_name, path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = mod
    spec.loader.exec_module(mod)
    tests = [
        getattr(mod, n) for n in dir(mod)
        if n.startswith('test_') and callable(getattr(mod, n))
    ]
    passed = failed = 0
    for t in tests:
        try:
            sig = inspect.signature(t)
            needs = [p for p in sig.parameters if sig.parameters[p].default is inspect.Parameter.empty]
            if needs:
                if 'tmp_path' in needs:
                    with tempfile.TemporaryDirectory() as td:
                        t(pathlib.Path(td))
                else:
                    t(*[None] * len(needs))
            else:
                t()
            passed += 1
            print('  PASS', t.__name__)
        except Exception:
            failed += 1
            print('  FAIL', t.__name__)
            traceback.print_exc()
    print(f'== {path}: {passed} passed, {failed} failed')
    return failed


if __name__ == '__main__':
    total = 0
    for p in sys.argv[1:]:
        total += run_tests(p)
    print('TOTAL FAIL', total)
    sys.exit(1 if total else 0)

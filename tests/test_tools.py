import asyncio
import tempfile
import unittest
from pathlib import Path

from tools.builtin_tools import CalculatorTool, ReadFileTool, WriteFileTool


class ToolTests(unittest.TestCase):
    def test_calculator(self):
        result = asyncio.run(CalculatorTool().execute(expression="2 * (3 + 4)"))
        self.assertTrue(result.success)
        self.assertEqual(result.output, 14)

    def test_file_tools_are_sandboxed(self):
        with tempfile.TemporaryDirectory() as tmp:
            import os
            old = os.environ.get("ASHU_FILES_ROOT")
            os.environ["ASHU_FILES_ROOT"] = tmp
            try:
                asyncio.run(WriteFileTool().execute(path="hello.txt", content="namaste"))
                result = asyncio.run(ReadFileTool().execute(path="hello.txt"))
                self.assertTrue(result.success)
                self.assertEqual(result.output, "namaste")
                blocked = asyncio.run(ReadFileTool().execute(path="../outside.txt"))
                self.assertFalse(blocked.success)
            finally:
                if old is None:
                    os.environ.pop("ASHU_FILES_ROOT", None)
                else:
                    os.environ["ASHU_FILES_ROOT"] = old


if __name__ == "__main__":
    unittest.main()

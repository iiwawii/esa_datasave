import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from esa_export import DEFAULT_ADDRESS, check_connection, csv_payload, export_trace, output_path


PAYLOAD = b"Model:,E4407B\r\n,Trace 1\r\nHz,dBm\r\n0.000,-80.00\r\n"
SIZE = str(len(PAYLOAD)).encode()
BLOCK = b"#" + str(len(SIZE)).encode() + SIZE + PAYLOAD + b"\n"


class ExportTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.folder = Path(directory.name).resolve()
        self.target = self.folder / "实验 1.csv"

        factory = MagicMock()
        patcher = patch("esa_export.pyvisa.ResourceManager", factory)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.manager = factory.return_value.__enter__.return_value
        self.session = self.manager.open_resource.return_value
        self.instrument = self.session.__enter__.return_value
        self.instrument.query.side_effect = lambda command: {
            "*IDN?": "Agilent Technologies,E4407B,123,A.14.06\n",
            "*OPC?": "1",
            ":SYST:ERR?": '+0,"No error"',
        }[command]
        self.instrument.read_raw.return_value = BLOCK
        self.report = MagicMock()

    def test_output_path_accepts_unicode_and_optional_extension(self):
        self.assertEqual(output_path(str(self.folder), "实验 1.CSV"), self.target)
        for invalid in ("", "..", "NUL", "COM1.trace", "bad/name", "name..csv"):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                output_path(str(self.folder), invalid)

    def test_connection_rejects_other_model_and_releases_session(self):
        self.instrument.query.side_effect = None
        self.instrument.query.return_value = "Agilent Technologies,E4402B,123,A.14.06"
        with self.assertRaisesRegex(ValueError, "E4402B"):
            check_connection(DEFAULT_ADDRESS)
        self.session.__exit__.assert_called_once()

    def test_export_keeps_instrument_bytes_and_uses_matching_remote_path(self):
        remote_path = export_trace(DEFAULT_ADDRESS, self.target, self.report)
        self.assertRegex(remote_path, r"^C:\\[0-9A-F]{8}\.CSV$")
        self.assertEqual(self.target.read_bytes(), PAYLOAD)
        self.assertEqual(list(self.folder.iterdir()), [self.target])
        self.assertEqual(
            [(call[0], call.args) for call in self.instrument.method_calls],
            [
                ("query", ("*IDN?",)),
                ("write", (f":MMEM:STOR:TRAC TRACE1,'{remote_path}'",)),
                ("query", ("*OPC?",)),
                ("query", (":SYST:ERR?",)),
                ("write", (f":MMEMory:DATA? '{remote_path}'",)),
                ("read_raw", ()),
            ],
        )
        self.session.__exit__.assert_called_once()

    def test_instrument_error_blocks_readback_and_leaves_no_local_file(self):
        self.instrument.query.side_effect = ["Agilent,E4407B,123,A.14.06", "1", '-250,"Mass storage error"']
        with self.assertRaisesRegex(ValueError, "Mass storage error"):
            export_trace(DEFAULT_ADDRESS, self.target, self.report)
        self.instrument.read_raw.assert_not_called()
        self.assertEqual(list(self.folder.iterdir()), [])
        self.session.__exit__.assert_called_once()

    def test_truncated_response_leaves_no_local_file(self):
        self.instrument.read_raw.return_value = BLOCK[:-3]
        with self.assertRaises(ValueError):
            export_trace(DEFAULT_ADDRESS, self.target, self.report)
        self.assertEqual(list(self.folder.iterdir()), [])

    def test_existing_file_is_preserved(self):
        self.target.write_bytes(b"existing")
        with self.assertRaises(FileExistsError):
            export_trace(DEFAULT_ADDRESS, self.target, self.report)
        self.assertEqual(self.target.read_bytes(), b"existing")
        self.manager.open_resource.assert_not_called()

    def test_file_created_during_transfer_is_also_preserved(self):
        def read():
            self.target.write_bytes(b"created elsewhere")
            return BLOCK

        self.instrument.read_raw.side_effect = read
        with self.assertRaises(FileExistsError):
            export_trace(DEFAULT_ADDRESS, self.target, self.report)
        self.assertEqual(self.target.read_bytes(), b"created elsewhere")
        self.assertEqual(list(self.folder.iterdir()), [self.target])

    def test_invalid_and_truncated_block_headers(self):
        for reply in (b"", b"#", b"#0abc", b"#91", b"#2ab", b"#19abc", b"#13abcgarbage"):
            with self.subTest(reply=reply), self.assertRaises(ValueError):
                csv_payload(reply)


if __name__ == "__main__":
    unittest.main()
"""E4407B communication and CSV export, independent of the GUI."""

import os
import re
from pathlib import Path
from secrets import token_hex
from tempfile import NamedTemporaryFile

import pyvisa


DEFAULT_ADDRESS = "GPIB0::18::INSTR"
TIMEOUT_MS = 20_000
INVALID_FILENAME = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
RESERVED_FILENAME = re.compile(r"CON|PRN|AUX|NUL|COM[1-9¹²³]|LPT[1-9¹²³]", re.I)


def output_path(directory, filename):
    folder = Path(directory)
    if not directory or not folder.is_dir():
        raise ValueError("请选择一个已存在的保存目录。")
    filename = filename.strip()
    if filename.lower().endswith(".csv"):
        filename = filename[:-4]
    if (
        not filename
        or filename.endswith((".", " "))
        or INVALID_FILENAME.search(filename)
        or RESERVED_FILENAME.fullmatch(filename.split(".")[0].rstrip())
    ):
        raise ValueError("请输入有效的 Windows 文件名。")
    return folder.resolve() / f"{filename}.csv"


def instrument_id(instrument):
    instrument.timeout = TIMEOUT_MS
    identity = instrument.query("*IDN?").strip()
    fields = identity.split(",")
    if len(fields) < 2 or fields[1].strip().upper() != "E4407B":
        raise ValueError(f"设备型号应为 E4407B。仪器返回：{identity or '空响应'}")
    return identity


def check_connection(address):
    with pyvisa.ResourceManager() as manager:
        with manager.open_resource(address) as instrument:
            return instrument_id(instrument)


def csv_payload(reply):
    """Extract the original file from the IEEE 488.2 definite-length block."""
    if len(reply) < 2 or reply[:1] != b"#" or reply[1:2] not in b"123456789":
        raise ValueError("仪器未返回有效的文件传输头。")
    header_end = 2 + int(reply[1:2])
    size_field = reply[2:header_end]
    if len(reply) < header_end or not size_field.isdigit():
        raise ValueError("仪器返回的文件长度字段无效。")
    end = header_end + int(size_field)
    if end == header_end or end > len(reply) or reply[end:] not in (b"", b"\n", b"\r\n"):
        raise ValueError("仪器返回的文件长度与实际数据不符。")
    return reply[header_end:end]


def check_instrument_operation(instrument):
    if instrument.query("*OPC?").strip() != "1":
        raise ValueError("仪器未确认操作完成。")
    response = instrument.query(":SYST:ERR?").strip()
    code, _, _ = response.partition(",")
    if code.strip() not in {"0", "+0"}:
        raise ValueError(f"仪器错误队列返回：{response or '空响应'}")


def publish_csv(pending, target, payload):
    with pending.open("wb") as file:
        file.write(payload)
        file.flush()
        os.fsync(file.fileno())
    if os.name == "nt":
        pending.rename(target)  # Windows rename fails if the destination exists.
    else:
        os.link(pending, target)


def export_trace(address, target, report):
    """Publish a complete local CSV, then return any instrument cleanup warning."""
    if target.exists():
        raise FileExistsError(f"本地文件已存在，请更换文件名：{target.name}")
    pending = None
    remote_path = None
    local_saved = False
    warning = None
    try:
        with NamedTemporaryFile(dir=target.parent, prefix=".esa-", suffix=".tmp", delete=False) as file:
            pending = Path(file.name)
        report("正在连接 E4407B…")
        with pyvisa.ResourceManager() as manager, manager.open_resource(address) as instrument:
            instrument_id(instrument)
            # ESA instrument names are limited to eight letters or digits.
            remote_path = f"C:\\{token_hex(4).upper()}.CSV"
            report(f"正在将 TRACE1 保存到仪器 {remote_path}…")
            instrument.write(f":MMEM:STOR:TRAC TRACE1,'{remote_path}'")
            check_instrument_operation(instrument)
            report("正在读回仪器文件…")
            instrument.write(f":MMEMory:DATA? '{remote_path}'")
            payload = csv_payload(instrument.read_raw())
            report("正在写入本地 CSV…")
            publish_csv(pending, target, payload)
            local_saved = True

            report("本地 CSV 已保存，正在清理仪器端临时文件…")
            try:
                instrument.write(f":MMEM:DEL '{remote_path}'")
                check_instrument_operation(instrument)
            except Exception as error:
                warning = f"未能确认仪器端临时文件已删除：{remote_path}\n{error}"
    except Exception as error:
        if local_saved:
            release_warning = f"关闭仪器连接时发生错误：{error}"
            warning = f"{warning}\n{release_warning}" if warning else release_warning
        elif remote_path:
            raise RuntimeError(f"{error}\n仪器端可能保留临时文件：{remote_path}") from error
        else:
            raise
    finally:
        if pending is not None:
            pending.unlink(missing_ok=True)
    return warning

# esa_datasave

用于 Agilent ESA E4407B 频谱仪的 Windows 数据导出工具。先在仪器面板上设置频率范围、扫描点数等参数，再通过电脑端界面将当前 `TRACE1` 扫描迹线保存为本地 CSV。

## 快速开始

1. 连接电脑与 E4407B，安装可用的 VISA 后端。使用 Keysight IO Libraries Suite 时，可在 Connection Expert 中检查仪器是否被识别。安装入口见 [VISA 后端下载说明](VISA%E5%90%8E%E7%AB%AF/%E4%B8%8B%E8%BD%BD%E8%AF%B4%E6%98%8E.txt)。
2. 确认仪器的 VISA 资源地址为 `GPIB0::18::INSTR`。当前程序使用固定地址。如果实际地址不同，请修改 `esa_datasave.py` 中的 `visa_address_esa`，再从源码运行。
3. 在频谱仪面板上设定所需的频率范围和扫描点数，确认待导出的数据在 `TRACE1`。
4. 运行 [Windows 可执行文件](dist/esa_datasave.exe)。在界面中填入一个已有且可写的本地目录，再输入文件名，省略 `.csv` 后缀，点击 **执行**。

例如，目录填 `D:\ESA_Data`，文件名填 `test1`，导出结果为 `D:\ESA_Data\test1.csv`。请使用新的文件名，以免覆盖本地同名文件。

## 从源码运行

准备带 Tkinter 的 Python 环境和可用的 VISA 后端，在仓库根目录运行：

```powershell
python -m pip install pyvisa
python esa_datasave.py
```

## 导出内容

程序通过 VISA 连接仪器，发送 `*IDN?` 并在控制台打印仪器响应，随后让仪器将 `TRACE1` 写入内部的 `C:\<文件名>.csv`。程序读回该文件并写入本地目录，仪器端文件会保留。

[示例 CSV](demo_data.csv) 展示了文件结构，包括中心频率、频宽、RBW、VBW 和扫描点数等测量信息，以及以 Hz 和 dBm 为单位的迹线数据。导入分析软件时，从 `Hz,dBm` 表头定位数据区。

## 问题反馈

连接失败时，先在 Connection Expert 中核对仪器识别状态和资源地址。保存失败时，检查本地目录是否存在、是否可写，并查看程序控制台中的报错。

提交 [Issue](https://github.com/iiwawii/esa_datasave/issues) 时，请附上仪器型号、连接方式、Windows 和 VISA 版本、运行方式以及完整报错。用导出数据做实验记录时，建议同时记录所用仓库提交和仪器设置。

## 许可证

本仓库目前未声明软件许可证。如需修改后分发或将代码纳入其他项目，请先联系维护者确认授权。

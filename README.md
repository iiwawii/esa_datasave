# esa_datasave

在 Windows 上导出 Agilent ESA E4407B 频谱仪的 `TRACE1`。扫描参数在仪器面板上设置，程序将仪器生成的迹线 CSV 保存到电脑。

## Windows 快速开始

1. 连接 E4407B 并安装可用的 VISA 后端。使用 Keysight IO Libraries Suite 时，可在 Connection Expert 中核对仪器地址。安装入口见 [VISA 后端下载说明](VISA%E5%90%8E%E7%AB%AF/%E4%B8%8B%E8%BD%BD%E8%AF%B4%E6%98%8E.txt)。
2. 下载并运行 [esa_datasave.exe（Windows x64）](dist/esa_datasave.exe)。

也可以使用带 Tkinter 的 Python，在仓库根目录从源码启动：

```powershell
python -m pip install pyvisa
python esa_datasave.py
```

## 导出一次扫描迹线

1. 在 E4407B 的频谱分析模式下设置频率范围、扫描点数等参数，确认待导出的数据在 `TRACE1`。
2. 在程序中输入 VISA 资源地址，默认是 `GPIB0::18::INSTR`。点击 **测试连接** 可查看仪器返回的身份信息。每次导出也会核对仪器型号。
3. 选择已存在的保存目录，输入本地文件名，点击 **导出 TRACE1**。同名文件已存在时，请换一个文件名。
4. 导出完成后，界面会显示本地 CSV 路径和仪器端清理状态。点击 **打开保存目录** 可查看结果。

导出时，程序使用仪器支持的八位临时文件名保存 `TRACE1`，确认写入完成并检查仪器错误队列，再读取文件。程序移除传输头后直接保存 CSV 内容，保留仪器返回的测量参数、列名和数据。电脑端成功保存后，程序只删除本次生成的仪器端临时文件。如果导出报错或无法确认清理完成，界面会提示可能残留的路径，可在仪器端核对。

[示例 CSV](demo_data.csv) 可用于了解文件结构。仓库现有样例标为 `Trace 3`。导入分析软件时，可用列名行区分测量参数区和迹线数据区。

## Windows 打包与测试

如需自行打包，在 Windows 的仓库根目录运行：

```powershell
python -m pip install pyvisa pyinstaller
python -m PyInstaller --onefile --windowed --specpath .build --workpath .build --distpath out esa_datasave.py
```

可执行文件生成于 `out/esa_datasave.exe`。PyInstaller 会在 `.build/` 中生成临时的 `.spec` 和打包中间文件。

运行 `python -m unittest -v` 可用模拟仪器检查命令顺序、传输长度、失败处理、本地文件保护和仪器端清理。此版本已验证 Windows 程序启动和模拟导出，E4407B 实机读写和自动清理待验证。

## 问题反馈

连接失败时，先核对 VISA 后端、资源地址和仪器型号。仪器写入失败时，请查看界面报告的错误，并检查仪器端存储。提交 [Issue](https://github.com/iiwawii/esa_datasave/issues) 时，请附上仓库提交、仪器型号和固件版本、连接方式、Windows 和 VISA 版本、运行方式以及完整报错。

## 许可证

本仓库目前未声明软件许可证。如需修改后分发或将代码纳入其他项目，请先联系维护者确认授权。

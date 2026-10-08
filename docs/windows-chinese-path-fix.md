# Windows 中文路径失败修复

> 适用版本：openlink v1.3.0+
> 验证时间：2026-10
> 平台：Windows 10 / AMD64

## 现象

在中文工作目录下执行删除等命令失败，回显：

```
G:\...>del /f "F:\...\深度学习论文\缺陷检测\机器视觉跑路.md"
The filename, directory name, or volume label syntax is incorrect.
```

或中文文件名显示为乱码。

## 根因

`backend/app/tools/exec_cmd.py` 在 Windows 上用 `cmd.exe /C <command>` 执行命令。cmd 按**控制台代码页**（中文 Windows 默认 GBK/936）解析命令行，而 Python 的 `asyncio.create_subprocess_exec` 以 UTF-8 编码字符串参数并走 Unicode API。中文路径的字节在 cmd 端被错误解码，导致路径解析失败。

两个看似可行的方案其实都无效：

- **命令前加 `chcp 65001`**：`chcp` 在 cmd 开始解析该命令行之后才执行，来不及改变已传入字节的解读方式。
- **直接把参数编码成 bytes 传入**：Windows 的 asyncio 会先用 `os.fsdecode`（UTF-8）解码参数，触发 `UnicodeDecodeError: 0xc9`。

## 修复

将命令写入一个 **UTF-8 编码的临时 `.bat`**（首行 `chcp 65001`），再执行该 bat。cmd 逐行读取 bat 时，第一行先切到 UTF-8 代码页，后续含中文的行即可被正确解析。

`backend/app/tools/exec_cmd.py`：

```python
def _write_temp_bat(cmd: str) -> str:
    import tempfile
    fd, path = tempfile.mkstemp(suffix=".bat", prefix="openlink_")
    os.close(fd)
    body = cmd.encode("utf-8", errors="replace")
    with open(path, "wb") as f:
        f.write(b"@echo off\r\nchcp 65001 >nul\r\n")
        f.write(body)
        f.write(b"\r\n")
    return path
```

执行分支（Windows 走 bat，其它平台仍用 shell）：

```python
bat_path = None
if sys.platform == "win32":
    comspec = os.environ.get("COMSPEC", "cmd.exe")
    shell, flag = comspec, "/C"
    bat_path = _write_temp_bat(cmd)
    cmd_arg = bat_path
else:
    shell, flag = "sh", "-c"
    cmd_arg = cmd
```

执行结束后在 `finally` 中清理临时 bat：

```python
finally:
    if bat_path is not None:
        try:
            os.remove(bat_path)
        except OSError:
            pass
```

## 关键点

- 编码必须三者一致：bat 内容 UTF-8、bat 首行 `chcp 65001`、输出解码 UTF-8。
- 早期尝试用 `mbcs`/`gbk` 写 bat（配合 `chcp 936`）反而导致乱码，说明运行时控制台实际处于 UTF-8；统一 UTF-8 才是稳定解。
- 回显中的中文文件名需正常显示，否则说明代码页仍未对齐。

## 验证

```cmd
dir "F:\...\深度学习论文\缺陷检测"
del /f "F:\...\深度学习论文\缺陷检测\某个文件.md"
```

中文应正常显示、删除成功。若报 `Could Not Find` 且中文正常，说明编码已修复，仅目标文件不存在。

## 涉及文件

| 文件 | 改动 |
|------|------|
| `backend/app/tools/exec_cmd.py` | 临时 bat 方案 |

修改后需重启后端服务。

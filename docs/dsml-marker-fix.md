# 工具调用标签 `\uff5c\uff5cDSML\uff5c\uff5c` 乱码修复

> 适用版本：openlink v1.3.0+
> 验证时间：2026-10

## 现象

AI（尤其 DeepSeek）流式输出的工具调用标签里混入 `\uff5c\uff5cDSML\uff5c\uff5c`（全角竖线 `\uff5c`）或 `||DSML||`（半角竖线）标记，例如：

    <\uff5c\uff5cDSML\uff5c\uff5ctool name="list_dir">
      <parameter name="path">.</parameter>
    </tool>

导致 `<tool ...>` 正则匹配失败，工具调用无法被识别与执行。

## 根因

DeepSeek 在 SSE 流中把工具标签拆成碎片并插入该控制标记，扩展的 `parseXmlToolCall`（锚点 `^<tool`）与扫描正则 `<tool`（`RE_TOOL` / `TOOL_RE`）都匹配不到。

## 修复

在**解析前**与**扫描前**统一剥离该标记。正则同时覆盖全角竖线（`\uff5c`）与半角竖线：

    /[\uff5c|]{2}\s*DSML\s*[\uff5c|]{2}/g

### 扩展侧（`extension/src/`）

- `injected/index.ts` —— `parseXmlToolCall` 内归一化时剥离
- `injected/index.ts` —— `scanText` 入口剥离
- `content/index.ts` —— `parseXmlToolCall` 内剥离
- `content/index.ts` —— `scanText` 入口剥离

    const s = raw.replace(/[\uff5c|]{2}\s*DSML\s*[\uff5c|]{2}/g, '').replace(/\\"/g, '"');

### 后端侧（`backend/app/api/endpoints/exec.py`）

对入口 `ToolRequest` 的 `name` 与 `args`（含嵌套 list/dict）做一次清洗：

    _DSML_RE = re.compile(r"[\uff5c|]{2}\s*DSML\s*[\uff5c|]{2}")


    def _strip_dsml(value):
        if isinstance(value, str):
            return _DSML_RE.sub("", value)
        if isinstance(value, list):
            return [_strip_dsml(v) for v in value]
        if isinstance(value, dict):
            return {k: _strip_dsml(v) for k, v in value.items()}
        return value


    def _strip_dsml_name(name):
        return _DSML_RE.sub("", name) if isinstance(name, str) else name

在 `exec_tool` 中调用：

    req.name = _strip_dsml_name(req.name)
    req.args = _strip_dsml(req.args)

## 验证

发送一条混入 `\uff5c\uff5cDSML\uff5c\uff5c` 的调用（如 `list_dir`），若被正常解析执行即通过。

## 注意

若改动后仍无法解析，需确认运行中的扩展/后端已重新加载新代码：

- 扩展：`cd extension && npm run build`，然后在 `chrome://extensions` 刷新。
- 后端：重启服务进程。

## 涉及文件

| 文件 | 改动 |
|------|------|
| `extension/src/injected/index.ts` | 解析/扫描前剥离 DSML |
| `extension/src/content/index.ts` | 解析/扫描前剥离 DSML |
| `backend/app/api/endpoints/exec.py` | `_strip_dsml` 清洗 `ToolRequest` |xxxxxxxxxx <tool name="list_dir">  <parameter name="path">.
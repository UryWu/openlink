# 工具错误响应被"系统提示"覆盖 —— commit `3564945` 复盘

> 主题：后端 `/exec` 返回错误时，错误信息没有按预期到达扩展端，被误显示成 `[系统提示] ...`
> Commit：[`3564945`](https://github.com/UryWu/openlink/commit/3564945) — `fix(backend): read_file 路径不存在时返回明确错误 + executor 错误响应不再被 reminder 覆盖`
> 影响范围：`backend/app/executor/executor.py`、`backend/app/tools/read_file.py`
> 修复者：UryWu
> 文档目的：把这次 bug 的**现象 → 根因 → 修复 → 教训**完整记录下来，供后续维护 / 教学使用

---

## 1. 现象

工具命令面板执行以下 XML：

```xml
<tool name="read_file">
  <parameter name="path">backend/app/core/executor.py</parameter>
</tool>
```

结果框显示的内容：

```
[read_file]
[系统提示] 请记住你是 openlink，一个交互式 CLI 工具，主要用于软件工程任务。
```

**用户的预期**：看到类似"文件不存在: backend/app/core/executor.py"的明确错误。

**实际**：错误信息完全消失，只剩一句不相关的"系统提示"。

---

## 2. 根因

要理解这个 bug，必须先看清工具调用从发出到显示的完整数据流。

### 2.1 三层数据模型

后端 / 扩展 / 前端之间流转的数据有三层：

```
┌─────────────────────────────┐
│ ToolResult (工具层内部)     │  backend/app/tools/read_file.py
│  ├─ status: "success"/"error"
│  ├─ output: str | None     │  ← 工具执行结果（成功时是文件内容）
│  └─ error:  str | None     │  ← 错误原因（成功时为 None）
└─────────────────────────────┘
            ↓ executor.py 包装
┌─────────────────────────────┐
│ ToolResponse (HTTP 响应)    │  backend/app/schemas/types.py
│  ├─ status                 │
│  ├─ output: str = ""       │  ← Pydantic 默认 "" 兜底 None
│  ├─ error:  str | None     │
│  └─ stopStream: bool       │
└─────────────────────────────┘
            ↓ JSON over HTTP
┌─────────────────────────────┐
│ 扩展端 executeToolCallRaw   │  extension/src/content/index.ts:213
│  return result.output        │
│      || result.error        │  ← 关键 fallback 链
│      || '[OpenLink] 空响应';
└─────────────────────────────┘
```

每一层都"看起来正确"，但**层与层之间的 fallback 顺序没对齐**。

### 2.2 错误数据流的逐层衰减

假设工具读取了不存在的文件：

| 层 | 字段 | 值 |
|---|---|---|
| `read_file.py` 抛 `FileNotFoundError` | `ToolResult.status` | `"error"` |
| | `ToolResult.output` | `None` |
| | `ToolResult.error` | (裸 `str(e)`，没带路径) |
| `executor.py:142-147` 构造 `ToolResponse` | `status` | `"error"` |
| | `output` | `""`（Pydantic 把 `None` 兜底成 `""`） |
| | `error` | `"[Errno 2] No such file or directory: '...'"` |
| `executor.py:149-153` 附加 `_REMINDER` | `output` | `"" + "\n\n[系统提示] ..."` |
| | `error` | `"[Errno 2] ..."` |
| `extension/src/content/index.ts:222` | `result.output \|\| result.error \|\| ...` | `"[系统提示] ..."`（**非空字符串**，直接返回） |

**问题一：`output = "" + 提示 ≠ ""`** —— JavaScript 的 `"" || "x"` 返回 `"x"`，但 `"\n\n[系统提示]..."` 是 truthy，所以 fallback 链根本不会走到 `error`。

**问题二：executor 把 reminder 拼到错误响应上** —— reminder 设计的初衷是"工具成功后提醒 AI 自己的身份"，但 executor 没区分 success / error，错误响应也被拼上。

**问题三：`read_file.py` 的错误信息没带路径** —— 即使错误能传出去，AI 看到的也只是 `"[Errno 2] No such file or directory: '...'"`，原始路径 `backend/app/core/executor.py` 和 sandbox 解析后的绝对路径都不在错误里，AI 无法自我纠正。

三个问题叠加 → 用户看到的是一段不相关提示，错误信息从工具到 UI 全程蒸发。

---

## 3. 修复

`3564945` 一次性修了这三个问题，diff 涵盖两个文件。

### 3.1 `backend/app/executor/executor.py`

**改动**：error 状态时跳过 reminder 注入。

```diff
-        if self._call_count % 20 == 0:
-            resp.output += "\n\n" + _build_init_prompt(self.config)
-        else:
-            resp.output += _REMINDER
+        # Skip on error: resp.output may be "" and resp.error carries the
+        # actual failure reason. Appending the reminder would make the
+        # extension display "[系统提示] ..." instead of the error.
+        if result.status != "error":
+            if self._call_count % 20 == 0:
+                resp.output += "\n\n" + _build_init_prompt(self.config)
+            else:
+                resp.output += _REMINDER
```

**为什么这样改而不是"把 error 也写进 output"**：保留 `status` / `output` / `error` 三字段的语义分离 —— `output` 是"工具结果"、 `error` 是"失败原因"，把错误塞进 `output` 会破坏 Pydantic schema 的预期消费方式。修源头（不污染 output）而不是修消费端。

### 3.2 `backend/app/tools/read_file.py`

**改动**：拆分 `OSError` 为具体异常，每条带原始路径 + sandbox 解析后的绝对路径。

```diff
-        except OSError as e:
-            return ToolResult(status="error", error=str(e))
+        except FileNotFoundError:
+            return ToolResult(
+                status="error",
+                error=f"文件不存在: {raw_path} (resolved: {abs_path})",
+            )
+        except IsADirectoryError:
+            return ToolResult(
+                status="error",
+                error=f"路径是目录而非文件: {raw_path}",
+            )
+        except PermissionError:
+            return ToolResult(
+                status="error",
+                error=f"无权限读取: {raw_path}",
+            )
+        except OSError as e:
+            return ToolResult(status="error", error=f"读取失败 {raw_path}: {e}")
```

**为什么这样写**：

- AI 看到 `文件不存在: backend/app/core/executor.py (resolved: G:\...\backend\backend\app\core\executor.py)` —— **原始路径**让它知道用户传的是什么（可能拼错），**resolved 路径**暴露 sandbox 解析后的结果（这次刚好暴露了 [commit `ce5b43f`](https://github.com/UryWu/openlink/commit/ce5b43f) 修的 root_dir 双重 backend bug，两个 bug 协作被一起发现）
- 拆分具体异常 → 错误信息更对症（"无权限" vs "不存在" 是完全不同的修复路径）
- 最后兜底 `except OSError` 防漏网（磁盘 I/O 错误、设备故障等罕见情况）

---

## 4. 验证

修复后再次执行同一个不存在的路径：

```bash
curl -X POST http://127.0.0.1:13999/exec \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"name":"read_file","args":{"path":"backend/app/core/executor.py"}}'
```

响应：

```json
{
  "status": "error",
  "output": "",
  "error": "文件不存在: backend/app/core/executor.py (resolved: G:\\Projects\\projects_ai\\openlink\\backend\\backend\\app\\core\\executor.py)",
  "stopStream": false
}
```

扩展端拿到后：
- `result.output` = `""`（空字符串是 falsy）
- `"" || result.error` → `"文件不存在: ..."`
- 用户在结果框看到这条消息

**注意**：`resolved` 路径里有 `backend\backend\app\...` 双重 backend —— 这不是 `3564945` 引入的，是 `ce5b43f` 单独修复的另一个 bug（`root_dir` 默认 `os.getcwd()` 在 backend/ 子目录下启动时被多算一层）。两次 commit 协作：本次 fix 让错误信息能传出来，错误信息**顺便**暴露了下游的 root_dir bug。

---

## 5. 教训（可推广的设计原则）

### 5.1 Pydantic `Optional[str]` + `str = ""` 是双刃

`ToolResponse.output: str = ""` 这个默认值的初衷是"成功的工具一定有 output"。但它把 `None` 静默兜底成 `""`，**让 `None` 和 `"成功但空字符串"` 在下游无法区分**。

经验：**当一个字段同时承担"成功结果"和"缺失值"两种语义时，要么分开（`output` + `is_empty` 标志位），要么显式拒绝 None（`output: str`，缺失时抛 ValidationError）**。

### 5.2 fallback 链要诚实

`result.output || result.error || '[OpenLink] 空响应'` 看似健壮（三个保底），实际**让"看似非空但语义为空"的内容**（空字符串 + 后置 reminder）混过了所有 fallback。

经验：**fallback 链的每一档都应该是真值**。当 `output = "" + reminder` 是非空字符串时，`||` 链的语义跟设计意图已经偏离了 —— 此时应该让上游产出明确的"空"标记，而不是依赖消费者去分辨。

### 5.3 装饰性附加（reminder / metadata）必须尊重 status

`executor.py` 的 `_REMINDER` 是为成功响应附加的身份提醒，但被无脑追加到所有响应上。**任何"对响应做装饰性追加"的代码都应该先问一句：这个响应的 status 是不是我该追加的场景？**

这次修法的本质：把无脑追加改成"只有 success 才追加"。

### 5.4 错误信息要带"自助修复线索"

`str(e)` 是最低质量的错误信息 —— 对开发者有用（知道系统调用 errno），对 AI / 终端用户没用（不知道是哪个文件、为什么失败）。

**错误信息的质量标准**：

| 维度 | 反例 (`str(e)`) | 正例 (本次修复后) |
|---|---|---|
| 是哪个资源？ | ❌ | ✅ `raw_path` |
| 实际访问到哪了？ | ❌ | ✅ `abs_path` |
| 失败类型？ | 半 (errno 数字) | ✅ `文件不存在 / 路径是目录 / 无权限` |
| 用户能怎么办？ | ❌ | ✅ 看路径就能修正 |

AI 工具调用场景下，错误信息本质上是给 AI 的"自助文档"，不是给开发者的调试日志。

### 5.5 跨层错误传递的"完整性测试"

单元测试 `read_file` 失败返回 `ToolResult(status="error", error="...")` 是过了的 —— 工具层行为正确。但**整条 HTTP 响应链路上错误信息能不能到达最终用户**，没人测过。

经验：**对错误响应做端到端测试**（从工具返回 → executor 包装 → JSON 序列化 → HTTP 响应 → 客户端解析 → UI 显示），每个环节断言 `error` 字段没被吞。这次 bug 的修复 PR 里应该加一条：

```python
def test_error_response_survives_full_chain():
    # 工具返回错误 → 后端 HTTP 响应 → 客户端应能拿到 error 字段
    resp = client.post("/exec", json={"name": "read_file", "args": {"path": "/nonexistent"}})
    assert resp.json()["status"] == "error"
    assert resp.json()["output"] == ""  # 关键：error 时 output 不被污染
    assert "文件不存在" in resp.json()["error"]
```

---

## 6. 后续行动清单

- [ ] 把上述端到端测试加进 `backend/tests/`
- [ ] 同样模式检查 `backend/app/tools/` 下其他 11 个工具（write_file / edit / list_dir / glob / grep / exec_cmd / web_fetch / question / skill / todo_write / invalid），是否都返回了带上下文的错误信息
- [ ] `executor.py` 的 reminder 设计可以提一个 type-level 约束：所有工具返回的 `ToolResult` 在 error 时 `output` 必须为 `None` 或 `""`（用 Pydantic validator 强制），防止以后又有工具返回奇怪的 error 响应被 reminder 污染

---

## 7. 相关 commit

- [`3564945`](https://github.com/UryWu/openlink/commit/3564945) — 本次复盘的 fix
- [`ce5b43f`](https://github.com/UryWu/openlink/commit/ce5b43f) — 修复 `root_dir` 双重 backend，让 `resolved` 路径最终正确（同期暴露）
- [`be3eb60`](https://github.com/UryWu/openlink/commit/be3eb60) — 清掉 `main.py` docstring 里过时的 Go 路径引用（同期清理）
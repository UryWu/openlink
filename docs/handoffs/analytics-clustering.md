# OpenLink Analytics 聚类功能开发交接文档 (Hand-off)

## 1. 项目背景
在 OpenLink 项目的 Analytics 页面 (`http://127.0.0.1:39527/app/analytics`) 中，需要增加一个“对话聚类”统计功能。该功能旨在将时间间隔较短的对话记录聚合成一个“会话组”，并统计每组的 Token 消耗和时间跨度，以便用户更直观地查看连续对话的成本分布。

## 2. 已完成的工作 (Backend)

### 2.1 Schema 更新
已在 `backend/app/schemas/types.py` 中完成了以下修改：
*   增加了 `ClusterStat` 模型，包含字段：`startTime`, `endTime`, `count`, `inputTokens`, `outputTokens`, `totalTokens`。
*   在 `StatsResponse` 模型中增加了 `clusters: list[ClusterStat] = []` 字段。

### 2.2 后端逻辑实现 (待验证/修复)
已在 `backend/app/api/endpoints/conversations.py` 中尝试实现聚类逻辑：
*   **接口参数**：`get_stats` 函数已增加 `clusterIntervalMinutes: int = 30` 参数。
*   **聚类算法**：
    1.  获取记录并按 `ts` 排序。
    2.  遍历记录，如果当前记录与上一条记录的时间差小于 `clusterIntervalMinutes * 60 * 1000` 毫秒，则归入同一组。
    3.  结算每组时计算总 Token 数和时间跨度。
*   **注意**：最后一次修改通过 Python 脚本执行，但前端调用时出现了 `422 Unprocessable Entity` 错误。这可能是因为 FastAPI 对 Query 参数的校验或前端传递参数的方式不匹配。**建议检查 `get_stats` 的签名是否正确使用了 `Query(...)` 或者确保前端传递的参数名与后端一致。**

## 3. 待完成的工作 (Frontend & Fix)

### 3.1 前端类型定义 (`frontend/src/types/index.ts`)
*   增加 `ClusterStat` 接口，与后端 Schema 保持一致。
*   更新 `StatsResponse` 接口，增加 `clusters: ClusterStat[]` 字段。

### 3.2 前端 API 调用 (`frontend/src/api/endpoints.ts`)
*   修改 `fetchStats` 函数，使其支持传递 `clusterIntervalMinutes` 参数。
    ```typescript
    export async function fetchStats(convId?: string, clusterIntervalMinutes?: number): Promise<StatsResponse> {
      const { data } = await api.get<StatsResponse>('/stats', {
        params: { 
          convId, 
          clusterIntervalMinutes 
        },
      })
      return data
    }
    ```

### 3.3 状态管理 (`frontend/src/stores/analytics.ts`)
*   增加 `clusterInterval` 响应式变量（默认 30）。
*   修改 `load` 方法，将 `clusterInterval` 传递给 `fetchStats`。

### 3.4 UI 展示 (`frontend/src/pages/Analytics.vue`)
*   **配置入口**：在页面顶部增加一个下拉框或输入框，允许用户选择聚类间隔（如：5min, 15min, 30min, 1h）。
*   **数据展示**：新增一个区域展示 `clusters` 数据。建议使用表格形式，列包括：
    *   时间跨度 (Start - End)
    *   对话条数 (Count)
    *   Input Tokens
    *   Output Tokens
    *   Total Tokens

## 4. 关键技术点与注意事项

1.  **时间戳单位**：后端使用的是毫秒级时间戳 (`ts * 1000`)，聚类计算时请注意单位转换。
2.  **422 错误排查**：如果前端调用 `/stats` 依然报 422，请检查：
    *   后端 `get_stats` 的参数是否被正确识别为 Query 参数。
    *   前端传递的参数名是否与后端完全一致（区分大小写）。
    *   尝试在后端暂时移除 `clusterIntervalMinutes` 的默认值，改为可选参数 `Optional[int]`。
3.  **性能考虑**：如果记录数量非常大，聚类算法在后端执行可能会有一定开销。目前数据量较小，直接内存计算即可。

## 5. 文件路径清单
*   `backend/app/schemas/types.py` (已修改)
*   `backend/app/api/endpoints/conversations.py` (已修改，需验证)
*   `frontend/src/types/index.ts` (待修改)
*   `frontend/src/api/endpoints.ts` (待修改)
*   `frontend/src/stores/analytics.ts` (待修改)
*   `frontend/src/pages/Analytics.vue` (待修改)

祝开发顺利！
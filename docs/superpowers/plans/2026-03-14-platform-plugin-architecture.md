# OpenLink 插件化架构升级计划

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**目标：** 将硬编码的平台配置重构为可扩展的插件系统

**架构：** 面向未来的可扩展插件系统，支持用户自定义平台配置

**技术栈：** TypeScript, Chrome Storage API, JSON Schema

---

## Phase 2: 插件化架构（未来阶段）

### 概述
将当前硬编码在代码中的平台配置重构为动态加载的插件系统，使用户能够：
- 自定义添加新的AI平台支持
- 修改现有平台配置而不需更改源代码
- 导入/导出现有的平台配置集合

---

### Task 1: 设计插件配置结构

**文件：**
- 新建：`extension/src/platforms/platform-config.ts`

**接口设计：**
```typescript
export interface PlatformConfig {
  id: string;                    // 唯一标识（如："qwen", "chatgpt"）
  name: string;                  // 显示名称（如："通义千问", "ChatGPT"）
  hostnames: string[];           // 适用的主机名数组（如：["qwen.ai", "www.qwen.ai"]）
  selectors: {
    editor: string;              // 主输入框选择器
    sendBtn: string;             // 发送按钮选择器  
    stopBtn?: string;            // 停止按钮选择器（可选）
  };
  responseSelector?: string;     // 响应区域选择器（用于observer模式）
  fillMethod: 'paste' | 'execCommand' | 'value' | 'prosemirror';  // 内容填充方式
  useObserver: boolean;          // 是否使用DOM观察器监控工具调用
  enabled: boolean;              // 是否启用此平台
  version?: string;              // 配置版本（便于后续升级）
}

export interface PlatformPlugin {
  schemaVersion: string;         // 插件配置格式版本
  name: string;                  // 插件名称
  description: string;           // 描述
  platforms: PlatformConfig[];   // 包含的平台配置
  author?: string;               // 作者信息
  timestamp: number;             // 创建时间戳
}
```

**验证步骤：**
1. TypeScript接口定义无语法错误
2. 各字段有合适的JSDoc注释
3. 扩展性考虑周全

**提交信息：**
```bash
git add extension/src/platforms/platform-config.ts
git commit -m "feat(platforms): 定义插件化平台配置的数据结构

- 定义PlatformConfig接口描述平台配置
- 定义PlatformPlugin接口描述插件包
- 包含必需和可选字段定义
- 为未来自定义平台支持奠定基础"
```

---

### Task 2: 实现插件存储管理器

**文件：**
- 新建：`extension/src/platforms/storage.ts`

**功能要求：**
```typescript
// 1. 加载内置平台配置
// 2. 从Chrome存储加载用户自定义配置
// 3. 保存/更新/删除用户配置
// 4. 导出/导入插件配置

export class PlatformStorage {
  private readonly STORE_KEY = 'openlink_platform_configs';
  
  // 获取所有活动的平台配置（内置 + 用户自定义）
  getAllPlatforms(): Promise<PlatformConfig[]>;
  
  // 获取单个平台配置
  getPlatform(id: string): Promise<PlatformConfig | null>;
  
  // 保存用户自定义平台
  saveCustomPlatform(config: PlatformConfig): Promise<void>;
  
  // 更新平台配置
  updatePlatform(id: string, config: Partial<PlatformConfig>): Promise<void>;
  
  // 删除用户自定义平台
  removePlatform(id: string): Promise<void>;
  
  // 重置为默认配置
  resetToDefaults(): Promise<void>;
  
  // 导出配置为JSON
  exportPlatforms(ids?: string[]): Promise<string>;
  
  // 从JSON导入配置
  importPlatforms(json: string): Promise<PlatformPlugin>;
  
  // 获取平台ID对应的域名（用于hostname匹配）
  getPlatformForHostname(hostname: string): Promise<PlatformConfig | null>;
}
```

**验证步骤：**
1. 实现CRUD基本操作
2. 处理内置平台与自定义平台合并逻辑
3. 避免内置平台被意外覆盖
4. 测试存储持久化功能

**提交信息：**
```bash
git add extension/src/platforms/storage.ts
git commit -m "feat(platforms): 实现平台配置存储管理器

- 实现PlatformStorage类提供完整的配置管理功能
- 支持内置平台与自定义平台分离管理
- 支持增删改查操作
- 支持配置导入导出功能"
```

---

### Task 3: 创建平台配置验证器

**文件：**
- 新建：`extension/src/platforms/validator.ts`

```typescript
// 验证平台配置的合法性（选择器有效性、格式等）
import Ajv from 'ajv';
import { PlatformConfig } from './platform-config';

export class PlatformValidator {
  private ajv: Ajv;
  
  constructor();
  
  // 验证配置对象格式
  validateFormat(config: any): { isValid: boolean; errors?: string[] };
  
  // 验证DOM选择器语法
  validateSelectors(config: PlatformConfig): boolean;
  
  // 验证必要字段完整性
  validateRequiredFields(config: PlatformConfig): { isValid: boolean; missingFields?: string[] };
  
  // 综合验证整个配置
  validate(config: PlatformConfig): ValidationResult;
}

interface ValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}
```

**注意：** 由于项目未使用外部库，使用原生JSON schema验证逻辑。

**验证步骤：**
1. 实现基本格式验证
2. 验证选择器语法合理性
3. 验证字段完整性
4. 返回结构化的验证结果

**提交信息：**
```bash
git add extension/src/platforms/validator.ts
git commit -m "feat(platforms): 添加平台配置验证器

- 实现配置格式验证功能
- 验证DOM选择器语法
- 提供完整的验证结果报告
- 确保用户配置的准确性"
```

---

### Task 4: 重构 getSiteConfig 为动态平台查找

**文件：**
- 修改：`extension/src/content/index.ts`

```typescript
// 1. 导入PlatformStorage
// 2. 修改getSiteConfig逻辑，从存储中加载配置
// 3. 保持向下兼容性

let platformStorage: PlatformStorage;
let currentPlatform: PlatformConfig | null = null;

// 初始化时加载平台配置
async function initializePlatformManager() {
  platformStorage = new PlatformStorage();
}

// 更新网站配置获取逻辑
async function getCurrentSiteConfig(): Promise<SiteConfig> {
  const hostname = location.hostname;
  const platform = await platformStorage.getPlatformForHostname(hostname);
  
  if (platform && platform.enabled) {
    currentPlatform = platform;
    return convertToSiteConfig(platform);
  }
  
  // 回退到默认配置
  return getDefaultFallbackConfig();
}

function convertToSiteConfig(platform: PlatformConfig): SiteConfig {
  return {
    editor: platform.selectors.editor,
    sendBtn: platform.selectors.sendBtn,
    stopBtn: platform.selectors.stopBtn || null,
    useObserver: platform.useObserver,
    fillMethod: platform.fillMethod,
    responseSelector: platform.responseSelector,
  };
}
}
```

**同时保持与现有SiteConfig接口兼容。**

**验证步骤：**
1. 网站仍能正常识别并返回正确的配置
2. 自定义平台配置生效
3. 兼容现有代码逻辑

**提交信息：**
```bash
git add extension/src/content/index.ts
git commit -m "refactor(content): 重构为动态平台配置查找

- 集成PlatformStorage管理平台配置
- 修改getSiteConfig为getCurrentSiteConfig（异步）
- 保持与现有SiteConfig接口的兼容性
- 支持运行时加载平台配置"
```

---

### Task 5: 扩展后台服务以支持配置管理

**文件：**
- 修改：`extension/src/background/index.ts`
- 依据原始代码推断实际文件名

```typescript
// 添加平台管理相关的消息处理
chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  // 现有的FETCH处理保持不变
  
  if (msg.type === 'GET_PLATFORMS') {
    platformStorage.getAllPlatforms().then(platforms => {
      sendResponse({ platforms });
    });
    return true; // keep channel open for async response
  }
  
  if (msg.type === 'SAVE_PLATFORM') {
    const validationResult = validator.validate(msg.config);
    if (validationResult.isValid) {
      platformStorage.saveCustomPlatform(msg.config).then(() => {
        sendResponse({ success: true });
      }).catch(err => {
        sendResponse({ success: false, error: err.message });
      });
      return true;
    } else {
      sendResponse({
        success: false,
        error: 'Invalid configuration',
        details: validationResult.errors
      });
    }
    return true;
  }
  
  // 更多配置管理接口...
});
```

**验证步骤：**
1. 现有的后台功能不受影响
2. 新的消息类型接口正确注册
3. 并发访问安全处理

**提交信息：**
```bash
git add extension/src/background/index.ts
git commit -m "feat(background): 添加平台配置管理后台服务

- 添加获取所有平台配置接口
- 添加保存自定义平台接口
- 集成平台验证逻辑
- 实现配置存储的后台管理"
```

---

### Task 6: 创建平台管理前端页面

**文件：**
- 新建：`extension/src/popup/pages/platforms.tsx`
- 新建：`extension/src/popup/components/platform-form.tsx`
- 新建：`extension/src/popup/components/platform-list.tsx`

**设计组件：**

**platforms.tsx:** 主管理页面
- 显示所有活动平台列表
- 导入/导出按钮
- 批量操作功能

**platform-form.tsx:** 配置编辑表单
- 配置项输入表单
- 实时验证功能
- 预览功能

**platform-list.tsx:** 平台列表组件
- 可交互的平台卡片
- 启用/禁用切换
- 编辑和删除按钮

**UI布局建议：**
```tsx
<div className="platform-manager">
  <div className="panel-header">
    <h3>平台管理</h3>
    <button onClick={() => setShowImportModal(true)}>导入</button>
    <button onClick={() => exportConfigs()}>导出</button>
    <button onClick={() => newPlatformForm.current?.reset()}>新建</button>
  </div>
  
  <div className="platform-grid">
    {/* 动态平台卡片 */}
  </div>
  
  <PlatformForm 
    onSubmit={savePlatform}
    show={showForm} 
    platform={editingPlatform} />
</div>
```

**验证步骤：**
1. UI符合Chrome扩展最佳实践
2. 响应式设计适配不同尺寸
3. 错误状态清晰展示
4. 操作反馈及时

**提交信息：**
```bash
git add extension/src/popup/pages/platforms.tsx
git add extension/src/popup/components/platform-form.tsx  
git add extension/src/popup/components/platform-list.tsx
git commit -m "feat(popup): 添加平台管理页面

- 创建平台管理主页面
- 创建平台配置编辑表单
- 创建平台列表展示组件
- 实现配置的增删改查UI交互"
```

---

### Task 7: 集成平台管理到主Popup中

**文件：**
- 修改：`extension/src/popup/App.tsx` 或对应入口文件
- 修改：`extension/src/popup/index.html`

```tsx
// 在主应用中添加平台管理导航选项
const Navigation = () => (
  <nav className="app-nav">
    <NavItem route="/" label="服务器连接" />
    <NavItem route="/history" label="历史记录" />
    <NavItem route="/platforms" label="平台管理" />
    <NavItem route="/settings" label="设置" />
  </nav>
);

// 路由配置中添加平台管理页面
const AppRouter = () => (
  <Routes>
    <Route path="/" element={<ConnectPage />} />
    <Route path="/history" element={<HistoryPage />} />
    <Route path="/platforms" element={<PlatformManager />} />
    <Route path="/settings" element={<SettingsPage />} />
  </Routes>
);
```

**验证步骤：**
1. 导航栏正确显示平台管理选项
2. 页面间跳转正常工作
3. 主题样式保持一致

**提交信息：**
```bash
git add extension/src/popup/App.tsx
git add extension/src/popup/index.html
git commit -m "feat(popup): 集成平台管理到主界面

- 添加平台管理导航项  
- 配置路由到平台管理页面
- 保持统一的UI体验"
```

---

### Task 8: 实现配置同步机制

**文件：**
- 新建：`extension/src/platforms/sync.ts`
- 修改：各需要接收配置变动的地方

```typescript
// 实现配置跨标签页同步机制
export class PlatformSyncManager {
  static CHANNEL_NAME = 'platform_config_sync';
  
  private broadcastChannel: BroadcastChannel;
  private configChangeListeners: Array<(platforms: PlatformConfig[]) => void> = [];
  
  constructor();
  
  // 监听配置变化  
  onConfigChange(callback: (platforms: PlatformConfig[]) => void): () => void;
  
  // 广播配置变化
  broadcastChanges(reason: string): void;
  
  // 同步标签页间配置变更
  private handleBroadcastMessage(event: MessageEvent): void;
  
  // 清理资源
  destroy(): void;
}

// 使用方式：
// 1. 内容脚本中监听变化，更新当前页配置
// 2. 弹窗中修改配置后通知各标签页刷新
// 3. 后台服务中同步存储更新
```

**验证步骤：**
1. 多标签页间的配置同步正常工作
2. 配置变化不会导致内存泄漏  
3. 网络通信量控制在合理范围

**提交信息：**
```bash
git add extension/src/platforms/sync.ts
git commit -m "feat(platforms): 实现配置同步机制

- 添加跨标签页配置同步功能
- 创建变更监听和广播机制
- 确保配置更新的一致性"
```

---

### Task 9: 添加配置示例和默认模板

**文件：**
- 新建：`extension/src/platforms/default-presets.ts`

```typescript
// 提供常见平台的配置模板
export const PRESET_PLATFORMS: Record<string, PlatformConfig> = {
  'gemini': {
    id: 'gemini',
    name: 'Google Gemini',
    hostnames: ['gemini.google.com'],
    selectors: {
      editor: 'div.ql-editor[contenteditable="true"]',
      sendBtn: 'button.send-button[aria-label*="发送"], button.send-button[aria-label*="Send"]',
      stopBtn: null,
    },
    fillMethod: 'execCommand',
    useObserver: true,
    enabled: true
  },
  'chatgpt': {
    id: 'chatgpt',
    name: 'ChatGPT',
    hostnames: ['chatgpt.com', 'www.chatgpt.com'],
    selectors: {
      editor: '.ProseMirror[contenteditable="true"]#prompt-textarea, .ProseMirror[contenteditable="true"]',
      sendBtn: 'button[data-testid="send-button"], button[aria-label*="Send"], button[aria-label*="发送"]',
      stopBtn: null,
    },
    fillMethod: 'prosemirror',
    useObserver: true,
    responseSelector: '.markdown.prose',
    enabled: true
  },
  // 更多预设...
};

export const IMPORT_TEMPLATES: Array<{ title: string; description: string; config: PlatformPlugin }> = [
  { 
    title: '主流AI平台套件', 
    description: 'Google Gemini, ChatGPT, 通义千问等常见AI平台配置', 
    config: { /* 包含多个平台的插件配置 */ } 
  },
  // 更多模板...
];
```

**验证步骤：**
1. 预设模板覆盖常见平台
2. 配置示例保持更新
3. 操作说明清晰

**提交信息：**
```bash
git add extension/src/platforms/default-presets.ts
git commit -m "feat(platforms): 添加常用平台配置预设

- 提供主流AI平台的标准配置模板
- 创建配置导入建议列表
- 简化用户自定义流程"
```

---

### Task 10: 测试和文档

**文件：**
- 创建：`extension/src/platforms/__tests__/integration.test.ts`
- 更新：`docs/platform-plugins.md`

**集成测试包括：**
1. 配置加载和验证流程
2. 动态平台识别功能  
3. 跨页面配置同步
4. 导入导出功能
5. 边界情况处理

**文档包含：**
1. 插件系统架构说明
2. 用户使用指南
3. 开发者API文档
4. 常见问题解决

**验证步骤：**
1. 完成功能性测试
2. 测试向后兼容性
3. 性能影响评估
4. 安全性检查

**提交信息：**
```bash
git add extension/src/platforms/__tests__/integration.test.ts
git add docs/platform-plugins.md
git commit -m "test(platforms): 完成插件化架构集成测试

- 实现配置管理的全面测试用例
- 更新使用文档和支持材料
- 完成系统集成验证"
```

---

## 迁移策略

### 步骤1: 兼容处理
1. 保持原有的硬编码配置作为默认值
2. 用户首次升级时自动创建配置备份
3. 逐步引导用户迁移到插件化配置

### 步骤2: 数据迁移  
1. 从现有的代码配置转换为存储配置
2. 用户自定义配置优先级高于默认配置  
3. 配置冲突时用户选择处理

### 步骤3: 功能增强
1. 添加社区预设分享功能
2. 实现配置版本管理  
3. 提供配置健康检查工具

## 技术注意事项

1. **性能考虑**: 避免每次页面加载时重复解析配置
2. **安全性**: 验证用户提供的DOM选择器防止XSS
3. **向后兼容**: 确保老用户的配置正常使用
4. **存储效率**: Chrome存储API有大小限制
5. **缓存策略**: 实施适当的配置缓存机制

## 验证检查点

1. 现有功能100%正常工作
2. 新平台配置动态生效
3. 配置导入导出功能完善
4. 系统性能不受明显影响
5. 用户体验保持简洁
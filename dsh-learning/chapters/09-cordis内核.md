# 第9章 Cordis 插件内核

> 这是理解 dsh 的"地基"。前面反复说"一切皆插件"，本章就讲 Cordis 这个插件框架**到底怎么工作**。

## 9.1 五种核心思想（先记住这五个）

来自 `docs/cordis-primer.md`，Cordis 的设计哲学有五条：

1. **插件是实现 `Service` 的对象**：可以是一个函数，或一个带 `inject`/`apply` 的对象。
2. **上下文是服务的仓库（ctx）**：服务占据稳定的 `ctx.<key>`（例如 `ctx.tools`、`ctx.llm`、`ctx.sessions`）。
3. **用 `inject` 声明依赖**：依赖关系同时表达了**加载顺序**，不用你手动写 boot 排序。
4. **用类型化事件通信**：`emit` / `waterfall` / `parallel` / `serial` 四种模式。
5. **注册是可逆的 effect**：通过 `ctx.effect()` 或 `ctx.on()` 安装，卸载/重载时统一回滚。

## 9.2 插件契约：name / inject / apply

一个最小插件长这样（以你写的 `my_notes` 为例，`packages/notes/tool-my-notes/src/index.ts`）：

```ts
import type { Context } from '@deepseek-ai/cordis'
import { defineTool } from '@deepseek-ai/dsh-tools'

export const name = 'tool-my-notes'      // 插件名
export const inject = ['tools']          // 声明依赖 ctx.tools（框架据此决定加载顺序）
export const Config = /* zod schema */  // 该插件可配置项

export function apply(ctx: Context, config: Config): void {
  // 在这里向 ctx 贡献能力
  ctx.tools.register(defineTool({ /* ... */ }))
}
```

三段式解读：

- `name`：插件的唯一标识。
- `inject: ['tools']`：告诉框架"我需要 `ctx.tools` 这个服务先就绪"。框架据此**自动排序**——`tools` 插件先加载，你的插件后加载。你不用写任何初始化顺序代码。
- `apply(ctx, config)`：插件"生效"的入口。所有注册都写在这里。

## 9.3 共享上下文 ctx：能力的"地址"

`ctx` 是整个系统的服务仓库。每个包"拥有"一个 key：

- `ctx.tools` —— 工具注册表（来自 `core/tools`）
- `ctx.llm` —— 模型适配层（来自 `llm/llm`）
- `ctx.sessions` —— 会话日志（来自 `core/session`）
- `ctx.agentPresets` —— 预设（来自 `preset/agent-presets`）

当你写 `ctx.tools.register(...)`，你就是在"往 `ctx.tools` 这张表里插一行"。别的插件、框架主循环，都从这里取工具。**这就是 dsh 各部件解耦协作的方式：谁都不直接 import 谁，只通过 `ctx` 贡献/消费服务。**

## 9.4 类型化事件：扩展点

除了服务，插件还能往 `ctx` 上挂**事件**。dsh 里大量"拦截点"都是事件：

- `agent/pre-step`：决定模型这一步看到什么（可改写/拒绝）；
- `agent/request`、`llm/stream`：模型请求与流式输出（瀑布，可监听）；
- `tools/pre-execute` / `tools/execute` / `tools/post-execute`：工具执行前后；
- `session/event`：会话事件的广播。

事件有四种触发模式（来自 primer）：

- `emit`：通知所有人，不等结果；
- `waterfall`：依次传递、可被改写（如 `agent/pre-step` 改写消息）；
- `parallel` / `serial`：并行/串行收集多个监听者结果。

> 小白意义：如果你想"在每次工具调用前打印日志"，你**不需要改工具代码**，只要监听 `tools/pre-execute` 事件即可。扩展 = 监听/贡献事件，不是改源码。

## 9.5 可逆 effect：为什么"卸载即干净"

所有注册都经由 `ctx.effect()` 或 `ctx.on()`。规则（见 `AGENTS.md` 与 primer）：

> every contribution goes through `ctx.effect()` / `ctx.on()`; a registry's `register()` returns the disposer.

意思是：`ctx.tools.register(...)` 的**返回值就是一个"销毁器（disposer）"**。插件卸载时，框架调用这个销毁器，你注册的那行就被撤掉。

这就保证了：

- 你加的 `my_notes` 工具，撤掉插件 → 工具从表里消失，**不留残留**；
- 升级、回滚、热重载都安全。

这正是第 5 章说的"可回滚"的工程实现。

## 9.6 源码入口（想深入时读这些）

| 主题 | 文件 |
|---|---|
| Cordis 入门 | `docs/cordis-primer.md` |
| 框架源码 | `vendor/cordis/src/`（`index.ts`、`context.ts`、`events.ts`、`registry.ts`、`service.ts`、`fiber.ts`） |

## 9.7 一句话总结

> Cordis 用 `ctx` 当服务仓库、用 `inject` 定顺序、用事件做扩展点、用可逆 `effect` 保回滚——**插件只需"贡献"，系统负责"编排"**。

> 下一章：模型每轮看到的"上下文"从哪来？答案是**会话日志 + 系统提示**。

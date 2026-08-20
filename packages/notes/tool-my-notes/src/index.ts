/**
 * 我的私有笔记工具（my_notes）
 *
 * 这是「阶段一」手写的第一个工具，用来演示 dsh 的插件扩展模型：
 *   - 一个工具 = 一个 Cordis 插件（导出 name / inject / apply）。
 *   - 插件通过 ctx.tools.register(defineTool({...})) 把自己的能力注册到工具表。
 *   - 模型在 ReAct 循环里看到这个工具，并决定何时调用它。
 *
 * 工具能力：
 *   - list   列出 ~/dsh-notes 下所有 .md 笔记文件名
 *   - read   读取某一篇笔记的全文
 *   - search 在所有笔记里按关键词（不区分大小写）搜索，返回命中行
 *
 * 笔记根目录默认是 ~/dsh-notes，可在 preset 的工具行里用 config.root 覆盖。
 *
 * @module @deepseek-ai/dsh-tool-my-notes
 */

import { readdir, readFile, stat } from 'node:fs/promises'
import { homedir } from 'node:os'
import { join } from 'node:path'
import type { Context } from '@deepseek-ai/cordis'
import z from '@deepseek-ai/schemastery'
import { defineTool } from '@deepseek-ai/dsh-tools'

// 插件标识：loader 用它把本模块识别为一个 Cordis 插件。
export const name = 'tool-my-notes'
// 声明本插件依赖的上下文服务；'tools' 是工具注册表。
export const inject = ['tools']

/** 工具配置：笔记根目录（可选，默认 ~/dsh-notes）。 */
export interface Config {
  /** 笔记文件夹路径；缺省为当前用户主目录下的 dsh-notes。 */
  root?: string
}

/** 用 schemastery 描述配置，供运行时的配置校验与文档生成使用。 */
export const Config: z<Config> = z.object({
  root: z.string().default(join(homedir(), 'dsh-notes')),
})

/** 计算笔记根目录：优先用配置，否则回退到 ~/dsh-notes。 */
function notesRoot(config: Config): string {
  const fallback = join(homedir(), 'dsh-notes')
  return config.root?.trim() ? config.root.trim() : fallback
}

/** 只保留 .md / .markdown 文件，并排序。目录不存在时返回空列表。 */
async function listNotes(root: string): Promise<string[]> {
  let entries: string[]
  try {
    entries = await readdir(root)
  } catch {
    // 目录不存在时当作「还没有任何笔记」，返回空列表而不是报错。
    return []
  }
  const files: string[] = []
  for (const entry of entries) {
    if (!/\.(md|markdown)$/i.test(entry)) continue
    if ((await stat(join(root, entry))).isFile()) files.push(entry)
  }
  return files.sort()
}

/** 把一次工具调用的结果整理成可读文本后返回。 */
function ok(text: string) {
  return Promise.resolve({ result: text })
}

/**
 * 插件入口。Cordis 在挂载本插件时调用 apply(ctx, config)。
 * @param ctx - 插件上下文，携带工具注册表。
 * @param config - preset / 部署下发的配置。
 */
export function apply(ctx: Context, config: Config): void {
  const root = notesRoot(config)
  ctx.tools.register(defineTool({
    name: 'my_notes',
    description:
      '读取并检索你的个人 Markdown 笔记（位于 ' + root + '）。'
      + '可用动作：list 列出全部笔记文件名；read 读取某篇笔记全文（需提供 name）；'
      + 'search 在所有笔记中按关键词搜索并返回命中行（需提供 keyword）。'
      + '当你需要回忆、查找或引用之前记下的内容时使用。',
    parameters: {
      action: {
        type: 'string',
        required: true,
        description: '要执行的操作：list | read | search',
        enum: ['list', 'read', 'search'],
      },
      name: {
        type: 'string',
        description: 'read 操作时的笔记文件名（含扩展名），例如 my-ideas.md（可选）',
      },
      keyword: {
        type: 'string',
        description: 'search 操作时的关键词，不区分大小写（可选）',
      },
    },
    // output 描述返回结构；render 决定在对话里如何展示返回值。
    output: {
      schema: {
        type: 'object',
        additionalProperties: false,
        properties: {
          result: { type: 'string', required: true, description: '工具返回的可读文本' },
        },
      },
      render: (_args, value) => [{ type: 'text', text: value.result }],
    },
    // execute 是模型真正调用工具时执行的函数。
    async execute(args) {
      const { action, name: fileName, keyword } = args as {
        action: 'list' | 'read' | 'search'
        name?: string
        keyword?: string
      }

      if (action === 'list') {
        const files = await listNotes(root)
        if (files.length === 0) return ok(`笔记目录 ${root} 下还没有任何 .md 笔记。`)
        return ok('我的笔记列表：\n' + files.map(f => `- ${f}`).join('\n'))
      }

      if (action === 'read') {
        if (!fileName) throw new Error('read 操作需要提供 name（笔记文件名）')
        const full = join(root, fileName)
        let content: string
        try {
          content = await readFile(full, 'utf8')
        } catch {
          throw new Error(`找不到笔记 ${fileName}（预期路径：${full}）`)
        }
        return ok(`# ${fileName}\n\n${content}`)
      }

      if (action === 'search') {
        if (!keyword) throw new Error('search 操作需要提供 keyword（关键词）')
        const needle = keyword.toLowerCase()
        const files = await listNotes(root)
        const hits: string[] = []
        for (const file of files) {
          const lines = (await readFile(join(root, file), 'utf8')).split('\n')
          lines.forEach((line, i) => {
            if (line.toLowerCase().includes(needle)) {
              hits.push(`${file}:${i + 1}: ${line.trim()}`)
            }
          })
        }
        if (hits.length === 0) return ok(`在笔记中没有找到包含「${keyword}」的内容。`)
        return ok(`在笔记中找到 ${hits.length} 处匹配：\n` + hits.join('\n'))
      }

      throw new Error(`未知的操作 ${String(action)}，仅支持 list / read / search`)
    },
  }))
}

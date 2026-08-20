#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
dsh-learning 学习书生成器（扁平结构 · 单信息源 = chapters/*.md）
==============================================================

把 chapters/ 下每篇 Markdown 转成「可双击打开」的 HTML 阅读页，并生成 index.html
作为书目首页（导读 + 学习路线图 + 章节总览）。

设计要点（避免此前 BUG）：
  - 所有生成的 HTML 都放在 dsh-learning/ 根目录，章节之间只用「同目录文件名」互链
    （如 01-大模型.html），因此**不存在子目录相对路径重复**的问题。
  - 章节顺序与分组由下方 BOOK 列表唯一决定（单一信息源）；新增/调整章节只改这一处。

目录结构：
  dsh-learning/
    build.py          # 本脚本
    chapters/*.md     # 写作源文件（单信息源）
    index.html        # 书目首页（自动生成）
    *.html            # 每章一页（自动生成）

用法：
  python3 build.py            # 重新生成全部 HTML
依赖：
  pip install markdown        # 仅用到 markdown 库（toc / tables / fenced_code）
"""

import os
import re
import markdown

ROOT = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(ROOT, "chapters")

# ── 书目清单（顺序即阅读顺序；part 用于侧边栏与路线图分组）─────────────────
# 每一项: (part, 章节标题, md 文件名, 本文学系目标)
BOOK = [
    ("Part 0 · 学前通识（0 基础）", "导读：本书怎么读、你将学会什么", "00-导读.md",
     "了解本书的定位与阅读方法，建立「从 0 基础到能改造 dsh」的完整学习路线。"),
    ("Part 0 · 学前通识（0 基础）", "第1章 什么是大模型（LLM）", "01-大模型.md",
     "用生活化比喻理解大模型是什么、能做什么、为什么需要 Agent 来驾驭它。"),
    ("Part 0 · 学前通识（0 基础）", "第2章 什么是提示词（Prompt）", "02-提示词.md",
     "理解人如何通过提示词与模型对话，以及系统提示、角色设定与少样本。"),
    ("Part 0 · 学前通识（0 基础）", "第3章 什么是指令循环与 Agent", "03-智能体.md",
     "理解 Agent = 模型 + 工具 + 循环，以及它如何自主完成多步任务。"),
    ("Part 0 · 学前通识（0 基础）", "第4章 什么是 Harness（智能体框架）", "04-框架.md",
     "理解 Harness 的作用：把模型、工具、记忆、上下文串成一辆可驾驶的「车」。"),
    ("Part 0 · 学前通识（0 基础）", "第5章 为什么选 dsh 做终身个人 Agent", "05-为何dsh.md",
     "理解 dsh 的「插件化」架构为何适合作为你终身迭代、更新的个人 Agent。"),

    ("Part 1 · 项目全景", "第6章 dsh 是什么 & 中心思想", "06-项目是什么.md",
     "掌握 dsh 的定位与中心思想「一切皆插件」，以及 Cordis 框架的角色。"),
    ("Part 1 · 项目全景", "第7章 本地把项目跑起来", "07-本地运行.md",
     "在本地把 dsh 跑起来（pnpm install / pnpm dsh web），理解免构建的源码启动。"),
    ("Part 1 · 项目全景", "第8章 目录结构与文件含义", "08-目录结构.md",
     "逐一看懂 packages/、vendor/、docs/、apps/ 等目录与关键文件的作用。"),

    ("Part 2 · 核心源码精讲", "第9章 Cordis 插件内核", "09-cordis内核.md",
     "理解 Cordis：插件契约、ctx 服务仓库、依赖注入、可逆 effect 生命周期。"),
    ("Part 2 · 核心源码精讲", "第10章 会话日志与系统提示", "10-会话与提示.md",
     "理解会话日志（SessionEvent）与系统提示组装，以及「模型可见即已记录」铁律。"),
    ("Part 2 · 核心源码精讲", "第11章 工具系统（tools / defineTool）", "11-工具系统.md",
     "理解工具系统：defineTool 结构、参数必填规则、作用域注册与带保护执行。"),
    ("Part 2 · 核心源码精讲", "第12章 LLM 能力层（llm provider）", "12-大模型层.md",
     "理解 LLM 能力层：Service Definition/Provider/Consumer 三角色与 DeepSeek 适配器。"),
    ("Part 2 · 核心源码精讲", "第13章 Agent 主循环（turn 流）", "13-主循环.md",
     "理解一个 turn 从领取输入、组装提示、调用模型到工具调用的完整事件流。"),
    ("Part 2 · 核心源码精讲", "第14章 预设系统（preset）与默认覆盖", "14-预设系统.md",
     "理解预设系统：defaultId 如何由 settings.yaml 覆盖 config.default，零改核心。"),
    ("Part 2 · 核心源码精讲", "第15章 实战：写第一个私有工具 my_notes", "15-实战工具.md",
     "动手写第一个私有工具 my_notes，并逐行讲解其代码与「改动逻辑」。"),

    ("Part 3 · 动手进化", "第16章 如何给 dsh 加能力", "16-如何加能力.md",
     "掌握加能力的方法：工具、记忆（新 SessionEvent）、子 Agent，以及扩展点映射表。"),
    ("Part 3 · 动手进化", "第17章 长期演进路线图", "17-演进路线.md",
     "规划长期演进：私有工具 → 个人知识库/记忆 → 多 Agent 协作 → 终身自治。"),
    ("Part 3 · 动手进化", "第18章 学习小结与下一步", "18-小结.md",
     "回顾学习成果，给出下一步行动清单与进阶资源。"),
]


# ── 共享样式（书本式阅读器，浅色专业风）────────────────────────────────────
CSS = """
:root{
  --bg:#f5f6f8; --paper:#ffffff; --ink:#1b2430; --muted:#5d6675; --faint:#8b94a3;
  --border:#e6e9ef; --accent:#2563eb; --accent-soft:#eaf1ff; --accent-ink:#1d4ed8;
  --green:#0f9d6b; --green-soft:#e7f6ef; --amber:#b9790a; --amber-soft:#fbf2dd;
  --code-bg:#0f172a; --code-fg:#e2e8f0;
  --radius:12px; --shadow:0 1px 2px rgba(16,32,46,.05),0 6px 24px rgba(16,32,46,.06);
}
*{box-sizing:border-box}
html{scroll-behavior:smooth}
body{margin:0;background:var(--bg);color:var(--ink);
  font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC","Hiragino Sans GB","Microsoft YaHei",Roboto,Helvetica,Arial,sans-serif;
  line-height:1.85;font-size:16px}
a{color:var(--accent-ink);text-decoration:none}
a:hover{text-decoration:underline}
code{font-family:"SF Mono",ui-monospace,Menlo,Consolas,monospace;font-size:.86em;
  background:var(--accent-soft);color:var(--accent-ink);padding:.1em .36em;border-radius:5px}
pre{margin:0}
.progress{position:fixed;top:0;left:0;height:3px;background:var(--accent);width:0;z-index:60}
header.top{position:sticky;top:0;z-index:50;background:rgba(255,255,255,.88);
  backdrop-filter:saturate(160%) blur(10px);border-bottom:1px solid var(--border)}
.top-inner{max-width:1200px;margin:0 auto;padding:12px 22px;font-weight:700;letter-spacing:.2px;
  display:flex;align-items:center;gap:10px}
.top-inner .dot{width:11px;height:11px;border-radius:3px;background:var(--accent)}
.top-inner small{font-weight:400;color:var(--faint);font-size:13px;margin-left:auto}
.top-inner a.home{color:var(--accent-ink);font-weight:600;font-size:13px}

.layout{display:grid;grid-template-columns:288px minmax(0,1fr);gap:40px;
  max-width:1200px;margin:0 auto;padding:26px 22px 90px}
.sidebar{position:sticky;top:66px;align-self:start;height:calc(100vh - 88px);overflow:auto;
  background:var(--paper);border:1px solid var(--border);border-radius:var(--radius);
  padding:16px 14px;box-shadow:var(--shadow);font-size:13px}
.side-cat{font-size:11.5px;font-weight:800;letter-spacing:.4px;color:var(--ink);
  margin:10px 8px 6px;padding-bottom:5px;border-bottom:2px solid var(--accent-soft)}
.sidebar ul{list-style:none;margin:0;padding:0}
.sidebar li{margin:0}
.sidebar a{display:block;padding:5px 10px;border-radius:8px;color:var(--muted);
  border-left:3px solid transparent;line-height:1.45}
.sidebar a:hover{background:var(--bg);color:var(--ink);text-decoration:none}
.sidebar a.active{color:var(--accent-ink);border-left-color:var(--accent);
  background:var(--accent-soft);font-weight:700}
.sidebar .toc{font-size:12.5px;margin:2px 0 10px;padding-left:4px}
.sidebar .toc ul{list-style:none;margin:0;padding:0}
.sidebar .toc li{margin:0}
.sidebar .toc a{display:block;padding:2px 9px;border-radius:6px;color:var(--muted);
  border-left:2px solid transparent}
.sidebar .toc a:hover{background:var(--bg)}
.sidebar .toc a.active{color:var(--accent-ink);border-left-color:var(--accent);
  background:var(--accent-soft);font-weight:600}

main{min-width:0}
.breadcrumb{font-size:13px;color:var(--faint);margin:2px 0 16px}
.breadcrumb b{color:var(--muted)}
.cover{background:linear-gradient(180deg,#fff,#eef3fb);border:1px solid var(--border);
  border-radius:16px;padding:34px 36px;margin-bottom:26px;box-shadow:var(--shadow)}
.cover .kicker{font-size:12px;letter-spacing:1.5px;color:var(--accent);font-weight:700}
.cover h1{font-size:28px;line-height:1.3;margin:8px 0 10px;letter-spacing:-.3px}
.cover .lede{color:var(--muted);margin:0 0 16px;font-size:15px;max-width:680px}
.goal{display:flex;gap:10px;align-items:flex-start;background:var(--accent-soft);
  border:1px solid #cfe0ff;border-radius:10px;padding:12px 14px;font-size:14.5px;color:var(--accent-ink)}
.goal .gicon{font-size:16px;line-height:1.4}
.goal b{margin-right:4px}
.article{background:var(--paper);border:1px solid var(--border);border-radius:var(--radius);
  padding:28px 36px;margin:0 0 26px;box-shadow:var(--shadow);scroll-margin-top:70px}
.article h2{font-size:22px;letter-spacing:-.2px;margin:26px 0 10px;padding-top:6px;
  border-left:4px solid var(--accent);padding-left:12px}
.article h3{font-size:17px;margin:22px 0 8px;color:var(--ink)}
.article h4{font-size:15px;margin:16px 0 6px;color:var(--ink)}
.article p{margin:12px 0}
.article ul,.article ol{margin:12px 0;padding-left:24px}
.article li{margin:5px 0}
.article pre{background:var(--code-bg);border-radius:10px;padding:16px 18px;overflow:auto;margin:14px 0}
.article pre code{background:transparent;color:var(--code-fg);padding:0;font-size:13px;line-height:1.6;white-space:pre}
.article blockquote{margin:14px 0;padding:12px 16px;border-left:3px solid var(--accent);
  background:var(--accent-soft);border-radius:0 8px 8px 0;color:var(--muted)}
.article blockquote p{margin:4px 0}
.article table{border-collapse:collapse;width:100%;margin:16px 0;font-size:14px;
  box-shadow:var(--shadow);border-radius:8px;overflow:hidden}
.article th,.article td{border:1px solid var(--border);padding:9px 12px;text-align:left;vertical-align:top}
.article th{background:var(--bg);font-weight:700;color:var(--ink)}
.article tr:nth-child(even) td{background:#fafbfd}
.callout{margin:16px 0;padding:13px 16px;border-radius:10px;font-size:14.5px;border:1px solid transparent}
.callout.key{background:var(--accent-soft);border-color:#cfe0ff;color:var(--accent-ink)}
.callout.tip{background:var(--green-soft);border-color:#bfe9d6;color:#0b6b49}
.callout.warn{background:var(--amber-soft);border-color:#f0dcae;color:#7a4f06}
.pager{display:flex;gap:14px;margin-top:6px}
.pager a{flex:1;background:var(--paper);border:1px solid var(--border);border-radius:10px;
  padding:14px 16px;box-shadow:var(--shadow);color:var(--ink)}
.pager a:hover{border-color:var(--accent);text-decoration:none}
.pager .dir{font-size:12px;color:var(--faint)}
.pager .ptitle{font-weight:700;margin-top:3px;display:block;color:var(--accent-ink)}
.pager .next{text-align:right}
footer{color:var(--faint);font-size:13px;text-align:center;padding:30px 16px 50px}
footer code{background:var(--bg)}

/* 首页 */
.home{max-width:1080px;margin:0 auto;padding:36px 22px 80px}
.hero{background:linear-gradient(180deg,#fff,#eef3fb);border:1px solid var(--border);
  border-radius:16px;padding:40px 38px;margin-bottom:30px;box-shadow:var(--shadow)}
.hero h1{font-size:30px;margin:0 0 10px;letter-spacing:-.3px}
.hero p{color:var(--muted);margin:0;font-size:15px;max-width:800px}
.road{list-style:none;margin:0;padding:0;position:relative}
.road::before{content:"";position:absolute;left:19px;top:8px;bottom:8px;width:2px;background:var(--border)}
.rstep{position:relative;display:flex;gap:18px;padding:12px 0}
.rstep .dot{flex:0 0 40px;height:40px;border-radius:50%;display:flex;align-items:center;
  justify-content:center;color:#fff;font-weight:800;font-size:13px;z-index:1;background:var(--accent);
  box-shadow:0 0 0 4px var(--bg)}
.rstep .body{flex:1;background:var(--paper);border:1px solid var(--border);border-radius:12px;
  padding:14px 18px;box-shadow:var(--shadow)}
.rstep .body a.title{font-size:16px;font-weight:700;color:var(--ink)}
.rstep .body a.title:hover{text-decoration:none;color:var(--accent-ink)}
.rstep .meta{font-size:12px;color:var(--faint);margin:4px 0 2px}
.rstep .goal{color:var(--muted);font-size:14px;margin:4px 0 0}
.sec-title{font-size:20px;margin:34px 0 4px}
.sec-sub{color:var(--muted);margin:0 0 18px;font-size:14px}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px}
.card{background:var(--paper);border:1px solid var(--border);border-radius:var(--radius);
  padding:18px 20px;box-shadow:var(--shadow);transition:transform .12s ease,border-color .12s ease}
.card:hover{transform:translateY(-2px);border-color:var(--accent);text-decoration:none}
.card .part{font-size:11px;font-weight:700;color:var(--accent);letter-spacing:.5px}
.card h3{margin:6px 0 8px;font-size:16px;color:var(--ink)}
.card p{margin:0;color:var(--muted);font-size:13.5px;line-height:1.6}
"""

JS = """
const prog=document.getElementById('progress');
const onScroll=()=>{const h=document.documentElement;
  prog.style.width=(h.scrollTop/(h.scrollHeight-h.clientHeight)*100)+'%';};
window.addEventListener('scroll',onScroll,{passive:true});onScroll();
const tocLinks=[...document.querySelectorAll('aside.sidebar .toc a')];
const heads=[...document.querySelectorAll('main .article h2[id],main .article h3[id]')];
if(heads.length && tocLinks.length){
  const obs=new IntersectionObserver((es)=>{es.forEach(e=>{
    if(e.isIntersecting){const id=e.target.id;
      tocLinks.forEach(a=>a.classList.toggle('active',a.getAttribute('href')==='#'+id));}
  });},{rootMargin:'-45% 0px -50% 0px'});
  heads.forEach(h=>obs.observe(h));
}
"""

DOC_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>{title} · dsh 学习书</title>
<style>{css}</style>
</head>
<body>
<div class="progress" id="progress"></div>
<header class="top"><div class="top-inner"><span class="dot"></span>dsh 学习书
  <a class="home" href="index.html">← 目录</a>
  <small>{part}</small></div></header>
<div class="layout">
<aside class="sidebar">
  <div class="side-cat">本页大纲</div>
  <div class="toc">{toc}</div>
  {nav}
</aside>
<main>
<div class="breadcrumb">{part} <b>›</b> {title}</div>
<div class="cover"><div class="kicker">{part}</div><h1>{title}</h1>
  <p class="lede">{lede}</p>
  <div class="goal"><span class="gicon">🎯</span><div><b>本文学系目标</b>{goal}</div></div>
</div>
<article class="article">
{content}
</article>
<nav class="pager">{pager}</nav>
</main>
</div>
<footer>dsh 学习书 · 配套 Markdown 见 <code>chapters/</code> · 双击 HTML 即可离线阅读</footer>
<script>{js}</script>
</body></html>"""

HOME_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1.0"/>
<title>dsh 学习书 · 从 0 学会智能体框架</title>
<style>{css}</style>
</head>
<body>
<div class="progress" id="progress"></div>
<header class="top"><div class="top-inner"><span class="dot"></span>dsh 学习书
  <small>从 0 基础到改造 dsh</small></div></header>
<div class="home">
<div class="hero"><h1>dsh 学习书：把 DeepSeek Harness 读成一本「可进化的书」</h1>
<p>你不需要是专业开发者，也能跟着这本书从零弄懂：大模型是什么、Agent 是什么、Harness 是什么，
再深入 dsh 的源码，理解它「一切皆插件」的中心思想，最后动手改造它，让它成为你<strong>终身迭代的个人 Agent</strong>。
全书分四部分、19 章，建议按顺序读；每一章都可双击 HTML 离线阅读。</p></div>

<section><h2 class="sec-title">学习路线图</h2>
<p class="sec-sub">按编号顺序阅读；点击任意章节直达。</p>
<ol class="road">{road}</ol></section>

<section><h2 class="sec-title">章节总览</h2>
<p class="sec-sub">按「分类 → 章节」组织，方便按主题跳读。</p>
<div class="grid">{cards}</div></section>
</div>
<footer>dsh 学习书 · 由 <code>build.py</code> 自动生成 · 改 BOOK 列表后重跑脚本即可</footer>
<script>{js}</script>
</body></html>"""


def extract_title_lede(md_text):
    lines = md_text.splitlines()
    title = "未命名文档"
    for ln in lines:
        if ln.startswith("# "):
            title = ln[2:].strip()
            break
    lede = ""
    started = False
    for ln in lines:
        s = ln.strip()
        if not started:
            if s.startswith("# "):
                started = True
            continue
        if not s:
            continue
        if s.startswith(("#", ">", "-", "*", "|", "```")):
            continue
        lede = s
        break
    return title, lede


def html_name(md_file):
    return md_file[:-3] + ".html"


def build_nav(active_file):
    groups = {}
    for part, title, fn, goal in BOOK:
        groups.setdefault(part, []).append((title, fn))
    out = ['<nav class="side">']
    for part, items in groups.items():
        out.append(f'<div class="side-cat">{part}</div><ul>')
        for title, fn in items:
            active = ' class="active"' if fn == active_file else ""
            out.append(f'<li><a{active} href="{html_name(fn)}">{title}</a></li>')
        out.append("</ul>")
    out.append("</nav>")
    return "".join(out)


def build_pager(idx):
    prev = BOOK[idx - 1] if idx > 0 else None
    nxt = BOOK[idx + 1] if idx < len(BOOK) - 1 else None
    out = []
    if prev:
        out.append(f'<a class="prev" href="{html_name(prev[2])}"><span class="dir">← 上一篇</span>'
                   f'<span class="ptitle">{prev[1]}</span></a>')
    else:
        out.append('<a class="prev" style="visibility:hidden"></a>')
    if nxt:
        out.append(f'<a class="next" href="{html_name(nxt[2])}"><span class="dir">下一篇 →</span>'
                   f'<span class="ptitle">{nxt[1]}</span></a>')
    else:
        out.append('<a class="next" style="visibility:hidden"></a>')
    return "".join(out)


def build_chapter(md_path, idx):
    part, title_doc, fn, goal = BOOK[idx]
    with open(md_path, encoding="utf-8") as f:
        md_text = f.read()
    md = markdown.Markdown(extensions=["toc", "tables", "fenced_code", "sane_lists"])
    content = md.convert(md_text)
    toc = md.toc
    title, lede = extract_title_lede(md_text)
    nav = build_nav(fn)
    pager = build_pager(idx)
    html = (DOC_TEMPLATE.replace("{css}", CSS).replace("{js}", JS)
            .replace("{toc}", toc)
            .replace("{nav}", nav)
            .replace("{part}", part)
            .replace("{title}", title)
            .replace("{lede}", lede)
            .replace("{goal}", goal)
            .replace("{content}", content)
            .replace("{pager}", pager))
    out = os.path.join(ROOT, html_name(fn))
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def build_home():
    # 路线图
    road = []
    for i, (part, title, fn, goal) in enumerate(BOOK, 1):
        road.append(
            f'<li class="rstep"><div class="dot">{i}</div>'
            f'<div class="body"><a class="title" href="{html_name(fn)}">{title}</a>'
            f'<div class="meta">{part}</div><p class="goal">{goal}</p></div></li>')
    # 卡片总览
    cards = []
    for part, title, fn, goal in BOOK:
        cards.append(
            f'<a class="card" href="{html_name(fn)}"><div class="part">{part}</div>'
            f'<h3>{title}</h3><p>{goal}</p></a>')
    home = (HOME_TEMPLATE.replace("{css}", CSS).replace("{js}", JS)
            .replace("{road}", "".join(road))
            .replace("{cards}", "".join(cards)))
    with open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8") as f:
        f.write(home)


def main():
    if not os.path.isdir(SRC):
        print("缺少 chapters/ 目录，请先放入 .md 源文件。")
        return
    for i, (part, title, fn, goal) in enumerate(BOOK):
        md_path = os.path.join(SRC, fn)
        if not os.path.exists(md_path):
            print(f"  跳过（源文件缺失）: {fn}")
            continue
        out = build_chapter(md_path, i)
        print("  +", os.path.relpath(out, ROOT))
    build_home()
    print("首页：index.html")


if __name__ == "__main__":
    main()

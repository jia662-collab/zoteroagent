# Zotero Connector 优先导入设计

## 目标

把已核验论文保存到 Zotero 时，每篇只产生一个父条目，PDF 作为该条目的子附件；避免“RIS 条目”和“PDF 自动识别条目”并列重复。

## 选定方案

浏览器保存为主，RIS 仅作失败兜底。

1. PaperLab 从 `candidates.json` 读取已核验的官方论文页面。
2. 同步 Zotero 索引，已存在的 DOI 或标题直接跳过。
3. Codex 控制 Chrome，逐篇打开论文正式页面，不打开 PDF 直链作为保存入口。
4. 使用 Zotero Connector 保存页面，让 Connector 一次创建父条目并附加可获取的 PDF。
5. 每保存一篇就检查成功状态，再处理下一篇。
6. 完成一批后重新同步 Better BibTeX，并由 PaperLab 按 DOI、标题和 PDF 数量验收。

## 失败处理

- 已有父条目但没有 PDF：在 Zotero 中对该条目使用“查找全文”（旧版本称“查找可用 PDF”）。
- Connector 无法识别正式页面：优先用 DOI“按标识符添加”。
- 无 DOI 或按标识符添加失败：仅为该论文生成单篇 RIS。
- 发现重复父条目：暂停该论文后续操作，通过 Zotero“合并条目”处理，不直接删除。
- 页面需要登录、验证码或付费权限：停止自动操作，只记录缺失 PDF；不绕过访问限制。

## 约束

- 不直接修改 `zotero.sqlite` 或 Zotero `storage`。
- 不通过 Zotero Connector 保存裸 PDF 页面到已存在元数据的文献。
- 不批量生成全库 RIS；RIS 只包含 Connector 和 DOI 路径均失败的条目。
- 浏览器串行处理论文，避免保存弹窗和目标条目错配。

## 验收

每篇候选论文必须满足：

- Zotero 中只有一个父条目；
- DOI 或规范化标题与候选记录匹配；
- 可获得的 PDF 位于父条目下面；
- PaperLab 同步结果为 `ready`，且 `duplicate_keys` 为空；
- 失败项有明确原因和下一步，不被误报为已完成。

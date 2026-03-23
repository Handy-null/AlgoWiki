# 补题链接与 Issue 可见性上线说明

本文档用于说明这次新增功能在服务器上的上线步骤。由于当前 Codex 无法直接操作你的服务器，这些步骤需要你在服务器或部署环境中手动执行。

## 本次新增内容

- 赛事专区新增子页面：`补题链接`
- 补题链接支持：
  - 公开列表展示
  - 按 `年份 / ICPC|CCPC / 网络赛|区域赛|邀请赛|省赛` 筛选
  - 登录用户提交新增或修改申请
  - 管理员审核通过后写入正式表格
- Issue 新增可见性字段：
  - `public`：公开
  - `private`：个人，仅作者和管理员可见
- 个人中心 Issue 页面新增：
  - 创建时选择 `个人 / 公开`
  - 列表筛选 `我的 / 全部`
  - 列表筛选 `个人 / 公开`

## 已提交到仓库的数据文件

- 补题链接快照文件：
  - `backend/data/competition_practice_links_snapshot.json`

这个快照已经根据以下三个 markdown 数据源生成：

- `01 - 省赛与邀请赛.md`
- `02 - ICPC.md`
- `03 - CCPC.md`

当前生成结果为 `231` 条记录。

## 数据库迁移

先进入项目根目录，然后执行：

```powershell
.\venv\Scripts\python.exe backend\manage.py migrate
```

这一步会创建：

- `CompetitionPracticeLink`
- `CompetitionPracticeLinkProposal`
- `IssueTicket.visibility`

说明：

- 旧的 Issue 会自动使用默认值 `public`
- 如果没有执行迁移，补题链接接口和 Issue 可见性功能都不会正常工作

## 导入补题链接数据

迁移完成后，执行：

```powershell
.\venv\Scripts\python.exe backend\manage.py import_competition_practice_links --snapshot backend\data\competition_practice_links_snapshot.json --replace-missing
```

说明：

- `--replace-missing` 会删除数据库中不在快照里的旧补题链接记录
- 如果你只想增量覆盖，不删旧记录，可以去掉 `--replace-missing`

## 如果你需要重新生成快照

只有当这三个 markdown 数据源更新后，才需要重新生成。

命令如下：

```powershell
.\venv\Scripts\python.exe backend\manage.py build_competition_practice_snapshot `
  --provincial "C:\Users\28119\Downloads\01 - 省赛与邀请赛.md" `
  --icpc "C:\Users\28119\Downloads\02 - ICPC.md" `
  --ccpc "C:\Users\28119\Downloads\03 - CCPC.md" `
  --output backend\data\competition_practice_links_snapshot.json
```

然后再次执行导入命令：

```powershell
.\venv\Scripts\python.exe backend\manage.py import_competition_practice_links --snapshot backend\data\competition_practice_links_snapshot.json --replace-missing
```

## 前端构建

如果你的部署方式是前后端分离并且需要重新构建前端，执行：

```powershell
cd frontend
npm run build
```

如果你使用的是 Docker 镜像部署，需要重新构建并发布镜像，再按你的现有流程更新容器。

## 上线后检查项

建议按下面顺序检查：

1. 打开赛事专区，确认出现 `补题链接` 子页面
2. 检查补题链接表格是否有数据
3. 检查筛选项：
   - 年份
   - ICPC / CCPC
   - 网络赛 / 区域赛 / 邀请赛 / 省赛
4. 用普通账号提交一条补题链接申请
5. 用管理员账号审核通过，确认表格实时更新
6. 用普通账号提交 `private` Issue
7. 用另一个普通账号确认看不到该 `private` Issue
8. 用管理员账号确认可以看到该 `private` Issue
9. 在个人中心确认 `我的 / 全部` 和 `个人 / 公开` 筛选正常

## 相关接口

新增/变更的主要接口如下：

- `GET /api/competition-practice-links/`
- `GET /api/competition-practice-links/taxonomy/`
- `GET /api/competition-practice-proposals/`
- `POST /api/competition-practice-proposals/`
- `POST /api/competition-practice-proposals/<id>/approve/`
- `POST /api/competition-practice-proposals/<id>/reject/`
- `GET /api/issues/`
- `POST /api/issues/`

其中 Issue 现在支持参数：

- `visibility=private|public`
- `mine=1`

## 本地已验证

本地已完成：

- Django `check`
- 目标后端测试
- 前端 `vite build`

如果服务器环境和本地环境有差异，以上命令仍建议在服务器环境再执行一遍验证。

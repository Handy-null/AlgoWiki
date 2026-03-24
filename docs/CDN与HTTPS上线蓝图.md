# AlgoWiki CDN 与 HTTPS 上线蓝图

本文档面向当前线上架构：

- 源码仓库：`https://github.com/NullResot/AlgoWiki`
- 镜像来源：`ghcr.io/nullresot/algowiki-web`
- 应用运行方式：`Nginx -> Docker 容器内 Django/Gunicorn`
- 当前目标排序：
  1. 先防天价账单
  2. 再保稳定
  3. 最后才追求更强加速

## 1. 最终推荐架构

第一阶段采用极保守方案：

- `https://www.algowiki.cn` 作为唯一公开入口
- `https://algowiki.cn` 永久 `301` 到 `https://www.algowiki.cn`
- 只给 `www.algowiki.cn` 接入阿里云 CDN
- CDN 回源协议使用 `HTTPS`
- CDN 只缓存静态资源
- API、后台和 HTML 壳页面不做强缓存
- 暂不把用户上传接到 OSS

结构如下：

```text
访客
  |
  v
阿里云 CDN (www.algowiki.cn)
  |
  v
Nginx (ECS, HTTPS)
  |
  v
Docker / Django / Gunicorn
```

`algowiki.cn` 不接入 CDN，只在 ECS 上做 `301` 跳转。

## 2. 为什么要这样配

项目当前的静态与路由行为如下：

- Django 静态目录是 `/static/`
- 媒体目录默认是 `/media/`
- `api/admin/static/media` 之外的路径都会回前端 `index.html`
- 前端的可长期缓存文件会返回 `Cache-Control: public, max-age=31536000, immutable`
- `index.html` 和非永久资源会返回 `Cache-Control: no-cache, no-store, must-revalidate`
- Markdown 中的相对 `assets/...` 会被转换为 `/wiki-assets/...`

因此 CDN 不能按“整站缓存”来做，只能精确缓存真正静态的路径。

## 3. 仓库内已经准备好的内容

本仓库已经补好这些文件，供服务器与文档直接使用：

- Nginx 示例：[`deploy/nginx.algowiki.conf`](../deploy/nginx.algowiki.conf)
- 生产环境示例：[`deploy/env.production.example`](../deploy/env.production.example)
- 巡检脚本：[`deploy/server-verify.sh`](../deploy/server-verify.sh)

`deploy/nginx.algowiki.conf` 已经按下面的原则改好：

- `80 -> 443`
- `example.com -> https://www.example.com`
- `www.example.com` 才真正反代到 `127.0.0.1:8001`
- 反代时显式透传 `X-Forwarded-Proto=https`

## 4. 阿里云控制台需要你手动完成的事情

这些步骤我不能替你在阿里云控制台里点击，但已经帮你把配置边界定死了。

### 4.1 DNS 与域名分工

建议这样分工：

- `algowiki.cn`
  - 解析到 ECS 公网 IP
  - 由 ECS 上的 Nginx 负责 `301` 到 `https://www.algowiki.cn`
- `www.algowiki.cn`
  - 接入阿里云 CDN
  - DNS 上配置成 CNAME 到阿里云 CDN 分配的加速域名

### 4.2 CDN 域名添加

在阿里云 CDN 控制台新增加速域名时：

- 加速域名：`www.algowiki.cn`
- 业务类型：网页/小文件下载
- 源站类型：源站域名或 IP
- 回源地址：你的 ECS 公网域名或公网 IP
- 回源 Host：`www.algowiki.cn`
- 回源协议：`HTTPS`
- 回源端口：`443`

不要把 `algowiki.cn` 也一并做成同级加速入口。

### 4.3 缓存规则

第一阶段只配这几类：

- `/assets/*`：缓存 `30 天`
- `/static/*`：缓存 `30 天`
- `/wiki-assets/*`：缓存 `30 天`
- `/media/*`：第一阶段不缓存
- 其它请求：遵循源站缓存头

重要约束：

- 不要开启“忽略源站不缓存标头”
- 不要手动给 HTML 做长缓存
- 不要对整站设置统一缓存 TTL

### 4.4 必须不缓存的路径

这些路径必须回源：

- `/api/*`
- `/admin/*`

说明：

- `/manage/*`、`/review/*`、`/profile/*` 等前端路由最终都会回 `index.html`
- 项目代码已经给 `index.html` 配成 `no-cache, no-store, must-revalidate`
- 只要 CDN 不去强行覆盖源站缓存头，这些路由就不会被错误长缓存

### 4.5 止损与预警

必须同时开：

- CDN 用量封顶
- 高额消费预警
- 成本预警
- 预算管理

配置原则：

- 预警阈值设低一点，负责提前通知
- 封顶阈值设高一点，负责最后止损

不要只开资源包，不开封顶和预警。资源包只能降单价，不能防爆账单。

## 5. 服务器上需要做的事情

在你正式切 CDN 前，服务器需要满足这几项：

1. `www.algowiki.cn` 与 `algowiki.cn` 的证书都已经签好
2. Nginx 已切到仓库里的新模板逻辑
3. `deploy/.env.production` 已启用 HTTPS 相关变量
4. 源站本身已经能稳定返回：
   - `https://www.algowiki.cn`
   - `https://www.algowiki.cn/api/health/`

当前推荐的关键环境变量如下：

```env
DJANGO_ALLOWED_HOSTS=algowiki.cn,www.algowiki.cn,127.0.0.1,localhost
DJANGO_CSRF_TRUSTED_ORIGINS=https://algowiki.cn,https://www.algowiki.cn
DJANGO_USE_X_FORWARDED_HOST=1
DJANGO_USE_X_FORWARDED_PORT=1
DJANGO_SECURE_PROXY_SSL_HEADER=HTTP_X_FORWARDED_PROTO,https
SECURE_SSL_REDIRECT=1
SECURE_HSTS_SECONDS=31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS=1
SECURE_HSTS_PRELOAD=1
SESSION_COOKIE_SECURE=1
CSRF_COOKIE_SECURE=1
```

## 6. 切换前后怎么验证

### 6.1 本机源站验证

服务器上执行：

```bash
cd /srv/algowiki
curl -I https://algowiki.cn
curl -I https://www.algowiki.cn
curl -fsS https://www.algowiki.cn/api/health/
curl -fsS -H 'X-Forwarded-Proto: https' http://127.0.0.1:8001/api/health/
```

### 6.2 使用巡检脚本

可以在服务器环境文件里补两行：

```env
PUBLIC_SITE_URL=https://www.algowiki.cn
PUBLIC_APEX_URL=https://algowiki.cn
```

然后执行：

```bash
cd /srv/algowiki
./deploy/server-verify.sh
```

脚本会额外检查：

- 本机 `127.0.0.1` 健康检查
- `https://www.algowiki.cn`
- `https://www.algowiki.cn/api/health/`
- `https://algowiki.cn` 的跳转响应头

## 7. 第一阶段不要做的事

为了优先压住账单与风险，先不要做：

- 不要上 OSS 用户上传
- 不要把 `/media/*` 放进长缓存
- 不要做“全站缓存”
- 不要一开始就上 DCDN / ESA / WAF 的全家桶
- 不要把 `algowiki.cn` 和 `www.algowiki.cn` 都当成正式入口

## 8. 第二阶段再考虑的增强项

等第一阶段稳定后，再评估：

- `/media/*` 短缓存
- Referer 防盗链
- URL 鉴权
- 对象存储托管公共静态资源
- 更高带宽或更大内存规格

## 9. 官方文档

- 阿里云 CDN 用量封顶：https://help.aliyun.com/zh/cdn/user-guide/configure-bandwidth-caps
- 阿里云 CDN 高额消费预警：https://help.aliyun.com/zh/cdn/product-overview/configure-high-bill-alerts
- 阿里云 费用与成本预警：https://help.aliyun.com/zh/user-center/user-guide/cost-alert
- 阿里云 预算管理开通说明：https://help.aliyun.com/zh/user-center/user-guide/opening-management
- 阿里云 CDN 缓存过期时间配置：https://help.aliyun.com/zh/cdn/user-guide/configure-the-cdn-cache-expiration-time
- 阿里云 CDN 访问控制概览：https://help.aliyun.com/zh/cdn/user-guide/access-control-overview

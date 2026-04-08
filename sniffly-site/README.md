# Sniffly Site

这是 sniffly.dev 的静态站点，用于托管公开分享的 Sniffly 仪表盘和公共 Gallery。

## 目录结构

```
sniffly-site/
├── index.html              # 落地页 + 公共 Gallery
├── admin.html              # Admin 管理后台
├── share-template.html     # 分享仪表盘模板
├── share.html              # 由 build.py 从模板构建生成
├── build.py                # 构建脚本：打包 sniffly 静态资源
├── package.json            # Node.js 配置（便捷脚本）
│
├── static/                 # 静态资源
│   ├── css/
│   │   ├── style.css       # 主站和 Gallery 样式
│   │   └── admin.css       # Admin 管理后台样式
│   └── js/
│       ├── gallery.js      # Gallery 功能
│       ├── share-viewer.js # 渲染分享仪表盘
│       └── admin.js        # Admin 管理后台功能
│
├── functions/              # Cloudflare Pages Functions
│   └── share/
│       └── [[id]].js       # 动态路由：处理 /share/{id} 请求
│
└── 本地开发服务器（仅用于本地测试）：
    ├── gallery-site-server.py     # 类生产环境服务器
    ├── local-dev-gallery-server.py # Gallery 开发服务器
    └── local-dev-share-server.py   # 分享查看器开发服务器
```

## 工作原理

### 1. 构建过程

Cloudflare Pages 构建时，`build.py` 执行以下操作：

- 从 `sniffly/static/css/dashboard.css` 导入 CSS
- 从 `sniffly/static/js/` 导入 JS 模块（constants, utils, stats, charts 等）
- 将所有资源打包进自包含的 `share.html`
- 这样分享的仪表盘可以独立运行，无需依赖主 Sniffly 服务器

### 2. 分享查看

当用户访问 `sniffly.dev/share/abc123` 时：

1. Cloudflare Pages Function (`functions/share/[[id]].js`) 拦截请求
2. 从 R2 Storage 获取分享数据 `{share-id}.json`
3. 将数据注入 `share.html`
4. 返回完整的、可交互的仪表盘页面

### 3. 公共 Gallery

首页 (`index.html`) 展示：

- 精选分享项目
- 所有公开分享的仪表盘
- 项目统计信息（命令数、Token 消耗时长、成本等）
- 从 R2 的 `/gallery-index.json` 获取数据

### 4. Admin 管理后台

Admin 界面 (`admin.html`) 允许授权用户：

- 查看所有分享项目
- 精选/取消精选项目
- 删除不当内容
- 查看分享统计
- 使用 Google OAuth 进行身份认证

## 本地开发

### 测试 Gallery 和首页

```bash
python local-dev-gallery-server.py
# 访问 http://localhost:8000
```

### 测试分享查看

```bash
python local-dev-share-server.py
# 访问 http://localhost:4001/share/{id}
```

### 类生产环境测试

```bash
# 模拟 Cloudflare Pages 环境，同时服务 Gallery（8000端口）和分享（4001端口）
python gallery-site-server.py
```

## 部署

### Cloudflare Pages 配置

1. **连接 GitHub 仓库**

2. **构建设置：**
   ```
   构建命令: cd sniffly-site && python build.py
   构建输出目录: sniffly-site
   ```

3. **环境变量：**
   ```
   ENV=PROD
   R2_ACCESS_KEY_ID=your-key
   R2_SECRET_ACCESS_KEY=your-secret
   R2_BUCKET_NAME=sniffly-shares
   R2_ENDPOINT=https://your-account.r2.cloudflarestorage.com
   GA_MEASUREMENT_ID=G-XXXXXXXXXX
   GOOGLE_CLIENT_ID=your-oauth-client-id
   GOOGLE_CLIENT_SECRET=your-oauth-secret
   ADMIN_EMAILS=admin@example.com,other@example.com
   ```

4. **Functions 配置：**
   - Functions 目录：`functions`
   - `[[id]].js` 函数处理动态分享路由

### R2 Bucket 设置

1. 创建名为 `sniffly-shares` 的 Bucket
2. 分享数据存储为 `{share-id}.json`
3. Gallery 索引存储为 `gallery-index.json`
4. 分享日志存储为 `shares-log.jsonl`

## 数据结构

### 分享数据 (`{share-id}.json`)

```json
{
  "share_id": "abc123",
  "project_name": "my-project",
  "created_at": "2024-01-01T00:00:00Z",
  "is_public": false,
  "stats": { ... },
  "user_commands": [ ... ],
  "charts": { ... }
}
```

### Gallery 索引 (`gallery-index.json`)

```json
{
  "projects": [
    {
      "share_id": "abc123",
      "project_name": "my-project",
      "is_featured": true,
      "created_at": "2024-01-01T00:00:00Z",
      "stats": { ... }
    }
  ]
}
```

## 安全

- 分享数据经过清理，移除敏感路径
- Admin 访问需要 Google OAuth + 邮箱白名单
- 分享 ID 使用 24 字符 UUID 确保唯一性
- 日志中的 IP 地址经过 SHA256 哈希处理以保护隐私

## 技术栈

- **前端**: HTML + CSS + Vanilla JS（无框架依赖）
- **后端**: Cloudflare Pages Functions（Edge Runtime）
- **存储**: Cloudflare R2 Storage（S3 兼容 API）
- **认证**: Google OAuth
- **分析**: Google Analytics

## 注意事项

- Python 开发服务器仅用于本地测试
- 生产环境由 Cloudflare Pages 提供所有静态文件服务
- 构建过程确保分享查看器可独立工作
- Gallery 在创建新分享时自动更新

# 谜题收藏 API 文档

## 服务信息

| 项目 | 说明 |
|------|------|
| 基础地址 | `http://<server_ip>:5001/api` |
| 数据格式 | JSON |
| 字符编码 | UTF-8 |

## 认证

远程访问需要 API Key，局域网（`127.0.0.1`、`192.168.x.x`）自动免认证。

两种传递方式（二选一）：

```
# Header 方式
X-API-Key: <your_key>

# Query 方式
GET /api/entries?api_key=<your_key>
```

API Key 通过 Web 管理页面 `/api/keys` 创建。

**错误响应：**

```json
// 401 - 未提供 Key
{"error": "API key is required"}

// 401 - Key 无效
{"error": "Invalid or inactive API key"}
```

## 数据分类

| category | 中文名 | 说明 |
|----------|--------|------|
| `riddle` | 谜语 | 传统谜语 |
| `brain_teaser` | 脑筋急转弯 | 趣味问答 |
| `trivia` | 知识问答 | 百科知识 |
| `word_puzzle` | 字谜 | 汉字谜语 |
| `idiom` | 成语 | 成语释义和接龙 |
| `joke` | 笑话 | 趣味笑话 |

---

## 接口列表

### 1. 获取随机条目

适合首页展示、每日推荐等场景。

```
GET /api/random/{count}
```

**参数：**

| 参数 | 位置 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `count` | URL | 是 | int | 返回条数 |
| `category` | Query | 否 | string | 按分类筛选 |
| `source` | Query | 否 | string | 去重标识（见下方说明） |

**请求示例：**

```
GET /api/random/5?category=riddle&source=home_feed
```

**响应（200）：**

```json
[
  {
    "id": 42,
    "question": "什么东西有头无脚？",
    "answer": "砖",
    "category": "riddle",
    "created_at": "2025-03-15T10:30:00"
  }
]
```

**`source` 去重机制：**

传入相同 `source` 值后，服务端通过 session cookie 记录已返回的条目 ID，后续请求自动排除已看过的。当剩余条目不足 `count` 条时自动重置。

> 手机端需持久化 cookie（或自行在客户端做去重）。

---

### 2. 分页查询条目

适合列表浏览、搜索结果展示等场景。

```
GET /api/entries
```

**参数：**

| 参数 | 位置 | 必填 | 类型 | 说明 |
|------|------|------|------|------|
| `category` | Query | 否 | string | 按分类筛选 |
| `q` | Query | 否 | string | 搜索关键词（匹配问题和答案） |
| `page` | Query | 否 | int | 页码，默认 `1` |
| `per_page` | Query | 否 | int | 每页条数，默认 `20`，最大 `100` |

**请求示例：**

```
# 浏览谜语第2页
GET /api/entries?category=riddle&page=2&per_page=20

# 搜索关键词
GET /api/entries?q=月亮&category=riddle

# 全分类搜索
GET /api/entries?q=月亮
```

**响应（200）：**

```json
{
  "items": [
    {
      "id": 42,
      "question": "什么东西有头无脚？",
      "answer": "砖",
      "category": "riddle",
      "created_at": "2025-03-15T10:30:00"
    }
  ],
  "total": 50362,
  "page": 1,
  "per_page": 20,
  "pages": 2519,
  "has_next": true,
  "has_prev": false
}
```

**分页字段说明：**

| 字段 | 类型 | 说明 |
|------|------|------|
| `items` | array | 当前页条目列表 |
| `total` | int | 符合条件的总条目数 |
| `page` | int | 当前页码 |
| `per_page` | int | 每页条数 |
| `pages` | int | 总页数 |
| `has_next` | bool | 是否有下一页 |
| `has_prev` | bool | 是否有上一页 |

---

### 3. 获取分类列表

获取所有分类及各分类的条目数量，适合分类选择页面。

```
GET /api/categories
```

**无参数。**

**响应（200）：**

```json
{
  "categories": [
    {"name": "riddle", "count": 50362},
    {"name": "brain_teaser", "count": 10007},
    {"name": "trivia", "count": 10338},
    {"name": "word_puzzle", "count": 10007},
    {"name": "idiom", "count": 6},
    {"name": "joke", "count": 5}
  ],
  "total": 80725
}
```

---

### 4. 批量添加条目

```
POST /api/add
Content-Type: application/json
```

**请求体（JSON 数组）：**

```json
[
  {
    "question": "什么东西越洗越脏？",
    "answer": "水",
    "category": "riddle"
  },
  {
    "question": "什么路不能走？",
    "answer": "电路",
    "category": "brain_teaser"
  }
]
```

**响应（201）：**

```json
{
  "success": [
    {
      "id": 100,
      "question": "什么东西越洗越脏？",
      "answer": "水",
      "category": "riddle",
      "created_at": "2025-03-15T10:30:00"
    }
  ],
  "failed": [
    {
      "entry": {"question": "", "answer": "空", "category": "riddle"},
      "reason": "Question and answer cannot be empty"
    }
  ],
  "duplicates": [
    {
      "entry": {"question": "已有的问题", "answer": "已有的答案", "category": "riddle"},
      "existing_id": 42
    }
  ]
}
```

**去重规则：** 通过 MD5(`"{question}|{answer}"`) 跨分类去重。相同问答对即使 category 不同也视为重复。

---

## 条目数据结构

所有接口返回的条目结构一致：

```json
{
  "id": 42,
  "question": "问题内容",
  "answer": "答案内容",
  "category": "riddle",
  "created_at": "2025-03-15T10:30:00"
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 唯一标识 |
| `question` | string | 问题 |
| `answer` | string | 答案 |
| `category` | string | 分类（见上方分类表） |
| `created_at` | string | 创建时间（ISO 8601） |

---

## 手机端接入指南

### 推荐使用方式

| 场景 | 推荐接口 |
|------|----------|
| 首页随机推荐 | `GET /api/random/10?source=home` |
| 分类选择页 | `GET /api/categories` |
| 分类浏览列表 | `GET /api/entries?category=riddle&page=1` |
| 搜索功能 | `GET /api/entries?q=关键词` |
| 分类内搜索 | `GET /api/entries?q=关键词&category=riddle` |
| 用户贡献内容 | `POST /api/add` |

### CORS 说明

当前服务端未配置 CORS。原生 HTTP 客户端（iOS URLSession / Android OkHttp / Flutter Dio）不受影响，可直接请求。仅 WebView 或浏览器环境需要 CORS 支持。

### 注意事项

- `per_page` 建议手机端设为 `20`，大列表可适当增大但不超过 `100`
- `source` 去重依赖 session cookie，原生客户端建议自行维护已读列表
- 所有文本内容为中文，需确保 UTF-8 编码

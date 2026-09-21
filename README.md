# ShadeCanopy-01 · 分区气候、轮灌与土壤含水抽检

温室「分区气候日志、轮灌计划与土壤含水抽检批次」全栈种子项目（非考勤 OA、非库存）。
A08 快照新增土壤含水抽检批次（批次挂温室、测点挂分区、封批与按温室对账）。

## 技术栈

| 层 | 技术 |
| --- | --- |
| 后端 | Python Django 5 · Django REST Framework · SimpleJWT · django-cors-headers · Gunicorn |
| 前端 | Vue 3 · Vite · Pinia · Vue Router |
| 数据库 | PostgreSQL 15 |
| 部署 | Docker Compose · Nginx（前端容器反代 `/api` → Django） |

## 路径与端口

- **项目路径**：`D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01\`
- **前端**：http://localhost:3500
- **后端 API**：http://localhost:8500（也可经前端同源 `/api` 访问）
- **PostgreSQL**：localhost:5435

## 演示账号

| 用户名 | 密码 | 角色 |
| --- | --- | --- |
| `admin` | `123456` | admin（管理员，可进 Django Admin） |
| `grower` | `123456` | grower（种植员） |

启动时 `entrypoint.sh` 会执行 `migrate` + `seed_data` 自动写入账号与示例业务数据。
含水抽检种子（幂等，重复执行 `seed_data` 也会补齐）：两个示范温室各有一个**相同批次号** `SM-20260921-01`——东坡一号棚批次含 2 个测点**可封批**，西篱二号棚同号批次仅 1 个测点**不可封批**（调用封批返回 409）。

## 快速启动

```bash
cd D:\work\document\bytecode\claudeCodePro\ShadeCanopy\ShadeCanopy-01
docker compose up --build
```

浏览器打开 http://localhost:3500 ，使用 `grower` / `123456` 登录。

停止：

```bash
docker compose down
```

## 业务模块

1. **Auth**：JWT `POST /api/auth/token/`，当前用户 `GET /api/auth/me/`
2. **Greenhouse**：name / location / areaM2 / notes
3. **Zone**：greenhouseId / zoneCode / cropName / status(`idle|growing|fallow`)；同温室 zoneCode 唯一
4. **ClimateLog**：zoneId / recordedAt / tempC / humidityPct / parUmol / co2Ppm；**humidityPct ∈ [20, 100]**
5. **IrrigationCycle**：zoneId / startAt / durationMin / waterLiters / status(`scheduled|running|done|skipped`)
6. **MoistureBatch（土壤含水抽检批次，A08）**：greenhouseId / batchCode / openedOn / closedAt(可空)
   - 批次挂温室：**同温室批次号唯一，跨温室允许相同批次号但不得串棚**
   - `openedOn` 为开批日，按东八区（Asia/Shanghai）自然日
7. **MoistureSample（抽检测点）**：batchId / zoneId / moisturePct / sampledAt
   - 测点挂分区，**分区必须属于批次所属温室**，否则拒绝
   - **moisturePct 为 5～95 的整数**
   - **未封批次内同一分区只许一个测点**（`batchId+zoneId` 唯一）
   - **批次封批后禁止再加点**
   - 封批接口：箱内至少 2 个测点，否则返回 **409** 且 `closedAt` 保持为空
8. **对账（按温室）**：每个温室给出批次数、批次侧点数与明细实际计数，**差额 diff 须为 0**
9. **Dashboard**：温室数、growing 分区数、近 24h 气候日志数、今日 scheduled 轮灌数 → `GET /api/dashboard/`

## API 一览

| 方法 | 路径 |
| --- | --- |
| POST | `/api/auth/token/` |
| POST | `/api/auth/token/refresh/` |
| GET | `/api/auth/me/` |
| CRUD | `/api/greenhouses/` |
| CRUD | `/api/zones/?greenhouseId=&status=` |
| CRUD | `/api/climate-logs/?zoneId=` |
| CRUD | `/api/irrigation-cycles/?zoneId=&status=` |
| CRUD | `/api/moisture-batches/?greenhouseId=` |
| POST | `/api/moisture-batches/{id}/close/`（封批，不足 2 点 → 409） |
| CRUD | `/api/moisture-samples/?batchId=&zoneId=` |
| GET | `/api/moisture-reconciliation/?greenhouseId=`（按温室对账，diff=0 才算平账） |
| GET | `/api/dashboard/` |

字段对外使用 camelCase（如 `areaM2`、`zoneCode`、`humidityPct`）。

## 本地开发（可选）

**后端**（需本机 Postgres 或已启动 compose 中的 db）：

```bash
cd backend
pip install -r requirements.txt
set POSTGRES_HOST=127.0.0.1
set POSTGRES_PORT=5435
python manage.py migrate
python manage.py seed_data
python manage.py runserver 0.0.0.0:8500
```

**前端**：

```bash
cd frontend
npm install
npm run dev
```

Vite 已将 `/api` 代理到 `http://127.0.0.1:8500`。

## 目录结构

```
ShadeCanopy-01/
├── docker-compose.yml
├── README.md
├── .gitignore
├── backend/
│   ├── Dockerfile
│   ├── entrypoint.sh      # migrate + seed + gunicorn
│   ├── requirements.txt
│   ├── manage.py
│   ├── config/            # settings / urls
│   ├── accounts/          # 自定义 User + role
│   └── core/              # 温室/分区/气候/轮灌 + seed_data
└── frontend/
    ├── Dockerfile
    ├── nginx.conf         # 静态资源 + /api 反代
    ├── package.json
    └── src/               # Vue 页面（叶绿/土色主题）
```

## 配色说明

前端采用叶绿（`#3d6b3a`）与土色（`#8b6b45`）主色，米色底与侧栏深绿渐变，贴近温室场景。

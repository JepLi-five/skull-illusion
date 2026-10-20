-- 骷髅幻戏私有平台 · SQLite schema
-- 客户端 / 知识库 / 自动化 / 线索 / 四部门流水线 / 互动
-- 注意：客户主表(主表_当前.xlsx)只读，本库为其增强副本，绝不回写。

PRAGMA foreign_keys = ON;

-- 客户（增强副本，来源主表只读导入）
CREATE TABLE IF NOT EXISTS clients (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    province    TEXT,
    industry    TEXT,
    contact     TEXT,
    phone       TEXT,
    priority    TEXT,        -- P0/P1/P2/P3
    score       REAL,
    source      TEXT,
    created_at  TEXT DEFAULT (datetime('now')),
    updated_at  TEXT DEFAULT (datetime('now'))
);

-- 知识库（私有大脑）
CREATE TABLE IF NOT EXISTS knowledge (
    id          INTEGER PRIMARY KEY,
    title       TEXT,
    body        TEXT,
    tags        TEXT,
    source      TEXT,
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 自动化任务
CREATE TABLE IF NOT EXISTS automations (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    schedule    TEXT,        -- cron / 描述
    status      TEXT,        -- active/paused
    last_run_at TEXT,
    note        TEXT
);

-- 线索（获客入口：外部门户 / 抓取 / 手动）
CREATE TABLE IF NOT EXISTS leads (
    id          INTEGER PRIMARY KEY,
    name        TEXT,
    contact     TEXT,
    intent      TEXT,
    source      TEXT,        -- web/wechat/scrape/manual
    status      TEXT DEFAULT 'new',
    created_at  TEXT DEFAULT (datetime('now'))
);

-- 四部门流水线（获客→转化→交付→沉淀）
CREATE TABLE IF NOT EXISTS pipeline (
    id          INTEGER PRIMARY KEY,
    lead_id     INTEGER,
    stage       TEXT,        -- acquire/convert/deliver/deposit
    owner       TEXT,
    entered_at  TEXT DEFAULT (datetime('now')),
    due_at      TEXT,
    notes       TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

-- 客户互动记录
CREATE TABLE IF NOT EXISTS interactions (
    id          INTEGER PRIMARY KEY,
    client_id   INTEGER,
    channel     TEXT,        -- wechat/phone/visit
    summary     TEXT,
    at          TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (client_id) REFERENCES clients(id)
);

CREATE INDEX IF NOT EXISTS idx_clients_priority ON clients(priority);
CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_pipeline_stage ON pipeline(stage);

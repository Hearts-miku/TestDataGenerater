// 社交网络图：节点 + 多种关系类型
// 用于验证图 Schema 解析、生成顺序与引用完整性

// ── 节点定义 ──
// (:User {id: INT, username: STRING, email: STRING, bio: STRING, created_at: DATETIME})
// (:Post {id: INT, content: STRING, published_at: DATETIME, likes: INT})
// (:Tag  {id: INT, name: STRING})

// ── 关系定义 ──
// (:User)-[:FOLLOWS {since: DATE}]->(:User)
// (:User)-[:AUTHORED]->(:Post)
// (:User)-[:LIKED]->(:Post)
// (:Post)-[:TAGGED_WITH]->(:Tag)

// 约束
CREATE CONSTRAINT ON (u:User) ASSERT u.id IS UNIQUE;
CREATE CONSTRAINT ON (p:Post) ASSERT p.id IS UNIQUE;
CREATE CONSTRAINT ON (t:Tag)  ASSERT t.name IS UNIQUE;

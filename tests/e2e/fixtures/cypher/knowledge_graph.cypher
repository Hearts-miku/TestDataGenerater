// 知识图谱：多跳关系、自引用、属性丰富
// 用于验证复杂图结构生成

// ── 节点 ──
// (:Company  {id: INT, name: STRING, industry: STRING, founded_year: INT})
// (:Person   {id: INT, name: STRING, title: STRING, email: STRING})
// (:Product  {id: INT, name: STRING, version: STRING, release_date: DATE})
// (:Location {id: INT, city: STRING, country: STRING})

// ── 关系 ──
// (:Person)-[:WORKS_AT {start_date: DATE, position: STRING}]->(:Company)
// (:Company)-[:LOCATED_IN]->(:Location)
// (:Company)-[:PRODUCES]->(:Product)
// (:Person)-[:MANAGES]->(:Person)           // 自引用（经理→下属）
// (:Company)-[:PARTNERS_WITH]->(:Company)   // 公司间合作

CREATE CONSTRAINT ON (c:Company)  ASSERT c.id IS UNIQUE;
CREATE CONSTRAINT ON (p:Person)   ASSERT p.id IS UNIQUE;
CREATE CONSTRAINT ON (pr:Product) ASSERT pr.id IS UNIQUE;
CREATE CONSTRAINT ON (l:Location) ASSERT l.id IS UNIQUE;

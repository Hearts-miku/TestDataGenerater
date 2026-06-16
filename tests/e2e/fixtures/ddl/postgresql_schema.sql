-- PostgreSQL 方言：验证多方言解析
CREATE TABLE departments (
    id         SERIAL       PRIMARY KEY,
    name       VARCHAR(100) NOT NULL UNIQUE,
    budget     NUMERIC(15, 2)
);

CREATE TABLE employees (
    id            SERIAL        PRIMARY KEY,
    department_id INTEGER       NOT NULL REFERENCES departments(id),
    first_name    VARCHAR(50)   NOT NULL,
    last_name     VARCHAR(50)   NOT NULL,
    email         VARCHAR(120)  NOT NULL UNIQUE,
    salary        NUMERIC(12, 2),
    hire_date     DATE          NOT NULL DEFAULT CURRENT_DATE,
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE
);

CREATE TABLE projects (
    id          SERIAL       PRIMARY KEY,
    name        VARCHAR(200) NOT NULL,
    start_date  DATE,
    end_date    DATE,
    lead_emp_id INTEGER      REFERENCES employees(id)
);

CREATE TABLE employee_projects (
    employee_id INT NOT NULL REFERENCES employees(id),
    project_id  INT NOT NULL REFERENCES projects(id),
    role        VARCHAR(80),
    PRIMARY KEY (employee_id, project_id)
);

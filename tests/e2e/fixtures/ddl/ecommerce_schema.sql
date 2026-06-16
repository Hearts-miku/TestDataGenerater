-- 多表电商场景：验证外键约束、拓扑排序生成顺序
CREATE TABLE categories (
    id          INT          NOT NULL AUTO_INCREMENT,
    name        VARCHAR(80)  NOT NULL UNIQUE,
    description TEXT,
    PRIMARY KEY (id)
);

CREATE TABLE products (
    id           INT            NOT NULL AUTO_INCREMENT,
    category_id  INT            NOT NULL,
    name         VARCHAR(200)   NOT NULL,
    price        DECIMAL(10, 2) NOT NULL,
    stock        INT            NOT NULL DEFAULT 0,
    sku          VARCHAR(64)    NOT NULL UNIQUE,
    PRIMARY KEY (id),
    FOREIGN KEY (category_id) REFERENCES categories(id)
);

CREATE TABLE users (
    id         INT          NOT NULL AUTO_INCREMENT,
    email      VARCHAR(120) NOT NULL UNIQUE,
    username   VARCHAR(50)  NOT NULL UNIQUE,
    phone      VARCHAR(20),
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id)
);

CREATE TABLE orders (
    id           INT          NOT NULL AUTO_INCREMENT,
    user_id      INT          NOT NULL,
    status       ENUM('pending', 'paid', 'shipped', 'completed', 'cancelled')
                              NOT NULL DEFAULT 'pending',
    total_amount DECIMAL(12, 2) NOT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    FOREIGN KEY (user_id) REFERENCES users(id)
);

CREATE TABLE order_items (
    id         INT            NOT NULL AUTO_INCREMENT,
    order_id   INT            NOT NULL,
    product_id INT            NOT NULL,
    quantity   INT            NOT NULL DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    PRIMARY KEY (id),
    FOREIGN KEY (order_id)   REFERENCES orders(id),
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- RCLP_DATA.CST_LABEL_INFO_ALL definition

CREATE TABLE `CST_LABEL_INFO_ALL` (
          `label_no` varchar(10) NULL COMMENT "标签编号",
          `cust_no` varchar(20) NULL COMMENT "客户编号",
          `uniq_key` varchar(300) NULL COMMENT "客户唯一键",
          `update_tm` varchar(90) NULL COMMENT "更新时间",
          `updtr_no` varchar(180) NULL COMMENT "更新人编号",
          `etl_dt` date NULL COMMENT "数据日期",
          `batch_no` varchar(90) NULL COMMENT "批次编号",
          INDEX label_no_index (`label_no`) USING BITMAP COMMENT ''
        ) ENGINE=OLAP
        DUPLICATE KEY(`label_no`)
        COMMENT "客户标签全量信息"
        PARTITION BY RANGE(`etl_dt`)
        (PARTITION p20231231 VALUES [("2023-12-31"), ("2024-01-01")),
        PARTITION p20240801 VALUES [("2024-08-01"), ("2024-08-02")),
        PARTITION p20240802 VALUES [("2024-08-02"), ("2024-08-03")),
        PARTITION p20240930 VALUES [("2024-09-30"), ("2024-10-01")),
        PARTITION p20260331 VALUES [("2026-03-31"), ("2026-04-01")))
        DISTRIBUTED BY HASH(`cust_no`) BUCKETS 12
        PROPERTIES (
        "bloom_filter_columns" = "label_no",
        "colocate_with" = "rclp_group_1",
        "compression" = "LZ4",
        "fast_schema_evolution" = "true",
        "replicated_storage" = "true",
        "replication_num" = "3"
        );

-- RCLP_DATA.LBL_VAL_LIST definition

CREATE TABLE `LBL_VAL_LIST` (
          `label_no` varchar(30) NULL COMMENT "标签编号",
          `update_tm` varchar(30) NULL COMMENT "更新时间",
          `create_tm` varchar(30) NULL COMMENT "创建时间",
          `updtr_no` varchar(60) NULL COMMENT "更新人编号",
          `update_org_no` varchar(80) NULL COMMENT "更新机构编号",
          `label_cls_no` varchar(60) NULL COMMENT "标签分类编号",
          `label_name` varchar(300) NULL COMMENT "标签名称",
          `label_desc` varchar(1000) NULL COMMENT "标签描述",
          `label_update_freq_cd` varchar(20) NULL COMMENT "标签更新频率代码",
          `label_status_cd` varchar(20) NULL COMMENT "标签状态代码",
          `label_src_cd` varchar(20) NULL COMMENT "标签来源代码",
          `label_visib_flag` varchar(10) NULL COMMENT "标签可见标志",
          `mnl_label_use_scope_cd` varchar(20) NULL COMMENT "人工标签使用范围代码",
          `label_invalid_tm` varchar(30) NULL COMMENT "标签失效时间",
          `label_biz_cali` varchar(3000) NULL COMMENT "标签业务口径",
          `cust_grp_cust_cnt` decimal(22, 0) NULL COMMENT "客户群客户数量",
          `cust_identify_cd` varchar(8) NULL COMMENT "客户标识代码",
          `update_way_cd` varchar(8) NULL COMMENT "更新方式代码",
          `lbl_ent_nm` varchar(100) NULL COMMENT "标签实体名称",
          `update_strategy_cd` varchar(20) NULL COMMENT "更新策略代码",
          `usage_cd_list` varchar(1000) NULL COMMENT "用途代码列表",
          `label_use_scope_cd` varchar(20) NULL COMMENT "标签使用范围代码",
          `label_aflt_brch_org_no_list` varchar(1000) NULL COMMENT "标签所属分支机构编号列表",
          `using_role_no_list` varchar(1000) NULL COMMENT "使用角色列表",
          `creatr_no` varchar(60) NULL COMMENT "创建人编号",
          `is_use_cd` varchar(20) NULL COMMENT "是否启用代码",
          `indv_cust_src_cd` varchar(20) NULL COMMENT "个人客户来源代码"
        ) ENGINE=OLAP
        DUPLICATE KEY(`label_no`)
        COMMENT "标签信息元数据表_STARK"
        DISTRIBUTED BY HASH(`label_no`) BUCKETS 1
        PROPERTIES (
        "bloom_filter_columns" = "label_no",
        "compression" = "LZ4",
        "fast_schema_evolution" = "true",
        "replicated_storage" = "true",
        "replication_num" = "3"
        );

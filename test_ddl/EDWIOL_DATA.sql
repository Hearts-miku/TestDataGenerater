-- EDWIOL_DATA.BRP_CUST_RELA_INFO_RBMS definition

CREATE TABLE `BRP_CUST_RELA_INFO_RBMS` (
  `party_id` varchar(60) NULL COMMENT "当事人标识",
  `source` varchar(24) NULL COMMENT "联系信息来源",
  `is_valid` varchar(24) NULL COMMENT "是否经验证有效",
  `is_default` varchar(24) NULL COMMENT "是否默认联系方式",
  `contact_mech_type_id` varchar(60) NULL COMMENT "联系机制类型编号",
  `info_string` varchar(765) NULL COMMENT "联系信息",
  `last_updated_stamp` datetime NULL COMMENT "最后更新时间",
  `last_updated_tx_stamp` datetime NULL COMMENT "最后更新事务时间",
  `created_stamp` datetime NULL COMMENT "创建时间",
  `created_tx_stamp` datetime NULL COMMENT "创建事务时间",
  `source_sort` varchar(30) NULL COMMENT "来源系统优先顺",
  `etl_timestamp` datetime NULL COMMENT "ETL时间戳",
  `start_dt` date NULL COMMENT "拉链开始时间",
  `end_dt` date NULL COMMENT "拉链结束时间",
  `id_mark` varchar(1) NULL COMMENT "增删标志"
) ENGINE=OLAP 
DUPLICATE KEY(`party_id`)
COMMENT "大零售客户联系信息表"
DISTRIBUTED BY HASH(`party_id`) BUCKETS 3 
PROPERTIES (
"compression" = "LZ4",
"fast_schema_evolution" = "true",
"replicated_storage" = "true",
"replication_num" = "3"
);


-- EDWIOL_DATA.CEI_TBDXASSETSHAREDETAIL1 definition

CREATE TABLE `CEI_TBDXASSETSHAREDETAIL1` (
  `serial_no` varchar(96) NULL COMMENT "交易流水编号",
  `cfm_no` varchar(96) NULL COMMENT "TA确认流水编号",
  `cfm_date` decimal(22, 0) NULL COMMENT "确认日期",
  `in_client_no` varchar(60) NULL COMMENT "商业养老金客户编号",
  `ta_code` varchar(54) NULL COMMENT "TA代码",
  `asset_acc` varchar(60) NULL COMMENT "商业养老金账号",
  `bank_no` varchar(96) NULL COMMENT "银行代码:租户编号(多租户模式用)",
  `seller_code` varchar(27) NULL COMMENT "销售商代码描述",
  `client_no` varchar(72) NULL COMMENT "客户编号",
  `bank_acc` varchar(192) NULL COMMENT "银行卡号",
  `ta_client` varchar(96) NULL COMMENT "商业养老金交易账号",
  `prd_code` varchar(96) NULL COMMENT "商业养老金产品编号",
  `ta_vol` decimal(18, 3) NULL COMMENT "TA份额",
  `ta_available_vol` decimal(18, 3) NULL COMMENT "TA可用份额",
  `ta_frozen_vol` decimal(18, 3) NULL COMMENT "TA冻结份额",
  `detail_flag` varchar(3) NULL COMMENT "明细标志",
  `frozen_vol` decimal(18, 3) NULL COMMENT "冻结份额",
  `long_frozen_vol` decimal(18, 3) NULL COMMENT "长期冻结份额",
  `pre_red_end_date` decimal(22, 0) NULL COMMENT "上一预计到期日",
  `allow_red_date` decimal(22, 0) NULL COMMENT "允许赎回日期",
  `branch_no` varchar(48) NULL COMMENT "分支机构编号",
  `share_class` varchar(9) NULL COMMENT "份额类别",
  `acc_status` varchar(3) NULL COMMENT "账户状态",
  `register_date` decimal(22, 0) NULL COMMENT "注册日期",
  `source_flag` varchar(3) NULL COMMENT "来源标志",
  `div_mode` varchar(3) NULL COMMENT "分红方式代码",
  `guaranteed_amount` decimal(16, 2) NULL COMMENT "监管金额",
  `table_num` varchar(30) NULL COMMENT "分表号",
  `reserve1` varchar(750) NULL COMMENT "保留字段1",
  `reserve2` varchar(750) NULL COMMENT "保留字段2",
  `amt1` decimal(18, 2) NULL COMMENT "备用金额1",
  `amt2` decimal(18, 2) NULL COMMENT "备用金额2",
  `integer1` decimal(22, 0) NULL COMMENT "保本到期日",
  `integer2` decimal(22, 0) NULL COMMENT "备用整型2",
  `etl_timestamp` datetime NULL COMMENT "ETL时间戳",
  `start_dt` date NULL COMMENT "拉链开始时间",
  `end_dt` date NULL COMMENT "拉链结束时间",
  `id_mark` varchar(1) NULL COMMENT "增删标志"
) ENGINE=OLAP 
DUPLICATE KEY(`serial_no`)
COMMENT "份额明细表"
DISTRIBUTED BY HASH(`cfm_no`, `cfm_date`, `ta_code`, `ta_client`, `prd_code`, `register_date`) BUCKETS 3 
PROPERTIES (
"compression" = "LZ4",
"fast_schema_evolution" = "true",
"replicated_storage" = "true",
"replication_num" = "3"
);


-- EDWIOL_DATA.GIS_GIS_POSITION_DETAIL definition

CREATE TABLE `GIS_GIS_POSITION_DETAIL` (
  `id` decimal(22, 0) NULL COMMENT "编号",
  `cac_date` varchar(24) NULL COMMENT "统计日期",
  `account_no` varchar(66) NULL COMMENT "积存金账号",
  `bancs_custno` varchar(36) NULL COMMENT "客户号",
  `card_no` varchar(57) NULL COMMENT "卡号",
  `position_type` varchar(36) NULL COMMENT "交易类型",
  `cust_bal` decimal(16, 4) NULL COMMENT "持仓份额",
  `cost_price` decimal(18, 2) NULL COMMENT "持仓成本均价",
  `market_amt` decimal(18, 2) NULL COMMENT "持仓市值",
  `bal_profit` decimal(18, 2) NULL COMMENT "持仓收益率",
  `close_price` decimal(18, 2) NULL COMMENT "最后一笔价格",
  `limit_time` varchar(30) NULL COMMENT "期限",
  `limit_unit` varchar(30) NULL COMMENT "期限单位",
  `trade_date` varchar(24) NULL COMMENT "交易日期",
  `exp_date` varchar(24) NULL COMMENT "到期日期",
  `issue_no` varchar(60) NULL COMMENT "产品代码",
  `issue_name` varchar(240) NULL COMMENT "产品名称",
  `market_teller` varchar(24) NULL COMMENT "推荐人工号",
  `bankid` varchar(15) NULL COMMENT "交易归属机构编号",
  `issue_rate` decimal(12, 2) NULL COMMENT "利率",
  `trade_no` varchar(66) NULL COMMENT "流水号",
  `remark1` varchar(300) NULL COMMENT "备用1",
  `etl_timestamp` datetime NULL COMMENT "ETL时间戳",
  `etl_dt` date NULL COMMENT "ETL数据日期"
) ENGINE=OLAP 
DUPLICATE KEY(`id`, `cac_date`)
COMMENT "客户持仓收益详情表"
DISTRIBUTED BY HASH(`id`) BUCKETS 3 
PROPERTIES (
"compression" = "LZ4",
"fast_schema_evolution" = "true",
"replicated_storage" = "true",
"replication_num" = "3"
);


-- EDWIOL_DATA.MED_INTERACTION_DIARY definition

CREATE TABLE `MED_INTERACTION_DIARY` (
  `userid` varchar(240) NULL COMMENT "客户编号",
  `event_dt` date NULL COMMENT "互动日期",
  `event_time` datetime NULL COMMENT "",
  `hdrj_type` varchar(240) NULL COMMENT "互动类型",
  `event` varchar(240) NULL COMMENT "互动行为",
  `event_params` varchar(6000) NULL COMMENT "互动详细参数",
  `event_summary` varchar(3000) NULL COMMENT "互动摘要",
  `batch_dt` date NULL COMMENT "跑批日期",
  `etl_timestamp` datetime NULL COMMENT "ETL时间戳",
  `etl_dt` date NULL COMMENT "ETL数据日期",
  `behav_tag` varchar(150) NULL COMMENT "行为标签",
  `behav_lvl` varchar(30) NULL COMMENT "行为等级"
) ENGINE=OLAP 
DUPLICATE KEY(`userid`)
COMMENT "零售客户互动日记表"
PARTITION BY RANGE(`etl_dt`)
(PARTITION p20250802 VALUES [("2025-08-02"), ("2025-08-03")),
PARTITION p20250913 VALUES [("2025-09-13"), ("2025-09-14")),
PARTITION p20250923 VALUES [("2025-09-23"), ("2025-09-24")),
PARTITION p20251231 VALUES [("2025-12-31"), ("2026-01-01")),
PARTITION p20260315 VALUES [("2026-03-15"), ("2026-03-16")),
PARTITION p20260331 VALUES [("2026-03-31"), ("2026-04-01")),
PARTITION p20260416 VALUES [("2026-04-16"), ("2026-04-17")),
PARTITION p20260426 VALUES [("2026-04-26"), ("2026-04-27")))
DISTRIBUTED BY HASH(`userid`) BUCKETS 3 
PROPERTIES (
"compression" = "LZ4",
"fast_schema_evolution" = "true",
"replicated_storage" = "true",
"replication_num" = "3"
);


-- EDWIOL_DATA.MFP_MIX_SMS_GATEWAY definition

CREATE TABLE `MFP_MIX_SMS_GATEWAY` (
  `id` decimal(22, 0) NULL COMMENT "主键",
  `user_id` decimal(22, 0) NULL COMMENT "操作员ID",
  `sa_name` varchar(150) NULL COMMENT "发送账号名称",
  `company_id` decimal(22, 0) NULL COMMENT "机构ID",
  `department_id` decimal(22, 0) NULL COMMENT "部门ID",
  `phone` decimal(22, 0) NULL COMMENT "手机号",
  `channel` decimal(22, 0) NULL COMMENT "通道号",
  `content` varchar(3150) NULL COMMENT "短信内容",
  `send_date` decimal(22, 0) NULL COMMENT "发送时间",
  `receive_date` decimal(22, 0) NULL COMMENT "接收时间",
  `platform_status` decimal(4, 0) NULL COMMENT "发送状态",
  `fee` decimal(4, 0) NULL COMMENT "计费条数",
  `group_id` decimal(22, 0) NULL COMMENT "内部序号",
  `user_ext_code` varchar(36) NULL COMMENT "账号扩展码",
  `send_ext_code` varchar(36) NULL COMMENT "发送扩展码",
  `platform_message_id` decimal(22, 0) NULL COMMENT "短信的MESSAGE_ID值",
  `user_message_id` varchar(192) NULL COMMENT "提交平台时候用户自定义的MESSID",
  `split_index` decimal(4, 0) NULL COMMENT "长短信拆分的序号",
  `submit_code` decimal(22, 0) NULL COMMENT "提交状态码，记录提交返回值",
  `status_type` decimal(22, 0) NULL COMMENT "状态类型",
  `service_id` varchar(1536) NULL COMMENT "批次号",
  `cmpp_msg_id` varchar(192) NULL COMMENT "运营商返的MSGID",
  `sign` varchar(90) NULL COMMENT "签名",
  `isp` decimal(4, 0) NULL COMMENT "手机号运营商",
  `province` decimal(4, 0) NULL COMMENT "省份",
  `extend_config` varchar(9000) NULL COMMENT "扩展JSON串",
  `gateway_id` varchar(192) NULL COMMENT "统一消息标识",
  `br_id` varchar(60) NULL COMMENT "机构ID2",
  `req_sys_id` varchar(33) NULL COMMENT "系统编号",
  `tlr_no` varchar(33) NULL COMMENT "柜员ID",
  `template_id` decimal(22, 0) NULL COMMENT "发送模板ID",
  `etl_timestamp` datetime NULL COMMENT "ETL时间戳",
  `etl_dt` date NULL COMMENT "ETL数据日期"
) ENGINE=OLAP 
DUPLICATE KEY(`id`, `user_id`)
COMMENT "网关记录表"
PARTITION BY RANGE(`etl_dt`)
(PARTITION p20260331 VALUES [("2026-03-31"), ("2026-04-01")),
PARTITION p20260401 VALUES [("2026-04-01"), ("2026-04-02")),
PARTITION p20260402 VALUES [("2026-04-02"), ("2026-04-03")),
PARTITION p20260403 VALUES [("2026-04-03"), ("2026-04-04")),
PARTITION p20260404 VALUES [("2026-04-04"), ("2026-04-05")),
PARTITION p20260405 VALUES [("2026-04-05"), ("2026-04-06")),
PARTITION p20260406 VALUES [("2026-04-06"), ("2026-04-07")),
PARTITION p20260407 VALUES [("2026-04-07"), ("2026-04-08")),
PARTITION p20260408 VALUES [("2026-04-08"), ("2026-04-09")),
PARTITION p20260409 VALUES [("2026-04-09"), ("2026-04-10")),
PARTITION p20260410 VALUES [("2026-04-10"), ("2026-04-11")),
PARTITION p20260411 VALUES [("2026-04-11"), ("2026-04-12")),
PARTITION p20260412 VALUES [("2026-04-12"), ("2026-04-13")),
PARTITION p20260413 VALUES [("2026-04-13"), ("2026-04-14")),
PARTITION p20260414 VALUES [("2026-04-14"), ("2026-04-15")),
PARTITION p20260415 VALUES [("2026-04-15"), ("2026-04-16")),
PARTITION p20260416 VALUES [("2026-04-16"), ("2026-04-17")),
PARTITION p20260417 VALUES [("2026-04-17"), ("2026-04-18")),
PARTITION p20260418 VALUES [("2026-04-18"), ("2026-04-19")),
PARTITION p20260419 VALUES [("2026-04-19"), ("2026-04-20")),
PARTITION p20260420 VALUES [("2026-04-20"), ("2026-04-21")),
PARTITION p20260421 VALUES [("2026-04-21"), ("2026-04-22")),
PARTITION p20260422 VALUES [("2026-04-22"), ("2026-04-23")),
PARTITION p20260423 VALUES [("2026-04-23"), ("2026-04-24")),
PARTITION p20260424 VALUES [("2026-04-24"), ("2026-04-25")),
PARTITION p20260425 VALUES [("2026-04-25"), ("2026-04-26")),
PARTITION p20260426 VALUES [("2026-04-26"), ("2026-04-27")),
PARTITION p20260427 VALUES [("2026-04-27"), ("2026-04-28")),
PARTITION p20260428 VALUES [("2026-04-28"), ("2026-04-29")),
PARTITION p20260429 VALUES [("2026-04-29"), ("2026-04-30")),
PARTITION p20260430 VALUES [("2026-04-30"), ("2026-05-01")),
PARTITION p20260501 VALUES [("2026-05-01"), ("2026-05-02")),
PARTITION p20260502 VALUES [("2026-05-02"), ("2026-05-03")),
PARTITION p20260503 VALUES [("2026-05-03"), ("2026-05-04")),
PARTITION p20260504 VALUES [("2026-05-04"), ("2026-05-05")),
PARTITION p20260505 VALUES [("2026-05-05"), ("2026-05-06")),
PARTITION p20260506 VALUES [("2026-05-06"), ("2026-05-07")),
PARTITION p20260507 VALUES [("2026-05-07"), ("2026-05-08")),
PARTITION p20260508 VALUES [("2026-05-08"), ("2026-05-09")),
PARTITION p20260509 VALUES [("2026-05-09"), ("2026-05-10")),
PARTITION p20260510 VALUES [("2026-05-10"), ("2026-05-11")),
PARTITION p20260511 VALUES [("2026-05-11"), ("2026-05-12")),
PARTITION p20260512 VALUES [("2026-05-12"), ("2026-05-13")),
PARTITION p20260513 VALUES [("2026-05-13"), ("2026-05-14")),
PARTITION p20260514 VALUES [("2026-05-14"), ("2026-05-15")))
DISTRIBUTED BY HASH(`id`) BUCKETS 3 
PROPERTIES (
"compression" = "LZ4",
"fast_schema_evolution" = "true",
"replicated_storage" = "true",
"replication_num" = "3"
);
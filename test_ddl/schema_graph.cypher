// ================================================================
// Neo4j Schema Graph — NJ Bank App
// 从 5 个 SQL 文件（Doris OLAP）DDL 中推断的表间关系
// 文件：RCLP_DATA.sql | EDWICL_DATA.sql | EDWIOL_DATA.sql
//       EDWIML_DATA.sql | DMRBM_DATA.sql
//
// 说明：Doris OLAP 表无显式 FOREIGN KEY，关系均由共享字段语义推断。
//   - 节点标签 :Table，唯一标识 fqn = "schema.tableName"
//   - 节点属性：schema / name / comment / layer / duplicateKey / distributedBy
//   - 边属性：  via（连接字段）/ note（业务含义）
// ================================================================

// ----------------------------------------------------------------
// 0. 唯一性约束（Neo4j 4.x+ 语法）
// ----------------------------------------------------------------
CREATE CONSTRAINT table_fqn_unique IF NOT EXISTS
  FOR (t:Table) REQUIRE t.fqn IS UNIQUE;


// ================================================================
// 1. RCLP_DATA — 标签层
// ================================================================

MERGE (t:Table {fqn: 'RCLP_DATA.CST_LABEL_INFO_ALL'})
SET t.schema        = 'RCLP_DATA',
    t.name          = 'CST_LABEL_INFO_ALL',
    t.comment       = '客户标签全量信息',
    t.layer         = '标签层',
    t.duplicateKey  = 'label_no',
    t.distributedBy = 'cust_no';

MERGE (t:Table {fqn: 'RCLP_DATA.LBL_VAL_LIST'})
SET t.schema        = 'RCLP_DATA',
    t.name          = 'LBL_VAL_LIST',
    t.comment       = '标签信息元数据表',
    t.layer         = '标签层',
    t.duplicateKey  = 'label_no',
    t.distributedBy = 'label_no';


// ================================================================
// 2. EDWICL_DATA — 数据清算层（ODS/CL 层）
// ================================================================

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PT_INDV_CUST_BASIC',
    t.comment       = '个人客户基本信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, party_id',
    t.distributedBy = 'party_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_AST'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PT_INDV_CUST_AST',
    t.comment       = '个人客户资产信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, party_id',
    t.distributedBy = 'party_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PB_ACCT_ORG',
    t.comment       = '账务机构信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'org_no',
    t.distributedBy = 'org_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PB_EMPLY'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PB_EMPLY',
    t.comment       = '员工信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'emply_no',
    t.distributedBy = 'emply_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PB_PROD',
    t.comment       = '产品信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_CC_CRDT_CARD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_CC_CRDT_CARD',
    t.comment       = '信用卡信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'lp_org_no',
    t.distributedBy = 'crdt_card_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_DP_DEBIT_CARD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_DP_DEBIT_CARD',
    t.comment       = '借记卡信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, card_no',
    t.distributedBy = 'card_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_DP_INDV_DPSIT_ACCT',
    t.comment       = '个人存款账户信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'dpstacct_no',
    t.distributedBy = 'dpstacct_no, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_BAL_ACCUM'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_DP_INDV_DPSIT_BAL_ACCUM',
    t.comment       = '个人存款余额积数',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'dpstacct_no',
    t.distributedBy = 'dpstacct_no, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_DP_ACCT_TXN_CNTRA'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_DP_ACCT_TXN_CNTRA',
    t.comment       = '账户交易对手信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'lp_org_no',
    t.distributedBy = 'lp_org_no, txn_ser_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_LN_INDV_LNACCT',
    t.comment       = '个人贷款账户信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'loan_acct_no',
    t.distributedBy = 'loan_acct_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LOAN_DUBIL_REPAY_STU'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_LN_INDV_LOAN_DUBIL_REPAY_STU',
    t.comment       = '个人贷款借据还款情况',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'dubil_no',
    t.distributedBy = 'dubil_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_LN_IFC_LNACCT_HIS'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_LN_IFC_LNACCT_HIS',
    t.comment       = '互金贷款账户信息历史',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, loan_acct_no',
    t.distributedBy = 'loan_acct_no, cust_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_LN_XYD_CRDT_LMT'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_LN_XYD_CRDT_LMT',
    t.comment       = '鑫易贷授信额度信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'crdt_line_no',
    t.distributedBy = 'crdt_line_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_LN_XYD_LOAN_DUBIL'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_LN_XYD_LOAN_DUBIL',
    t.comment       = '鑫易贷借据信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, dubil_no',
    t.distributedBy = 'dubil_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_AGEN_INSURE'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_AGEN_INSURE',
    t.comment       = '代理保险信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'insure_bil_no',
    t.distributedBy = 'insure_bil_no, lp_org_no, insure_plc_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_AGEN_TRSBOND'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_AGEN_TRSBOND',
    t.comment       = '代理国债信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'cap_acct_no',
    t.distributedBy = 'trsbond_no, lp_org_no, trsbond_acct_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_CMCL_PNSN_ACCT_BASIC'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_CMCL_PNSN_ACCT_BASIC',
    t.comment       = '商业养老金账户基本信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, src_product_id',
    t.distributedBy = 'etl_dt, src_product_id, lp_org_no, cmcl_pnsn_txn_acct_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_FIN_ACCT_BASIC'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_FIN_ACCT_BASIC',
    t.comment       = '理财账户基本信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'cap_acct_no',
    t.distributedBy = 'cap_acct_no, lp_org_no, src_product_id, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_FIN_TXN_CFM_DTL'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_FIN_TXN_CFM_DTL',
    t.comment       = '理财交易确认明细',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'etl_dt, ta_cfm_flow_no',
    t.distributedBy = 'etl_dt, ta_cfm_flow_no, lp_org_no, ta_cd';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_FUND_ACCT_BASIC',
    t.comment       = '基金账户基本信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'fund_cd',
    t.distributedBy = 'fund_acct_no, lp_org_no, cap_acct_no, src_product_id, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_FUND_TXN_DTL'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_FUND_TXN_DTL',
    t.comment       = '基金交易明细',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'txn_ser_no',
    t.distributedBy = 'txn_ser_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_INDV_CST_WLTH_PRD_TXN_SUM'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_INDV_CST_WLTH_PRD_TXN_SUM',
    t.comment       = '个人客户财富类产品交易汇总',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'cust_no',
    t.distributedBy = 'cust_no, src_product_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_PREC_METAL_TXN_DTL'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_PREC_METAL_TXN_DTL',
    t.comment       = '贵金属交易明细',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'txn_no',
    t.distributedBy = 'txn_no, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_IT_THIR_DPSIT_MGMT'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_IT_THIR_DPSIT_MGMT',
    t.comment       = '第三方存管信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'secu_acct_no',
    t.distributedBy = 'secu_acct_no, lp_org_no, broker_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PD_FIN_PROD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PD_FIN_PROD',
    t.comment       = '理财产品信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'src_product_id',
    t.distributedBy = 'src_product_id, lp_org_no';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PD_FUND_PROD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PD_FUND_PROD',
    t.comment       = '基金产品信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'src_product_id',
    t.distributedBy = 'src_product_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PD_PREC_METAL_PROD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PD_PREC_METAL_PROD',
    t.comment       = '贵金属产品信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'src_product_id',
    t.distributedBy = 'src_product_id';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PD_CSN_BOND_PROD'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PD_CSN_BOND_PROD',
    t.comment       = '代销债券产品信息',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'src_product_id',
    t.distributedBy = 'src_product_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWICL_DATA.C_PD_DPSIT_PROD_INT_RATE_BSATR'})
SET t.schema        = 'EDWICL_DATA',
    t.name          = 'C_PD_DPSIT_PROD_INT_RATE_BSATR',
    t.comment       = '存款产品利率基本属性',
    t.layer         = '数据清算层',
    t.duplicateKey  = 'src_product_id',
    t.distributedBy = 'src_product_id, curr_cd, dpsit_period, int_rate_grade, lp_org_no, brch_org_no, etl_dt';


// ================================================================
// 3. EDWIOL_DATA — 线上数据层（OL 层）
// ================================================================

MERGE (t:Table {fqn: 'EDWIOL_DATA.BRP_CUST_RELA_INFO_RBMS'})
SET t.schema        = 'EDWIOL_DATA',
    t.name          = 'BRP_CUST_RELA_INFO_RBMS',
    t.comment       = '大零售客户联系信息表',
    t.layer         = '线上数据层',
    t.duplicateKey  = 'party_id',
    t.distributedBy = 'party_id';

MERGE (t:Table {fqn: 'EDWIOL_DATA.CEI_TBDXASSETSHAREDETAIL1'})
SET t.schema        = 'EDWIOL_DATA',
    t.name          = 'CEI_TBDXASSETSHAREDETAIL1',
    t.comment       = '商业养老金份额明细表',
    t.layer         = '线上数据层',
    t.duplicateKey  = 'serial_no',
    t.distributedBy = 'cfm_no, cfm_date, ta_code, ta_client, prd_code, register_date';

MERGE (t:Table {fqn: 'EDWIOL_DATA.GIS_GIS_POSITION_DETAIL'})
SET t.schema        = 'EDWIOL_DATA',
    t.name          = 'GIS_GIS_POSITION_DETAIL',
    t.comment       = '客户持仓收益详情表',
    t.layer         = '线上数据层',
    t.duplicateKey  = 'id, cac_date',
    t.distributedBy = 'id';

MERGE (t:Table {fqn: 'EDWIOL_DATA.MED_INTERACTION_DIARY'})
SET t.schema        = 'EDWIOL_DATA',
    t.name          = 'MED_INTERACTION_DIARY',
    t.comment       = '零售客户互动日记表',
    t.layer         = '线上数据层',
    t.duplicateKey  = 'userid',
    t.distributedBy = 'userid';

MERGE (t:Table {fqn: 'EDWIOL_DATA.MFP_MIX_SMS_GATEWAY'})
SET t.schema        = 'EDWIOL_DATA',
    t.name          = 'MFP_MIX_SMS_GATEWAY',
    t.comment       = '短信网关记录表',
    t.layer         = '线上数据层',
    t.duplicateKey  = 'id, user_id',
    t.distributedBy = 'id';


// ================================================================
// 4. EDWIML_DATA — 数据中间层（ML 层）
// ================================================================

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_LIACCT',
    t.comment       = '负债账户',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_LNACCT',
    t.comment       = '贷款账户',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT_DEVAL_H'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_LNACCT_DEVAL_H',
    t.comment       = '贷款账户减值历史',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, lp_org_no, start_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_FUND_SHARE_DTL'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_FUND_SHARE_DTL',
    t.comment       = '基金份额明细',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, bank_acct_no, product_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_FUND_INVEST_PRFT_LOSS_H'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_FUND_INVEST_PRFT_LOSS_H',
    t.comment       = '基金投资损益历史',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, lp_org_no, start_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_CMCL_PNSN_INVT_PRFT_LSS_H'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_CMCL_PNSN_INVT_PRFT_LSS_H',
    t.comment       = '商业养老金投资损益历史',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_CUST_BROKER_ACCT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_CUST_BROKER_ACCT',
    t.comment       = '客户券商账户',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_IYDV_STL_ACCT_BIYD_REGBK'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_IYDV_STL_ACCT_BIYD_REGBK',
    t.comment       = '个人结算账户绑定信息',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id, liab_acct_no, bind_card_liab_acct_no, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_AR_XXD_CRDT_CONT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_AR_XXD_CRDT_CONT',
    t.comment       = '鑫享贷授信合同',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ar_agt_id',
    t.distributedBy = 'ar_agt_id';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_CA_INTLG_MKTING_OUT_CALL_REC'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_CA_INTLG_MKTING_OUT_CALL_REC',
    t.comment       = '智能营销呼出记录表',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'mkting_act_no',
    t.distributedBy = 'mkting_act_no';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_EV_CMCL_PNSN_TXN_CFM'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_EV_CMCL_PNSN_TXN_CFM',
    t.comment       = '商业养老金交易确认事件',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'event_id',
    t.distributedBy = 'event_id, lp_org_no';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PB_INSURE_CORP_TA'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PB_INSURE_CORP_TA',
    t.comment       = '商业养老保险公司TA信息',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'ta_cd',
    t.distributedBy = 'ta_cd';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PB_RTL_CORE_PROD_MAP'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PB_RTL_CORE_PROD_MAP',
    t.comment       = '零售核心产品映射',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'aval_prdct_no',
    t.distributedBy = 'aval_prdct_no, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PB_SERV_CTRL'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PB_SERV_CTRL',
    t.comment       = '服务控制登记簿',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'serv_ctrl_no',
    t.distributedBy = 'liab_acct_no';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_PRODUCT',
    t.comment       = '产品主表（中间层）',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_CMCL_PNSN_PROD',
    t.comment       = '商业养老金产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id, lp_org_no';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD_MKT'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_CMCL_PNSN_PROD_MKT',
    t.comment       = '商业养老金产品市场信息',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id, lp_org_no, issue_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_CORE_DPSIT_PROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_CORE_DPSIT_PROD',
    t.comment       = '核心存款产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_CORE_LOANPROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_CORE_LOANPROD',
    t.comment       = '核心贷款产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id, lp_org_no, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_DEBIT_CARD_PROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_DEBIT_CARD_PROD',
    t.comment       = '借记卡产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'etl_dt, product_id, lp_org_no',
    t.distributedBy = 'product_id';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_ESPEC_DPSIT_PROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_ESPEC_DPSIT_PROD',
    t.comment       = '特殊存款产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'lp_org_no',
    t.distributedBy = 'lp_org_no, product_id, etl_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_FUND_PROD'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_FUND_PROD',
    t.comment       = '基金产品',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PD_PROD_RELA_H'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PD_PROD_RELA_H',
    t.comment       = '产品关系历史',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'product_id',
    t.distributedBy = 'product_id, lp_org_no, prod_rela_type_cd, start_dt';

MERGE (t:Table {fqn: 'EDWIML_DATA.M_PT_RBI_EMPLY_ROLE'})
SET t.schema        = 'EDWIML_DATA',
    t.name          = 'M_PT_RBI_EMPLY_ROLE',
    t.comment       = '零售银行员工角色信息',
    t.layer         = '数据中间层',
    t.duplicateKey  = 'party_id',
    t.distributedBy = 'party_id, rbi_emply_role_type_cd';


// ================================================================
// 5. DMRBM_DATA — 零售数据集市层（DM 层）
// ================================================================

MERGE (t:Table {fqn: 'DMRBM_DATA.A_DNP_RTL_CUST_CAPTY'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_DNP_RTL_CUST_CAPTY',
    t.comment       = '零售客户产能信息表',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, ecf_party_id';

MERGE (t:Table {fqn: 'DMRBM_DATA.A_RCP_RTL_PERSONA_CUST_SEARCH'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_RCP_RTL_PERSONA_CUST_SEARCH',
    t.comment       = '零售客户画像客户检索接口',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_ASTIT_KEY_LINK'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_ROA_INDV_CST_ASTIT_KEY_LINK',
    t.comment       = '个人客户资产类指标通用接口-关键链路',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_BHV_T_KEY_LINK'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_ROA_INDV_CST_BHV_T_KEY_LINK',
    t.comment       = '个人客户行为类指标通用接口-关键链路',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_DBTIT_KEY_LINK'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_ROA_INDV_CST_DBTIT_KEY_LINK',
    t.comment       = '个人客户负债类指标通用接口-关键链路',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_MKTXT_KEY_LINK'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'A_ROA_INDV_CST_MKTXT_KEY_LINK',
    t.comment       = '个人客户营销类指标通用接口-关键链路',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_BS_CUST_MGMT_MGR_PRIOR'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_BS_CUST_MGMT_MGR_PRIOR',
    t.comment       = '管户经理优先级信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_CA_MKTING_ACT_TASK_INDEX'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_CA_MKTING_ACT_TASK_INDEX',
    t.comment       = '营销活动任务指标',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, act_no, task_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_OT_RTL_MKT_CD'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_OT_RTL_MKT_CD',
    t.comment       = '零售集市代码表',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, model_lvl_cd',
    t.distributedBy = 'etl_dt, model_lvl_cd, pub_cd, cd_val';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_CONTRI_DEG_FEATURE'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_CONTRI_DEG_FEATURE',
    t.comment       = '客户贡献度特征',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, cust_no, stat_range_cd';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_FIN_FEATURE'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_FIN_FEATURE',
    t.comment       = '客户金融特征',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no, ecf_party_id',
    t.distributedBy = 'etl_dt, lp_org_no, ecf_party_id';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_INDV_AGT_SIGN'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_INDV_AGT_SIGN',
    t.comment       = '个人客户协议签约信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, sign_no',
    t.distributedBy = 'etl_dt, sign_no, sign_biz_cd, sign_status_cd, aflt_org_no, sign_chnl_cd';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_LVL_ESTIM'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_LVL_ESTIM',
    t.comment       = '客户等级评价信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, party_id';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_MGMT_RELA_H'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_MGMT_RELA_H',
    t.comment       = '管户关系历史',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'start_dt, end_dt, lp_org_no',
    t.distributedBy = 'party_id, mgmt_org_no, cust_mgr_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_POINT_BIZ_FEATURE'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_POINT_BIZ_FEATURE',
    t.comment       = '客户积分业务特征',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, ecf_party_id';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_SIGN_LABEL'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_SIGN_LABEL',
    t.comment       = '客户签约标签',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, party_id';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_TEL_ELEC_CONT'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_TEL_ELEC_CONT',
    t.comment       = '客户电话电子联系信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, party_id, tel_addr_type_cd, tel_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_CUST_VIEW_KEY_LINK'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_CUST_VIEW_KEY_LINK',
    t.comment       = '客户视图信息-关键链路',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CST_CRP_PYOF_BIZ_FTURE'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_INDV_CST_CRP_PYOF_BIZ_FTURE',
    t.comment       = '个人客户企业代发业务特征',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, cust_no',
    t.distributedBy = 'etl_dt, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_BASIC_LABEL'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_INDV_CUST_BASIC_LABEL',
    t.comment       = '个人客户基础标签信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, cust_no';

MERGE (t:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_VIEW_EXPAND'})
SET t.schema        = 'DMRBM_DATA',
    t.name          = 'E_PT_INDV_CUST_VIEW_EXPAND',
    t.comment       = '个人客户视图扩展信息',
    t.layer         = '数据集市层',
    t.duplicateKey  = 'etl_dt, lp_org_no',
    t.distributedBy = 'etl_dt, lp_org_no, cust_no';


// ================================================================
// ================================================================
// SECTION B：关系（边）
// 说明：所有关系均为从"明细/事务表"指向"主表/被引用表"的方向
//       推断依据：共享字段名称 + 业务语义
// ================================================================
// ================================================================


// ================================================================
// R1. 标签体系关系
// ================================================================

// 标签值元数据 ← 客户标签记录（同一 label_no）
MATCH (a:Table {fqn: 'RCLP_DATA.CST_LABEL_INFO_ALL'})
MATCH (b:Table {fqn: 'RCLP_DATA.LBL_VAL_LIST'})
MERGE (a)-[r:CLASSIFIES_BY_LABEL]->(b)
SET r.via  = 'label_no → label_no',
    r.note = '客户标签记录通过 label_no 引用标签元数据定义';

// 客户主表 ← 客户标签记录（cust_no ≈ party_id）
MATCH (a:Table {fqn: 'RCLP_DATA.CST_LABEL_INFO_ALL'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MERGE (a)-[r:LABELS_CUSTOMER]->(b)
SET r.via  = 'cust_no → party_id',
    r.note = '客户标签关联到个人客户基本信息（cust_no 即 party_id）';


// ================================================================
// R2. 以客户主表为中心的引用关系（C_PT_INDV_CUST_BASIC → *）
// ================================================================

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_AST'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '个人客户资产信息归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIOL_DATA.BRP_CUST_RELA_INFO_RBMS'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '大零售客户联系信息归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_CC_CRDT_CARD'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'ecf_party_id → party_id',
    r.note = '信用卡持有人（ecf_party_id 即 party_id）';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_DP_DEBIT_CARD'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '借记卡持有人';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '个人存款账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_DP_ACCT_TXN_CNTRA'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '账户交易对手记录归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '个人贷款账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_AGEN_INSURE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '代理保险单归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_AGEN_TRSBOND'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '代理国债记录归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_FIN_ACCT_BASIC'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '理财账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '基金账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_FUND_TXN_DTL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '基金交易明细归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_PREC_METAL_TXN_DTL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '贵金属交易明细归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_THIR_DPSIT_MGMT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '第三方存管账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_LN_XYD_CRDT_LMT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id / cust_no → party_id',
    r.note = '鑫易贷授信额度归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_LN_XYD_LOAN_DUBIL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '鑫易贷借据归属客户';

// cust_no 等价于 party_id 的引用
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_INDV_CST_WLTH_PRD_TXN_SUM'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '财富类产品交易汇总归属客户（cust_no 即 party_id）';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_LN_IFC_LNACCT_HIS'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '互金贷款历史归属客户';

// ML 层客户关联
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '负债账户（ML层）归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '贷款账户（ML层）归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_CUST_BROKER_ACCT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '客户券商账户归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_XXD_CRDT_CONT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '鑫享贷授信合同归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PT_RBI_EMPLY_ROLE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '员工角色信息（当事人为员工兼客户身份）';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_CA_INTLG_MKTING_OUT_CALL_REC'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '智能营销外呼记录归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_EV_CMCL_PNSN_TXN_CFM'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '商业养老金交易确认事件归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PB_SERV_CTRL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '服务控制登记归属客户';

// DM 层客户关联（party_id / ecf_party_id）
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_LVL_ESTIM'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '客户等级评价归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_MGMT_RELA_H'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '管户关系历史归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_SIGN_LABEL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '客户签约标签归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_TEL_ELEC_CONT'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'party_id → party_id',
    r.note = '客户电话电子联系信息归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_FIN_FEATURE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'ecf_party_id → party_id',
    r.note = '客户金融特征归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_POINT_BIZ_FEATURE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'ecf_party_id → party_id',
    r.note = '客户积分业务特征归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_DNP_RTL_CUST_CAPTY'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'ecf_party_id → party_id',
    r.note = '零售客户产能信息归属客户';

// DM 层 cust_no 关联
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_RCP_RTL_PERSONA_CUST_SEARCH'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '客户画像检索接口归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_ASTIT_KEY_LINK'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '资产类指标关键链路归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_BHV_T_KEY_LINK'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '行为类指标关键链路归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_DBTIT_KEY_LINK'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '负债类指标关键链路归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_MKTXT_KEY_LINK'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '营销类指标关键链路归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_CONTRI_DEG_FEATURE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '客户贡献度特征归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_CUST_VIEW_KEY_LINK'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '客户视图关键链路归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_INDV_CST_CRP_PYOF_BIZ_FTURE'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '企业代发业务特征归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_BASIC_LABEL'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '个人客户基础标签归属客户';

MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_VIEW_EXPAND'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'cust_no → party_id',
    r.note = '个人客户视图扩展归属客户';


// ================================================================
// R3. 产品主表引用关系（C_PB_PROD ← 各账户/业务表）
// ================================================================

// 产品子类详情引用产品主表（src_product_id 是 product_id 的细化）
MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PD_FIN_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '理财产品详情扩展产品主表';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PD_FUND_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '基金产品详情扩展产品主表';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PD_PREC_METAL_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '贵金属产品详情扩展产品主表';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PD_CSN_BOND_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '代销债券产品详情扩展产品主表';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_PD_DPSIT_PROD_INT_RATE_BSATR'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '存款产品利率属性扩展产品主表';

// 账户/业务表引用产品主表
MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_CC_CRDT_CARD'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '信用卡使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_DP_DEBIT_CARD'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '借记卡使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '个人存款账户使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '个人贷款账户使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_AGEN_INSURE'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '代理保险使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_AGEN_TRSBOND'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '代理国债使用某产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_FIN_ACCT_BASIC'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '理财账户关联产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '基金账户关联产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '负债账户（ML层）关联产品';

MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
MERGE (b)-[r:USES_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '贷款账户（ML层）关联产品';

// ML 产品主表与 CL 产品主表
MATCH (prod_cl:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (prod_ml:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MERGE (prod_ml)-[r:DERIVES_FROM]->(prod_cl)
SET r.via  = 'product_id → product_id',
    r.note = '中间层产品主表源自清算层产品主表';

// ML 产品子类引用 ML 产品主表
MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '商业养老金产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_CORE_DPSIT_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '核心存款产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_CORE_LOANPROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '核心贷款产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_DEBIT_CARD_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '借记卡产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_FUND_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '基金产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_ESPEC_DPSIT_PROD'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '特殊存款产品扩展中间层产品主表';

MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_PRODUCT'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_PROD_RELA_H'})
MERGE (b)-[r:RECORDS_PRODUCT_RELA]->(prod)
SET r.via  = 'product_id → product_id',
    r.note = '产品关系历史记录某产品的演进关系';

// 商业养老金产品市场信息引用养老金产品
MATCH (pnsn:Table {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD_MKT'})
MERGE (b)-[r:EXTENDS_PRODUCT]->(pnsn)
SET r.via  = 'product_id → product_id',
    r.note = '养老金产品市场信息扩展养老金产品';

// 产品映射表引用产品主表
MATCH (prod:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PB_RTL_CORE_PROD_MAP'})
MERGE (b)-[r:MAPS_TO_PRODUCT]->(prod)
SET r.via  = 'src_product_id → product_id',
    r.note = '零售核心产品映射表关联产品主表';


// ================================================================
// R4. 机构主表引用关系（C_PB_ACCT_ORG ← 各账户/业务表）
// ================================================================

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MERGE (b)-[r:OPENED_AT_ORG]->(org)
SET r.via  = 'open_acct_org_no → org_no',
    r.note = '存款账户开户机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MERGE (b)-[r:OPENED_AT_ORG]->(org)
SET r.via  = 'open_acct_org_no → org_no',
    r.note = '贷款账户开户机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_CC_CRDT_CARD'})
MERGE (b)-[r:MANAGED_BY_ORG]->(org)
SET r.via  = 'mgmt_org_no → org_no',
    r.note = '信用卡管理机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_DP_DEBIT_CARD'})
MERGE (b)-[r:MANAGED_BY_ORG]->(org)
SET r.via  = 'mgmt_org_no → org_no',
    r.note = '借记卡管理机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_IT_AGEN_INSURE'})
MERGE (b)-[r:MANAGED_BY_ORG]->(org)
SET r.via  = 'mgmt_org_no / org_no → org_no',
    r.note = '代理保险签约/管理机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_IT_AGEN_TRSBOND'})
MERGE (b)-[r:MANAGED_BY_ORG]->(org)
SET r.via  = 'mgmt_org_no / org_no → org_no',
    r.note = '代理国债签约/管理机构';

MATCH (org:Table {fqn: 'EDWICL_DATA.C_PB_ACCT_ORG'})
MATCH (b:Table   {fqn: 'DMRBM_DATA.E_PT_CUST_MGMT_RELA_H'})
MERGE (b)-[r:MANAGED_BY_ORG]->(org)
SET r.via  = 'mgmt_org_no → org_no',
    r.note = '管户关系记录中的管理机构';


// ================================================================
// R5. 员工主表引用关系（C_PB_EMPLY ← 各业务表）
// ================================================================

MATCH (emp:Table {fqn: 'EDWICL_DATA.C_PB_EMPLY'})
MATCH (b:Table   {fqn: 'DMRBM_DATA.E_PT_CUST_MGMT_RELA_H'})
MERGE (b)-[r:MANAGED_BY_EMPLY]->(emp)
SET r.via  = 'cust_mgr_no → emply_no',
    r.note = '管户关系中的客户经理';

MATCH (emp:Table {fqn: 'EDWICL_DATA.C_PB_EMPLY'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_CC_CRDT_CARD'})
MERGE (b)-[r:REFERRED_BY_EMPLY]->(emp)
SET r.via  = 'recmd_emply_no → emply_no',
    r.note = '信用卡推荐人工号';

MATCH (emp:Table {fqn: 'EDWICL_DATA.C_PB_EMPLY'})
MATCH (b:Table   {fqn: 'EDWICL_DATA.C_IT_AGEN_TRSBOND'})
MERGE (b)-[r:REFERRED_BY_EMPLY]->(emp)
SET r.via  = 'recmd_emply_no → emply_no',
    r.note = '国债推荐人工号';


// ================================================================
// R6. 账户内部链式关系
// ================================================================

// 存款账户 → 余额积数（同一账号）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_BAL_ACCUM'})
MERGE (b)-[r:ACCUMULATES_FROM]->(a)
SET r.via  = 'dpstacct_no → dpstacct_no',
    r.note = '存款余额积数来源于存款账户';

// 借记卡 → 存款账户（关联账号）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_DP_DEBIT_CARD'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MERGE (a)-[r:LINKS_TO_ACCT]->(b)
SET r.via  = 'rela_acct_no → cust_acct_no / dpstacct_no',
    r.note = '借记卡绑定的关联存款账号';

// 存款账户 → ML层负债账户（协议编号）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_DP_INDV_DPSIT_ACCT'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MERGE (b)-[r:MAPS_TO_DEPOSIT]->(a)
SET r.via  = 'ar_agt_id → ar_agt_id',
    r.note = 'ML层负债账户通过协议编号对应CL层存款账户';

// 贷款账户 → ML层贷款账户（协议编号）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
MERGE (b)-[r:MAPS_TO_LOAN]->(a)
SET r.via  = 'ar_agt_id → ar_agt_id  /  loan_acct_no → loan_acct_no',
    r.note = 'ML层贷款账户通过协议编号对应CL层贷款账户';

// 贷款账户 → 借据还款情况
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LOAN_DUBIL_REPAY_STU'})
MERGE (b)-[r:REPAY_OF_LOAN]->(a)
SET r.via  = 'loan_acct_no → loan_acct_no  /  dubil_no → dubil_no',
    r.note = '借据还款情况属于某贷款账户';

// 互金贷款历史 → 贷款账户
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_LN_IFC_LNACCT_HIS'})
MERGE (b)-[r:HISTORY_OF_LOAN]->(a)
SET r.via  = 'loan_acct_no → loan_acct_no',
    r.note = '互金贷款历史表记录贷款账户的历史状态';

// 鑫易贷借据 → 贷款账户
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LNACCT'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_LN_XYD_LOAN_DUBIL'})
MERGE (b)-[r:BELONGS_TO_LOAN]->(a)
SET r.via  = 'loan_acct_no → loan_acct_no',
    r.note = '鑫易贷借据归属某贷款账户';

// 鑫易贷借据 → 授信额度
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_XYD_CRDT_LMT'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_LN_XYD_LOAN_DUBIL'})
MERGE (b)-[r:USES_CREDIT_LINE]->(a)
SET r.via  = 'crdt_line_no → crdt_line_no',
    r.note = '鑫易贷借据使用某授信额度';

// ML层贷款账户 → 借据还款情况
MATCH (a:Table {fqn: 'EDWICL_DATA.C_LN_INDV_LOAN_DUBIL_REPAY_STU'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
MERGE (b)-[r:HAS_DUBIL_REPAY]->(a)
SET r.via  = 'dubil_no → dubil_no',
    r.note = 'ML层贷款账户引用借据还款情况';

// ML层贷款账户减值历史 → ML层贷款账户
MATCH (a:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_LNACCT_DEVAL_H'})
MERGE (b)-[r:HISTORY_OF_DEVAL]->(a)
SET r.via  = 'ar_agt_id → ar_agt_id',
    r.note = '贷款账户减值历史归属某贷款协议';

// 个人结算账户绑定 → ML层负债账户
MATCH (a:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_IYDV_STL_ACCT_BIYD_REGBK'})
MERGE (b)-[r:BINDS_LIAB_ACCT]->(a)
SET r.via  = 'liab_acct_no → liab_acct_no',
    r.note = '结算账户绑定某负债账号';

// 服务控制登记 → ML层负债账户
MATCH (a:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_PB_SERV_CTRL'})
MERGE (b)-[r:CONTROLS_LIAB_ACCT]->(a)
SET r.via  = 'liab_acct_no → liab_acct_no',
    r.note = '服务控制登记簿控制某负债账户';

// ML层负债账户 → 交易对手流水
MATCH (a:Table {fqn: 'EDWICL_DATA.C_DP_ACCT_TXN_CNTRA'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MERGE (b)-[r:HAS_TXN_RECORD]->(a)
SET r.via  = 'liab_acct_no → liab_acct_no',
    r.note = '负债账户对应的交易对手记录';


// ================================================================
// R7. 理财 / 基金 / 养老金业务链
// ================================================================

// 理财账户 → 理财交易确认明细
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_FIN_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_IT_FIN_TXN_CFM_DTL'})
MERGE (b)-[r:CONFIRMS_FOR_FIN_ACCT]->(a)
SET r.via  = 'cap_acct_no → cap_acct_no',
    r.note = '理财交易确认明细属于某理财资金账号';

// 基金账户 → 基金交易明细
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_IT_FUND_TXN_DTL'})
MERGE (b)-[r:TXN_OF_FUND_ACCT]->(a)
SET r.via  = 'fund_acct_no → fund_acct_no',
    r.note = '基金交易明细属于某基金账号';

// 基金账户 → ML层基金份额明细（cap_acct_no 关联）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_FUND_SHARE_DTL'})
MERGE (b)-[r:SHARE_OF_FUND_ACCT]->(a)
SET r.via  = 'cap_acct_no → cap_acct_no  /  ar_agt_id 联动',
    r.note = 'ML层基金份额明细来源于基金账户';

// ML层基金份额明细 → ML层基金产品
MATCH (a:Table {fqn: 'EDWIML_DATA.M_PD_FUND_PROD'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_FUND_SHARE_DTL'})
MERGE (b)-[r:SHARE_OF_FUND_PROD]->(a)
SET r.via  = 'product_id → product_id',
    r.note = '基金份额明细关联基金产品';

// ML层基金投资损益历史 → ML层基金份额明细
MATCH (a:Table {fqn: 'EDWIML_DATA.M_AR_FUND_SHARE_DTL'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_FUND_INVEST_PRFT_LOSS_H'})
MERGE (b)-[r:PRFT_OF_FUND_SHARE]->(a)
SET r.via  = 'ar_agt_id → ar_agt_id',
    r.note = '基金投资损益历史基于基金份额协议';

// 商业养老金份额明细（OL层）→ 养老金账户基本信息（CL层）
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_CMCL_PNSN_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWIOL_DATA.CEI_TBDXASSETSHAREDETAIL1'})
MERGE (b)-[r:SHARE_OF_PNSN_ACCT]->(a)
SET r.via  = 'ta_client → cap_acct_no（商业养老金交易账号）',
    r.note = 'OL层份额明细对应养老金资金账户';

// 养老金交易确认事件 → TA信息
MATCH (ta:Table {fqn: 'EDWIML_DATA.M_PB_INSURE_CORP_TA'})
MATCH (b:Table  {fqn: 'EDWIML_DATA.M_EV_CMCL_PNSN_TXN_CFM'})
MERGE (b)-[r:TXN_VIA_TA]->(ta)
SET r.via  = 'ta_cd → ta_cd',
    r.note = '养老金交易通过某TA机构确认';

// TA信息 → 养老金产品
MATCH (prod:Table {fqn: 'EDWIML_DATA.M_PD_CMCL_PNSN_PROD'})
MATCH (b:Table    {fqn: 'EDWIML_DATA.M_PB_INSURE_CORP_TA'})
MERGE (b)-[r:MANAGES_PNSN_PROD]->(prod)
SET r.via  = 'ta_cd → ta_cd',
    r.note = '保险公司TA管理某商业养老金产品';

// 养老金投资损益历史 → 养老金账户基本信息
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_CMCL_PNSN_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWIML_DATA.M_AR_CMCL_PNSN_INVT_PRFT_LSS_H'})
MERGE (b)-[r:PRFT_OF_PNSN_ACCT]->(a)
SET r.via  = 'ar_agt_id 联动（商业养老金协议编号）',
    r.note = '养老金投资损益历史对应某养老金账户协议';

// 财富产品交易汇总 → 各业务子类产品引用
MATCH (a:Table {fqn: 'EDWICL_DATA.C_PB_PROD'})
MATCH (b:Table {fqn: 'EDWICL_DATA.C_IT_INDV_CST_WLTH_PRD_TXN_SUM'})
MERGE (b)-[r:SUMMARIZES_BY_PRODUCT]->(a)
SET r.via  = 'src_product_id → product_id',
    r.note = '财富产品交易汇总表按产品聚合';

// 持仓收益详情（OL层）— 同类数据参考基金账户
MATCH (a:Table {fqn: 'EDWICL_DATA.C_IT_FUND_ACCT_BASIC'})
MATCH (b:Table {fqn: 'EDWIOL_DATA.GIS_GIS_POSITION_DETAIL'})
MERGE (b)-[r:POSITION_OF_FUND_ACCT]->(a)
SET r.via  = 'id ↔ fund_acct_no（持仓ID对应基金账号）',
    r.note = 'OL层持仓收益详情关联基金账户';

// 互动日记（OL层）→ 客户基本信息
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIOL_DATA.MED_INTERACTION_DIARY'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'userid → party_id（APP用户ID对应客户编号）',
    r.note = 'APP互动日记归属客户';

// 短信网关记录（OL层）→ 客户基本信息
MATCH (cust:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table    {fqn: 'EDWIOL_DATA.MFP_MIX_SMS_GATEWAY'})
MERGE (b)-[r:BELONGS_TO_CUSTOMER]->(cust)
SET r.via  = 'user_id → party_id（用户ID对应客户编号）',
    r.note = '短信网关记录归属客户';


// ================================================================
// R8. DM 层聚合来源关系（AGGREGATES_FROM）
// ================================================================

MATCH (a:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_AST'})
MATCH (b:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_ASTIT_KEY_LINK'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'party_id / cust_no',
    r.note = '资产类指标聚合自客户资产表';

MATCH (a:Table {fqn: 'EDWIML_DATA.M_AR_LIACCT'})
MATCH (b:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_DBTIT_KEY_LINK'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'party_id / cust_no',
    r.note = '负债类指标聚合自负债账户表';

MATCH (a:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table {fqn: 'DMRBM_DATA.E_PT_CUST_CONTRI_DEG_FEATURE'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'cust_no → party_id',
    r.note = '客户贡献度特征聚合自客户基本信息';

MATCH (a:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_BASIC_LABEL'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'cust_no → party_id',
    r.note = '基础标签聚合自客户基本信息';

MATCH (a:Table {fqn: 'RCLP_DATA.CST_LABEL_INFO_ALL'})
MATCH (b:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_BASIC_LABEL'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'cust_no（客户标签数据）',
    r.note = '基础标签同时聚合自客户标签全量表';

MATCH (a:Table {fqn: 'DMRBM_DATA.E_PT_CUST_VIEW_KEY_LINK'})
MATCH (b:Table {fqn: 'DMRBM_DATA.E_PT_INDV_CUST_VIEW_EXPAND'})
MERGE (b)-[r:EXTENDS_VIEW]->(a)
SET r.via  = 'cust_no',
    r.note = '客户视图扩展表基于客户视图关键链路';

MATCH (a:Table {fqn: 'EDWICL_DATA.C_PT_INDV_CUST_BASIC'})
MATCH (b:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_BHV_T_KEY_LINK'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'cust_no → party_id',
    r.note = '行为类指标聚合自客户基本信息';

MATCH (a:Table {fqn: 'EDWIML_DATA.M_CA_INTLG_MKTING_OUT_CALL_REC'})
MATCH (b:Table {fqn: 'DMRBM_DATA.A_ROA_INDV_CST_MKTXT_KEY_LINK'})
MERGE (b)-[r:AGGREGATES_FROM]->(a)
SET r.via  = 'party_id / cust_no',
    r.note = '营销类指标聚合自智能营销外呼记录';

// ================================================================
// END
// ================================================================

from django.db import migrations


CREATE_VW_FACT_HARVEST = """
CREATE OR REPLACE VIEW vw_fact_harvest AS
SELECT
    fh.fact_id,
    fh.event_date,
    fh.quantity_kg::NUMERIC(18, 3) AS quantity_kg,
    fh.unit_count,
    pg.code AS product_grade_code,
    dc.display_name AS company,
    ds.site_name,
    fh.dim_batch_id AS batch_id
FROM finance_factharvest fh
JOIN harvest_productgrade pg ON pg.id = fh.product_grade_id
JOIN finance_dimcompany dc ON dc.company_id = fh.dim_company_id
JOIN finance_dimsite ds ON ds.site_id = fh.dim_site_id;
"""


CREATE_VW_INTERCOMPANY = """
CREATE OR REPLACE VIEW vw_intercompany_transactions AS
SELECT
    tx.tx_id,
    tx.posting_date,
    tx.state,
    dc_from.display_name AS from_company,
    dc_to.display_name AS to_company,
    pg.code AS product_grade_code,
    tx.amount::NUMERIC(18, 2) AS amount,
    tx.currency
FROM finance_intercompanytransaction tx
JOIN finance_intercompanypolicy pol ON pol.policy_id = tx.policy_id
JOIN finance_dimcompany dc_from ON dc_from.company_id = pol.from_company_id
JOIN finance_dimcompany dc_to ON dc_to.company_id = pol.to_company_id
JOIN harvest_productgrade pg ON pg.id = pol.product_grade_id;
"""


DROP_VIEWS = """
DROP VIEW IF EXISTS vw_intercompany_transactions;
DROP VIEW IF EXISTS vw_fact_harvest;
"""


CREATE_INDEXES = """
CREATE INDEX IF NOT EXISTS ix_fact_harvest_event_date
    ON finance_factharvest (event_date);

CREATE INDEX IF NOT EXISTS ix_fact_harvest_company_grade
    ON finance_factharvest (dim_company_id, product_grade_id);

CREATE INDEX IF NOT EXISTS ix_intercompany_posting_date
    ON finance_intercompanytransaction (posting_date);
"""


DROP_INDEXES = """
DROP INDEX IF EXISTS ix_intercompany_posting_date;
DROP INDEX IF EXISTS ix_fact_harvest_company_grade;
DROP INDEX IF EXISTS ix_fact_harvest_event_date;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("finance", "0003_navexportbatch_navexportline_historicalnavexportline_and_more"),
    ]

    operations = [
        migrations.RunSQL(sql=CREATE_VW_FACT_HARVEST, reverse_sql="DROP VIEW IF EXISTS vw_fact_harvest"),
        migrations.RunSQL(sql=CREATE_VW_INTERCOMPANY, reverse_sql="DROP VIEW IF EXISTS vw_intercompany_transactions"),
        migrations.RunSQL(sql=CREATE_INDEXES, reverse_sql=DROP_INDEXES),
    ]

import csv
import logging
from datetime import datetime, timedelta
from tempfile import NamedTemporaryFile

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook


default_args = {"owner": "Daniel", "retries": 5, "retry_delay": timedelta(minutes=10)}


def postgres_to_s3(ds_nodash, next_ds_nodash):
    # step 1: query data from postgresql db and save into text file
    hook = PostgresHook(postgres_conn_id="postgres_localhost")
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.execute("select * from orders where quantity > 50")
    with NamedTemporaryFile(mode="w", suffix=f"{ds_nodash}") as f:
        with open(f"dags/get_orders_{ds_nodash}.txt", "w") as f:
            csv_writer = csv.writer(f)
            csv_writer.writerow([i[0] for i in cursor.description])
            csv_writer.writerows(cursor)
            f.flush()
        cursor.close()
        conn.close()
        logging.info(
            "Saved orders data in text file: %s", f"dags/get_orders_{ds_nodash}.txt"
        )


with DAG(
    dag_id="dag_with_postgres_hooks_v05",
    default_args=default_args,
    start_date=datetime(2024, 3, 13),
    schedule_interval="@daily",
) as dag:
    task1 = PythonOperator(task_id="postgres_to_s3", python_callable=postgres_to_s3)
    task1

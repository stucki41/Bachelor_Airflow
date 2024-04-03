from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.email_operator import EmailOperator

default_args = {
    "owner": "Daniel",
    "retries": 1,
    "retry_delay": timedelta(seconds=5),
    "email": "daniel.stuckenberger@studmail.htw-aalen.de",
    "email_on_failure": True,
    "email_on_retry": True,
}

with DAG(
    dag_id="dag_email_notification",
    default_args=default_args,
    start_date=datetime(2024, 4, 2),
    schedule_interval="@daily",
    catchup=False,
) as dag:
    task1 = EmailOperator(
        task_id="send_email",
        to="daniel.stuckenberger@studmail.htw-aalen.de",
        subject="Airflow Alert",
        html_content=""" <h3>Email Test</h3> """,
    )

    task1

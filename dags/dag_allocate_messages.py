from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.utils.email import send_email


default_args = {"owner": "daniel", "retries": 5, "retry_delay": timedelta(minutes=5)}

hook = PostgresHook(postgres_conn_id="postgres_localhost")


def insert_message(cursor, table, message):
    cursor.execute(
        f"INSERT INTO {table} (msg_id, msg_date, msg_time, message) VALUES( %s, %s, %s, %s ) ON CONFLICT DO NOTHING",
        (message[0], message[1], message[2], message[3]),
    )


def insert_message_with_category(cursor, table, message, category):
    cursor.execute(
        f"INSERT INTO {table} (msg_id, msg_date, msg_time, message, category) VALUES( %s, %s, %s, %s, %s ) ON CONFLICT DO NOTHING",
        (message[0], message[1], message[2], message[3], category),
    )


def process_error_messages(ti):
    print("proccess error messages")
    message_ids = []
    message_html = ""
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.execute("select * from messages where msg_type = 'error'")

    messages = cursor.fetchall()
    for message in messages:
        insert_message(cursor, "error_messages", message)
        message_ids.append(message[0])
        message_html += f"<p> {message[1]} / {message[2]}: {message[3]}</p>"
        print(f"insert errr ID: {message[0]}")

    conn.commit()
    cursor.close()
    conn.close()

    if message_html != "":
        send_email(
            to="daniel.stuckenberger@studmail.htw-aalen.de",
            subject="Error Message in Log",
            html_content=f"""
                        Hi, <br>
                        <p>Following messages were raised in System</p>
                        {message_html}
                        <br> Thank You. <br>
                    """,
        )
    print("proccess error messages")
    ti.xcom_push(key="error_messages", value=message_ids)


def process_warning_messages(ti):
    print("proccess warning messages")
    message_ids = []
    category = ""
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.execute("select * from messages where msg_type = 'warning'")

    messages = cursor.fetchall()
    for message in messages:
        text = message[3]
        if "[GLOBAL]" in text:
            category = "global"
        elif "[SPECIAL]" in text:
            category = "special"
        else:
            category = "unknown"

        insert_message_with_category(cursor, "warning_messages", message, category)
        message_ids.append(message[0])
        print(f"insert warning ID: {message[0]}")

    conn.commit()
    cursor.close()
    conn.close()
    ti.xcom_push(key="warning_messages", value=message_ids)


def process_success_messages(ti):
    print("proccess success messages")
    message_ids = []
    conn = hook.get_conn()
    cursor = conn.cursor()
    cursor.execute("select * from messages where msg_type = 'success'")

    messages = cursor.fetchall()
    for message in messages:
        insert_message(cursor, "success_messages", message)
        message_ids.append(message[0])
        print(f"insert success ID: {message[0]}")

    conn.commit()
    cursor.close()
    conn.close()
    ti.xcom_push(key="success_messages", value=message_ids)


def delete_original_messages(ti):
    print("delete original messages")
    message_ids = []
    error_ids = ti.xcom_pull(task_ids="process_error_messages", key="error_messages")
    warning_ids = ti.xcom_pull(
        task_ids="process_warning_messages", key="warning_messages"
    )
    success_ids = ti.xcom_pull(
        task_ids="process_success_messages", key="success_messages"
    )

    message_ids += error_ids
    message_ids += warning_ids
    message_ids += success_ids

    conn = hook.get_conn()
    cursor = conn.cursor()
    for id in message_ids:
        cursor.execute("DELETE FROM messages WHERE msg_id = '{}'".format(id))

    conn.commit()
    cursor.close()
    conn.close()


with DAG(
    dag_id="dag_allocate_messages",
    default_args=default_args,
    start_date=datetime(2024, 3, 27),
    schedule_interval="@daily",
) as dag:
    error_messages = PythonOperator(
        task_id="process_error_messages", python_callable=process_error_messages
    )
    success_messages = PythonOperator(
        task_id="process_success_messages", python_callable=process_success_messages
    )
    warning_messages = PythonOperator(
        task_id="process_warning_messages", python_callable=process_warning_messages
    )
    delete_original_messages = PythonOperator(
        task_id="delete_original_messages", python_callable=delete_original_messages
    )

    [error_messages, success_messages, warning_messages] >> delete_original_messages

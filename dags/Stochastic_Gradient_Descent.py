import pandas as pd
import os
from datetime import datetime, timedelta
from airflow.decorators import dag, task
from airflow.models.taskinstance import TaskInstance
from tensorflow import keras
from tensorflow.keras import layers


default_args = {"owner": "daniel", "retries": 5, "retry_delay": timedelta(minutes=5)}


@dag(
    dag_id="Stochastic_Gradient_Descent_v4",
    default_args=default_args,
    start_date=datetime(2024, 4, 16),
    schedule_interval="@daily",
)
def Stochastic_Gradient_Descent():
    @task
    def load_dataset():
        # from IPython.display import display
        red_wine = pd.read_csv("data/winequality-red.csv")

        # Create training and validation splits
        df_train = red_wine.sample(frac=0.7, random_state=0)
        df_valid = red_wine.drop(
            df_train.index
        )  # drop from red_wine the lines (indices) contained in df_train

        # Scale to [0, 1]
        max_ = df_train.max(axis=0)
        min_ = df_train.min(axis=0)
        df_train = (df_train - min_) / (max_ - min_)
        df_valid = (df_valid - min_) / (max_ - min_)
        df_train.to_csv(f"data/train/wq-scaled.csv", index=False)
        df_valid.to_csv(f"data/valid/wq-scaled.csv", index=False)

    @task
    def split_dataset():
        # Split features and target
        df_train = pd.read_csv(f"data/train/wq-scaled.csv")
        df_valid = pd.read_csv(f"data/valid/wq-scaled.csv")

        X_train = df_train.drop("quality", axis=1)
        X_valid = df_valid.drop("quality", axis=1)
        y_train = df_train["quality"]
        y_valid = df_valid["quality"]

        X_train.to_csv(f"data/train/X_train.csv", index=False)
        y_train.to_csv(f"data/train/y_train.csv", index=False)
        X_valid.to_csv(f"data/valid/X_valid.csv", index=False)
        y_valid.to_csv(f"data/valid/y_valid.csv", index=False)

    @task
    def train_model(task_instance: TaskInstance):
        model = keras.Sequential(
            [
                layers.Dense(512, activation="relu", input_shape=[11]),
                layers.Dense(512, activation="relu"),
                layers.Dense(512, activation="relu"),
                layers.Dense(1),
            ]
        )
        model.compile(
            optimizer="adam",
            loss="mae",
        )

        X_train = pd.read_csv(f"data/train/X_train.csv")
        y_train = pd.read_csv(f"data/train/y_train.csv")
        X_valid = pd.read_csv(f"data/valid/X_valid.csv")
        y_valid = pd.read_csv(f"data/valid/y_valid.csv")

        history = model.fit(
            X_train,
            y_train,
            validation_data=(X_valid, y_valid),
            batch_size=256,
            epochs=10,
        )
        # history_df = pd.DataFrame(history.history)
        # print(history_df)

        model.save("data/models/{}".format(task_instance.run_id))

    @task
    def predict_value_on_test_data(task_instance: TaskInstance):
        import tensorflow as tf

        df_valid = pd.read_csv(f"data/valid/wq-scaled.csv")
       
        model = tf.keras.models.load_model(
            "data/models/{}".format(task_instance.run_id)
        )
        expl = df_valid.sample(n=10)
        X = expl.drop("quality", axis=1)
        y = expl["quality"]
        print("expected Values: -------------------------------------------------")
        print(y)
        yp = model.predict(X)
        print("predicted Values: -------------------------------------------------")
        print(yp)

    load_dataset() >> split_dataset() >> train_model() >> predict_value_on_test_data()


ml_dag = Stochastic_Gradient_Descent()

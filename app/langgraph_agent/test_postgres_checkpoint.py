from langgraph.checkpoint.postgres import PostgresSaver


# POSTGRES_URI = "postgresql://someshjaiswal@localhost:5432/restaurant_agent"
POSTGRES_URI = "postgresql://someshjaiswal@localhost:5432/restaurant_agent"


with PostgresSaver.from_conn_string(POSTGRES_URI) as checkpointer:
    checkpointer.setup()

    print("PostgreSQL checkpointer initialized successfully.")
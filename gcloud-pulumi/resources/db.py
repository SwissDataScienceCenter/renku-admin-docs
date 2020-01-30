from pulumi_gcp import sql


def deploy_db():
    """Create an SQL db instance"""

    db_instance = sql.DatabaseInstance(
        "my-database-instance",
        region="europe-west3",
        database_version="POSTGRES_9_6",
        settings={"tier": "db-f1-micro"},
    )

    return db_instance

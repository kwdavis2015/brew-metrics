import json
import logging
import os

import boto3

logger = logging.getLogger(__name__)


def load_secrets():
    secret_name_db = os.environ.get("SECRET_NAME_DB")
    secret_name_admin = os.environ.get("SECRET_NAME_ADMIN")

    if not secret_name_db and not secret_name_admin:
        return

    region = os.environ.get("AWS_REGION", "us-east-1")
    client = boto3.client("secretsmanager", region_name=region)

    if secret_name_db:
        secret = json.loads(client.get_secret_value(SecretId=secret_name_db)["SecretString"])
        os.environ["DATABASE_URL"] = secret["url"]
        logger.info("DB credentials loaded from Secrets Manager")

    if secret_name_admin:
        secret = json.loads(client.get_secret_value(SecretId=secret_name_admin)["SecretString"])
        os.environ["ADMIN_USERNAME"] = secret["username"]
        os.environ["ADMIN_PASSWORD"] = secret["password"]
        if "dossier_key" in secret:
            os.environ["DOSSIER_KEY"] = secret["dossier_key"]
        logger.info("Admin credentials loaded from Secrets Manager")

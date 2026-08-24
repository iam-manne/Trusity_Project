import csv
import hashlib
import io
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from urllib.parse import unquote_plus

import boto3
import pg8000.dbapi

logger = logging.getLogger()
logger.setLevel(logging.INFO)
s3 = boto3.client("s3")
secrets = boto3.client("secretsmanager")


def _database_config() -> dict:
    secret = json.loads(
        secrets.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"]
    )
    return {
        "host": os.environ["DB_HOST"],
        "port": int(os.environ.get("DB_PORT", "5432")),
        "database": os.environ["DB_NAME"],
        "user": secret["username"],
        "password": secret["password"],
        "ssl_context": True,
        "timeout": 10,
    }


def _parse_row(row: dict[str, str]) -> tuple[str, str, int]:
    customer_id = (row.get("customer_id") or "").strip()
    product_id = (row.get("product_id") or "").strip()
    if not customer_id or len(customer_id) > 100:
        raise ValueError("customer_id must contain 1-100 characters")
    if not product_id or len(product_id) > 100:
        raise ValueError("product_id must contain 1-100 characters")
    quantity = int(row.get("quantity") or 0)
    if quantity <= 0 or quantity > 1_000_000:
        raise ValueError("quantity must be between 1 and 1000000")
    return customer_id, product_id, quantity


def _import_file(bucket: str, key: str, version_id: str | None) -> dict:
    get_args = {"Bucket": bucket, "Key": key}
    if version_id:
        get_args["VersionId"] = version_id
    body = s3.get_object(**get_args)["Body"].read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(body))
    required = {"customer_id", "product_id", "quantity"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError(f"CSV headers must include {sorted(required)}")

    connection = pg8000.dbapi.connect(**_database_config())
    inserted = duplicates = 0
    failures: list[dict] = []
    try:
        cursor = connection.cursor()
        for row_number, row in enumerate(reader, start=2):
            source = f"{bucket}/{key}/{version_id or 'unversioned'}/{row_number}"
            import_id = hashlib.sha256(source.encode()).hexdigest()
            try:
                customer_id, product_id, quantity = _parse_row(row)
                cursor.execute(
                    """
                    INSERT INTO orders
                        (order_id, customer_id, product_id, quantity, status,
                         source_import_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, 'pending', %s, %s, %s)
                    ON CONFLICT (source_import_id) DO NOTHING
                    """,
                    (
                        str(uuid.uuid4()), customer_id, product_id, quantity,
                        import_id, datetime.now(timezone.utc), datetime.now(timezone.utc),
                    ),
                )
                if cursor.rowcount == 1:
                    inserted += 1
                else:
                    duplicates += 1
                connection.commit()
            except (ValueError, TypeError) as exc:
                connection.rollback()
                failures.append({"row": row_number, "error": str(exc), "data": row})
            except Exception:
                connection.rollback()
                logger.exception("Transient database error at row %s", row_number)
                raise
    finally:
        connection.close()

    result = {
        "bucket": bucket,
        "key": key,
        "inserted": inserted,
        "duplicates": duplicates,
        "failed": len(failures),
        "failures": failures,
    }
    report_key = f"import-reports/{key.rsplit('/', 1)[-1]}.{version_id or 'latest'}.json"
    s3.put_object(
        Bucket=os.environ.get("REPORT_BUCKET", bucket),
        Key=report_key,
        Body=json.dumps(result, default=str).encode(),
        ContentType="application/json",
    )
    logger.info("import complete %s", json.dumps({k: v for k, v in result.items() if k != "failures"}))
    return result


def handler(event, _context):
    results = []
    for record in event.get("Records", []):
        bucket = record["s3"]["bucket"]["name"]
        key = unquote_plus(record["s3"]["object"]["key"])
        version_id = record["s3"]["object"].get("versionId")
        results.append(_import_file(bucket, key, version_id))
    return {"processed_files": len(results), "results": results}

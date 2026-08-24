#!/usr/bin/env python3
"""Generate and optionally publish the public order statistics page."""

import argparse
import html
import json
import os
from pathlib import Path
from urllib.request import urlopen

import boto3
from sqlalchemy import create_engine, text


QUERY = text("""
SELECT
  COUNT(*) AS total,
  COUNT(*) FILTER (WHERE status = 'pending') AS pending,
  COUNT(*) FILTER (WHERE status = 'completed') AS completed,
  COUNT(*) FILTER (WHERE status = 'failed') AS failed,
  COALESCE((SELECT product_id FROM orders GROUP BY product_id
            ORDER BY SUM(quantity) DESC, product_id LIMIT 1), 'N/A') AS top_product
FROM orders
""")


def render(stats: dict) -> str:
    cards = "".join(
        f'<article><span>{html.escape(label)}</span><strong>{html.escape(str(value))}</strong></article>'
        for label, value in (
            ("Total orders", stats["total"]),
            ("Pending", stats["pending"]),
            ("Completed", stats["completed"]),
            ("Failed", stats["failed"]),
            ("Top product", stats["top_product"]),
        )
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Order processing statistics</title><style>
:root{{--ink:#18212b;--muted:#66717c;--paper:#f5f7f8;--accent:#007a68;--line:#d7dde1}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--paper);color:var(--ink);font-family:system-ui,sans-serif}}
main{{max-width:1000px;margin:0 auto;padding:64px 24px}}header{{border-bottom:3px solid var(--accent);padding-bottom:24px}}
h1{{font-size:clamp(2rem,5vw,4rem);margin:0 0 8px;letter-spacing:0}}p,span{{color:var(--muted)}}
section{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:1px;background:var(--line);border:1px solid var(--line);margin-top:32px}}
article{{background:white;padding:24px;min-height:140px;display:flex;flex-direction:column;justify-content:space-between}}
strong{{font-size:2rem;overflow-wrap:anywhere}}@media(max-width:480px){{main{{padding:32px 16px}}}}
</style></head><body><main><header><h1>Order statistics</h1><p>Current processing snapshot</p></header><section>{cards}</section></main></body></html>"""


def stats_from_api(api_url: str) -> dict:
    with urlopen(f"{api_url.rstrip('/')}/orders", timeout=30) as response:
        orders = json.load(response)
    quantities: dict[str, int] = {}
    for order in orders:
        product_id = order["product_id"]
        quantities[product_id] = quantities.get(product_id, 0) + order["quantity"]
    top_product = min(
        quantities,
        key=lambda product_id: (-quantities[product_id], product_id),
        default="N/A",
    )
    return {
        "total": len(orders),
        "pending": sum(order["status"] == "pending" for order in orders),
        "completed": sum(order["status"] == "completed" for order in orders),
        "failed": sum(order["status"] == "failed" for order in orders),
        "top_product": top_product,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", default=os.getenv("DATABASE_URL"))
    parser.add_argument("--api-url", default=os.getenv("API_URL"))
    parser.add_argument("--output", type=Path, default=Path("site/index.html"))
    parser.add_argument("--bucket", help="Optional S3 destination bucket")
    args = parser.parse_args()
    if args.api_url:
        stats = stats_from_api(args.api_url)
    elif args.database_url:
        engine = create_engine(args.database_url, pool_pre_ping=True)
        with engine.connect() as connection:
            stats = dict(connection.execute(QUERY).mappings().one())
    else:
        parser.error("--api-url, API_URL, --database-url, or DATABASE_URL is required")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(stats), encoding="utf-8")
    if args.bucket:
        boto3.client("s3").upload_file(
            str(args.output), args.bucket, "index.html",
            ExtraArgs={"ContentType": "text/html", "CacheControl": "max-age=300"},
        )
    print(f"Generated {args.output}")


if __name__ == "__main__":
    main()

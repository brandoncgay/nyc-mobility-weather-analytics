import os
from dagster import asset, AssetExecutionContext
from google.cloud import storage
from src.utils.config import config
from dagster_dbt import DbtCliResource

@asset(
    deps=["nyc_mobility_analytics_dbt_assets"],
    description="Generate dbt docs and elementary report, then upload to GCS",
    group_name="documentation"
)
def upload_documentation(context: AssetExecutionContext, dbt: DbtCliResource):
    """
    1. Run `dbt docs generate`
    2. Run `edr report`
    3. Upload to GCS
    """
    if not config.gcs_bucket_name:
        context.log.warn("No GCS bucket configured. Skipping documentation upload.")
        return

    # 1. Generate dbt docs
    context.log.info("Generating dbt docs...")
    dbt.cli(["docs", "generate"], context=context).wait()

    # 2. Upload dbt docs
    bucket_name = config.gcs_bucket_name
    client = storage.Client()
    bucket = client.bucket(bucket_name)

    # Walk through target directory and upload relevant files
    target_dir = "dbt/target"
    files_to_upload = ["index.html", "manifest.json", "catalog.json", "run_results.json"]
    
    for filename in files_to_upload:
        filepath = os.path.join(target_dir, filename)
        if os.path.exists(filepath):
            blob = bucket.blob(f"dbt-docs/{filename}")
            blob.upload_from_filename(filepath)
            context.log.info(f"Uploaded {filename} to gs://{bucket_name}/dbt-docs/")

    # 3. Generate & Upload Elementary Report
    # Note: This assumes 'edr' is available in the environment
    context.log.info("Generating Elementary report...")
    report_path = "dbt/elementary_report.html"
    os.system(f"edr report --file-path {report_path}")

    if os.path.exists(report_path):
        blob = bucket.blob("observability/report.html")
        blob.upload_from_filename(report_path)
        context.log.info(f"Uploaded report.html to gs://{bucket_name}/observability/")
    else:
        context.log.warn("Elementary report generation failed or file not found.")

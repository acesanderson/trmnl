import os

EXPECTED_HOSTNAME = "caruana"

if not os.getenv("TRMNL_SKIP_HOST_CHECK") and __import__("socket").gethostname() != EXPECTED_HOSTNAME:
    raise EnvironmentError(
        f"You are not on the trmnl server host (you should be on {'expected_hostname'})."
    )

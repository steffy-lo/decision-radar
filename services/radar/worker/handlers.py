"""KAN-4/KAN-17 register their idempotent business handlers here.

Each handler receives the saved immutable Job. Use job.id/source_version for
publication IDs and verify input versions before writing. Completion receipts
cannot make non-idempotent business writes safe after a process crash.
"""

from services.radar.services.jobs import JobHandler


def get_job_handlers() -> dict[str, JobHandler]:
    # Main does not yet contain source refresh or assessment services.
    # Admission stays closed until those handlers are integrated and tested.
    return {}

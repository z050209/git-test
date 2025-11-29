"""Utilities for emailing collected job search results.

The helpers keep SMTP handling isolated from the scraping logic so you can
import ``send_job_results`` from other scripts (for example ``job_search.py``)
and reuse it across cron jobs or notebooks.
"""

import os
import smtplib
from email.message import EmailMessage
from typing import Iterable, Mapping, NamedTuple

Job = Mapping[str, str]


class SMTPConfig(NamedTuple):
    """Configuration for connecting to the SMTP relay."""

    host: str
    port: int
    username: str
    password: str
    use_tls: bool = True
    from_address: str | None = None

    @classmethod
    def from_env(cls) -> "SMTPConfig":
        """Load SMTP settings from environment variables.

        Required variables
        ------------------
        - ``SMTP_HOST``
        - ``SMTP_PORT``
        - ``SMTP_USERNAME``
        - ``SMTP_PASSWORD``

        Optional variables
        ------------------
        - ``SMTP_USE_TLS``: defaults to ``True`` unless set to a falsy value
        - ``SMTP_FROM_ADDRESS``: defaults to ``SMTP_USERNAME`` when missing
        """

        host = os.environ["SMTP_HOST"]
        port = int(os.environ.get("SMTP_PORT", 587))
        username = os.environ["SMTP_USERNAME"]
        password = os.environ["SMTP_PASSWORD"]
        use_tls = os.environ.get("SMTP_USE_TLS", "true").lower() not in {"0", "false", "no"}
        from_address = os.environ.get("SMTP_FROM_ADDRESS") or username

        return cls(
            host=host,
            port=port,
            username=username,
            password=password,
            use_tls=use_tls,
            from_address=from_address,
        )


def format_jobs(jobs: Iterable[Job], limit: int = 50) -> str:
    """Render a readable text summary of the collected jobs."""

    job_list = list(jobs)
    lines: list[str] = []
    for idx, job in enumerate(job_list, start=1):
        if idx > limit:
            remaining = len(job_list) - (limit)
            lines.append(f"...and {remaining} more")
            break

        company = job.get("company", "Unknown company")
        title = job.get("title", "Unknown title")
        location = job.get("location", "")
        source = job.get("source", "")
        link = job.get("link", "")
        score = job.get("score", "")

        remote_flag = " 🌍REMOTE" if job.get("remote") else ""
        lines.append(f"#{idx} {company} — {title}{remote_flag}")
        lines.append(f"   ⭐ Score: {score}")
        lines.append(f"   📍 {location} | 来源: {source}")
        lines.append(f"   🔗 {link}")
        lines.append("-")

    return "\n".join(lines)


def send_job_results(jobs: Iterable[Job], recipient: str, smtp_config: SMTPConfig, *, subject: str = "Daily AI/ML job search") -> None:
    """Send the formatted job list to ``recipient`` using the given SMTP relay."""

    body = format_jobs(jobs)
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = smtp_config.from_address or smtp_config.username
    msg["To"] = recipient
    msg.set_content(body)

    with smtplib.SMTP(smtp_config.host, smtp_config.port, timeout=30) as server:
        if smtp_config.use_tls:
            server.starttls()
        if smtp_config.username:
            server.login(smtp_config.username, smtp_config.password)
        server.send_message(msg)


def send_job_results_from_env(jobs: Iterable[Job], recipient: str, *, subject: str = "Daily AI/ML job search") -> None:
    """Convenience wrapper using :class:`SMTPConfig` loaded from environment variables."""

    smtp_config = SMTPConfig.from_env()
    send_job_results(jobs, recipient, smtp_config, subject=subject)


__all__ = ["SMTPConfig", "send_job_results", "send_job_results_from_env", "format_jobs"]

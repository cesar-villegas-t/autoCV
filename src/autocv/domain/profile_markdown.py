"""Render a CandidateProfile in the same Markdown layout as profiles/profile.example.md."""
from autocv.domain.profile import CandidateProfile

MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def month_label(value: str) -> str:
    year, month = value.split("-")
    return f"{MONTHS[int(month) - 1]} {year}"


def date_range(start: str | None, end: str | None, current: bool) -> str:
    finish = "Present" if current else (month_label(end) if end else "")
    begin = month_label(start) if start else ""
    if begin and finish:
        return f"{begin} – {finish}"
    return begin or finish


def bullets(value: str) -> list[str]:
    """One bullet per line; the prefix also stops user text from becoming headings."""
    lines = []
    for raw in value.split("\n"):
        line = raw.strip()
        if not line:
            continue
        lines.append(line if line[:2] in {"- ", "* "} else f"- {line}")
    return lines


def dates_line(start: str | None, end: str | None, current: bool) -> list[str]:
    label = date_range(start, end, current)
    return [f"**Dates:** {label}"] if label else []


def render_profile_markdown(profile: CandidateProfile) -> str:
    name = " ".join(part for part in (profile.first_name, profile.last_name) if part)
    out: list[str] = [f"# {name}" if name else "# Candidate", ""]
    sections: list[tuple[str, list[str]]] = []

    contact = []
    if profile.phone:
        contact.append(f"- **Phone:** {profile.phone}")
    if profile.email:
        contact.append(f"- **Email:** {profile.email}")
    if profile.linkedin:
        contact.append(f"- **LinkedIn:** {profile.linkedin}")
    contact += [f"- **{link.label}:** {link.url}" for link in profile.links]
    if profile.location:
        contact.append(f"- **Current Location:** {profile.location}")
    if profile.relocations:
        contact.append(f"- **Availability / Relocation:** Open to relocation: {', '.join(profile.relocations)}")
    if contact:
        sections.append(("Contact Information & Links", contact))

    if profile.summary:
        sections.append(("Professional Summary", bullets(profile.summary)))

    if profile.experience:
        body: list[str] = []
        for job in profile.experience:
            body += [f"### {job.title} | {job.company}",
                     *dates_line(job.start_date, job.end_date, job.current)]
            if job.description:
                body += ["**Key Achievements & Responsibilities:**", *bullets(job.description)]
            body.append("")
        sections.append(("Work Experience", body))

    if profile.education:
        body = []
        for study in profile.education:
            where = f"{study.institution}, {study.location}" if study.location else study.institution
            body += [f"### {study.degree}", f"**Institution:** {where}",
                     *dates_line(study.start_date, study.end_date, study.current)]
            if study.grade:
                body.append(f"- **Grade:** {study.grade}")
            body += bullets(study.description)
            body.append("")
        sections.append(("Education", body))

    for title, items in (("Achievements", profile.achievements), ("Projects", profile.projects)):
        if items:
            body = []
            for item in items:
                body += [f"### {item.name}", *dates_line(item.start_date, item.end_date, item.current),
                         *bullets(item.description), ""]
            sections.append((title, body))

    if profile.skills:
        sections.append(("Skills", bullets(profile.skills)))

    if profile.languages:
        rows = []
        for entry in profile.languages:
            detail = " – ".join(part for part in (entry.level, entry.certification) if part)
            rows.append(f"- **{entry.language}:** {detail}" if detail else f"- **{entry.language}**")
        sections.append(("Languages", rows))

    for number, (title, body) in enumerate(sections, start=1):
        out += [f"## {number}. {title}", *body, ""]
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + "\n"

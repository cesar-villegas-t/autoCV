from typing import Any
from autocv.domain.text import tex, safe_url, safe_email

def hyperlink(label: str, url: str) -> str:
    return rf"\href{{{tex(url)}}}{{{tex(label)}}}" if safe_url(url) else ""


def render(resume: dict[str, Any]) -> str:
    """Render escaped model data through a local compact A4 CV template."""
    lines = [
        r"\documentclass[10pt,a4paper]{extarticle}",
        r"\usepackage[left=0.48in,right=0.48in,top=0.35in,bottom=0.35in]{geometry}",
        r"\usepackage[T1]{fontenc}",
        r"\usepackage[utf8]{inputenc}",
        r"\usepackage{lmodern}",
        r"\usepackage{microtype}",
        r"\input{glyphtounicode}",
        r"\pdfgentounicode=1",
        r"\usepackage[hidelinks]{hyperref}",
        r"\usepackage{enumitem}",
        r"\pagestyle{empty}",
        r"\setlength{\parindent}{0pt}",
        r"\setlength{\parskip}{0pt}",
        r"\linespread{0.96}",
        r"\setlist[itemize]{leftmargin=1.1em,topsep=1pt,itemsep=0pt,parsep=0pt,partopsep=0pt}",
        r"\newcommand{\cvsection}[1]{\vspace{4pt}{\large\bfseries #1}\par\vspace{1pt}\hrule\vspace{2pt}}",
        r"\newcommand{\entry}[3]{\textbf{#1}\hfill\textit{#3}\par\textit{#2}\par}",
        r"\begin{document}",
        r"\begin{center}",
        rf"{{\Large\bfseries {tex(resume['name'])}}}\\[-2pt]",
        rf"{{\normalsize {tex(resume['headline'])}}}\\[0pt]",
    ]
    contact, email = resume["contact"], safe_email(resume["contact"]["email"])
    contact_rows = [
        [tex(contact["location"])],
        [tex(contact["phone"]), rf"\href{{mailto:{tex(email)}}}{{{tex(email)}}}" if email else ""],
        [hyperlink(contact["linkedin"], contact["linkedin"]),
         hyperlink(contact["github"], contact["github"])],
    ]
    lines.append(r"{\small")
    for row in contact_rows:
        if items := [item for item in row if item]:
            lines.append(r" $\,|\, $ ".join(items) + r"\par")
    lines += ["}", r"\end{center}\vspace{-5pt}"]
    if resume["summary"]:
        lines += [r"\cvsection{Profile}", tex(resume["summary"]) + r"\par"]
    if resume["experience"]:
        lines.append(r"\cvsection{Work Experience}")
        for job in resume["experience"]:
            title = tex(job["title"]) + (f" | {tex(job['location'])}" if job["location"] else "")
            lines.append(rf"\entry{{{title}}}{{{tex(job['company'])}}}{{{tex(job['dates'])}}}")
            if job["bullets"]:
                lines += [r"\begin{itemize}", *[rf"\item {tex(bullet)}" for bullet in job["bullets"]], r"\end{itemize}"]
    if resume["education"]:
        lines.append(r"\cvsection{Education}")
        for study in resume["education"]:
            lines.append(rf"\entry{{{tex(study['degree'])}}}{{{tex(study['institution'])}}}{{{tex(study['dates'])}}}")
            if study["details"]:
                lines.append(tex(study["details"]) + r"\par")
    if resume["projects"]:
        lines.append(r"\cvsection{Projects \& Awards}")
        for project in resume["projects"]:
            heading = rf"\textbf{{{tex(project['name'])}}}"
            if project["tech"]:
                heading += rf" --- \textit{{{tex(project['tech'])}}}"
            lines += [heading + r"\par", *[tex(bullet) + r"\par" for bullet in project["bullets"]]]
    if resume["skills"]:
        lines.append(r"\cvsection{Skills}")
        lines += [rf"\textbf{{{tex(skill['category'])}:}} {tex(', '.join(skill['items']))}\par"
                  for skill in resume["skills"]]
    if resume["languages"]:
        lines += [r"\cvsection{Languages}", tex(", ".join(resume["languages"])) + r"\par"]
    return "\n".join([*lines, r"\end{document}", ""])

def sample_resume():
    return {
        "name": "Test Candidate",
        "headline": "Data & Software Engineer",
        "contact": {
            "email": "first_last+tag@example.com",
            "phone": "",
            "location": "",
            "linkedin": "https://example.com/a_b?x=1&y=2#section",
            "github": "https://example.com/a%20b",
        },
        "summary": "Engineered data platforms for research & development.",
        "experience": [{
            "title": "Engineer",
            "company": f"Employer {i}",
            "dates": "2020-2024",
            "location": "",
            "bullets": [f"Optimized pipeline {j}, reducing runtime by 80%." for j in range(5)],
        } for i in range(3)],
        "education": [{
            "degree": f"Qualification {i}",
            "institution": "University",
            "dates": "2016-2020",
            "details": "Documented qualification detail. " * 6 + "GPA: 3.8/4.0",
        } for i in range(3)],
        "projects": [{
            "name": f"Project {i}",
            "tech": "Python",
            "bullets": ["Implemented a data pipeline.", "Reduced processing time by 25%."],
        } for i in range(3)],
        "skills": [{"category": f"Category {i}", "items": [f"Tool {j}" for j in range(11)]}
                   for i in range(5)],
        "languages": [f"Language {i}: documented level" for i in range(5)],
    }
